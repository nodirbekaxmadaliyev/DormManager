import tempfile
from django.utils import timezone
from django.db.models import Count, Q
import os
from django.views.generic import ListView, DetailView, UpdateView, CreateView, DeleteView
from django.urls import reverse_lazy, reverse
from .forms import StudentCreateForm
from dormitory.models import Dormitory, Room
from .models import Student
import pandas as pd
from django.http import HttpResponse
from datetime import datetime
from openpyxl import Workbook
from utils.hikvision import add_user_to_devices, delete_user_from_devices, open_user_on_devices, block_user_on_devices
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db import models
from django.views.decorators.csrf import csrf_exempt
from utils.utils import filter_by_user_role
from django.views import View
from django.contrib import messages
from django.shortcuts import redirect
import time


class StudentListView(ListView):
    model = Student
    template_name = 'student/home.html'
    context_object_name = 'object_list'
    paginate_by = 20

    def get_queryset(self):

        queryset = super().get_queryset()
        queryset = filter_by_user_role(queryset, self.request.user)

        # Status filter (ichkarida/tashqarida)
        status = self.request.GET.get('status', '')
        if status == 'in_dormitory':
            queryset = queryset.filter(is_in_dormitory=True, is_deleted=False)
        elif status == 'out_dormitory':
            queryset = queryset.filter(is_in_dormitory=False, is_deleted=False)
        elif status == 'deleted':
            queryset = queryset.filter(is_deleted=True)
        else:
            queryset = queryset.filter(is_deleted=False)

        # Qidiruv parametrlari
        dormitory = self.request.GET.get('dormitory', '')
        room = self.request.GET.get('room', '')
        first_name = self.request.GET.get('first_name', '')
        faculty = self.request.GET.get('faculty', '')

        if dormitory:
            queryset = queryset.filter(dormitory__name__icontains=dormitory)
        if room:
            queryset = queryset.filter(room__number__icontains=room)
        if first_name:
            queryset = queryset.filter(
                Q(first_name__icontains=first_name) |
                Q(last_name__icontains=first_name)
            )
        if faculty:
            queryset = queryset.filter(faculty__icontains=faculty)

        return queryset.order_by('room', 'last_name', 'first_name')

    def get(self, request, *args, **kwargs):
        if request.GET.get("export") == "excel":
            queryset = self.get_queryset()

            df = pd.DataFrame(list(queryset.values(
                'pk', 'first_name', 'last_name', 'dormitory__name', 'faculty', 'room__number',
                'phone_number', 'parent_full_name', 'is_in_dormitory', 'arrival_time', 'checkout_time'
            )))

            # total_payment ni qo‘shish
            df['total_payment'] = [student.total_payment for student in queryset]

            df.index = df.index + 1
            df.insert(0, '№', df.index)

            # Sarlavhalarni o'zgartirish
            df.rename(columns={
		'pk': 'Student ID',
                'first_name': 'Ismi',
                'last_name': 'Familiyasi',
                'dormitory__name': 'Yotoqxonasi',
                'faculty': 'Fakulteti',
                'room': 'Xonasi',
                'phone_number': 'Telefon raqami',
		'parent_full_name': 'Ota-onasi',
                'is_in_dormitory': 'Yotoqxonada',
                'arrival_time': 'Kelgan sana',
                'checkout_time': 'Ketadigan sana',
                'total_payment': 'To\'lov summasi'
            }, inplace=True)

            # Boolean qiymatlarni formatlash
            df['Yotoqxonada'] = df['Yotoqxonada'].map({True: 'Ha', False: 'Yo\'q'})

            # Sana maydonlarini formatlash (None qiymatlarni hisobga olgan holda)
            for date_col in ['Kelgan sana', 'Ketadigan sana']:
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                df[date_col] = df[date_col].dt.strftime('%Y-%m-%d')
                df[date_col] = df[date_col].replace('NaT', '')

            now = datetime.now().strftime("%Y-%m-%d_%H-%M")
            filename = f"talabalar_{now}.xlsx"

            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename={filename}'
            df.to_excel(response, index=False)
            return response

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_count"] = self.get_queryset().count()
        context["device_errors"] = self.request.session.pop("device_errors", None)

        user = self.request.user

        if hasattr(user, 'director'):
            dormitories = Dormitory.objects.filter(director=user.director)
        else:
            dormitories = Dormitory.objects.filter(employees__user=user).distinct()

        # 🧩 Har bir yotoqxona bo‘yicha statistikalar (faol talabalar)
        dormitory_stats = dormitories.annotate(
            total=Count('students', filter=Q(students__is_deleted=False)),
            in_dorm=Count('students', filter=Q(students__is_in_dormitory=True, students__is_deleted=False))
        )

        # 🧩 O‘chirilgan talabalar soni (umumiy)
        # 🧩 Har bir yotoqxona bo‘yicha statistikalar (faol va o‘chirilgan talabalar)
        dormitory_stats = dormitories.annotate(
            total=Count('students', filter=Q(students__is_deleted=False)),
            in_dorm=Count('students', filter=Q(students__is_in_dormitory=True, students__is_deleted=False)),
            deleted_count=Count('students', filter=Q(students__is_deleted=True))
        )

        # 🧩 Umumiy faol talabalar soni
        active_students_count = Student.objects.filter(
            dormitory__in=dormitories,
            is_deleted=False
        ).count()

        context['dormitory_stats'] = dormitory_stats
        context['all_student_count'] = active_students_count
        context['dormitories'] = dormitories

        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.GET.get('export') == 'excel':
            return self.export_to_excel(context['object_list'])
        return super().render_to_response(context, **response_kwargs)

    def export_to_excel(self, queryset):
        wb = Workbook()
        ws = wb.active
        ws.title = "Talabalar ro'yxati"

        # Sarlavhalar
        ws.append(['Ismi', 'Familiyasi', 'Xonasi', 'Fakulteti', 'Yotoqxonada'])

        # Ma’lumotlar
        for student in queryset:
            ws.append([
                student.first_name,
                student.last_name,
                student.room,
                student.faculty,
                'Ichkarida' if student.is_in_dormitory else 'Tashqarida'
            ])

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=talabalar.xlsx'
        wb.save(response)
        return response

class StudentDetailView(DetailView):
    model = Student
    template_name = 'student/student_detail.html'
    context_object_name = 'student'

class StudentUpdateView(UpdateView):
    model = Student
    template_name = 'student/student_update.html'
    fields = [
        "dormitory", "room", "first_name", "last_name", "faculty",
        "arrival_time", "checkout_time",
    ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Talaba ma'lumotlarini tahrirlash"
        return context

    def form_valid(self, form):
        student = form.save(commit=False)
        student.save()

        return super().form_valid(form)

    def get_success_url(self):
        return reverse('student_detail', kwargs={'pk': self.object.pk})

class StudentDeleteView(View):
    template_name = 'student/student_delete.html'
    success_url = reverse_lazy('students')

    def get(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        return render(request, self.template_name, {'object': student})

    def post(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        dormitory = student.dormitory
        student_id = str(student.id)

        # Qurilmalardan o‘chirishga harakat qilamiz
        success, reason = delete_user_from_devices(dormitory, student_id)

        if success:
            student.is_deleted = True
            student.checkout_time = timezone.now().date()
            student.room = None
            student.parent_full_name = (request.user.get_full_name() or request.user.username) + ' tomonidan o`chirilgan'
            student.save(update_fields=["is_deleted", "checkout_time", "room", "parent_full_name"])
            messages.success(request, "Talaba qurilmalardan muvaffaqiyatli o‘chirildi va tizimda 'o‘chirilgan' deb belgilandi.")
        else:
            messages.error(request, f"Talabani qurilmalardan o‘chirib bo‘lmadi: {reason}")

        return redirect(self.success_url)

class StudentDeleteFromModel(DeleteView):
    model = Student
    template_name = 'student/student_delete.html'
    success_url = reverse_lazy('students')

class DeleteAllStudentsView(View):
    success_url = reverse_lazy('students')

    def post(self, request, *args, **kwargs):
        students = Student.objects.all()

        deleted_count = 0
        failed_count = 0

        for student in students:
            dormitory = student.dormitory
            employee_id = str(student.id)

            success, reason = delete_user_from_devices(dormitory, employee_id)
            if success:

                student.delete()
                deleted_count += 1
            else:
                failed_count += 1
                messages.error(request, f"{student.first_name} {student.last_name} qurilmadan o‘chmadi: {reason}")

        if deleted_count:
            messages.success(request, f"{deleted_count} ta talaba muvaffaqiyatli o‘chirildi.")
        if failed_count:
            messages.warning(request, f"{failed_count} ta talabani qurilmadan o‘chirishda xatolik bo‘ldi.")

        return redirect(self.success_url)

class StudentCreateView(CreateView):
    model = Student
    template_name = 'student/student_add.html'
    form_class = StudentCreateForm
    success_url = reverse_lazy('students')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        student = form.save(commit=False)
        photo_file = form.cleaned_data.get('image')
        full_name = f"{form.cleaned_data['first_name']} {form.cleaned_data['last_name']}"
        dormitory = form.cleaned_data.get('dormitory')

        if photo_file and photo_file.size >= 200 * 1024:
            messages.error(self.request, "Rasm hajmi 200KB dan oshmasligi kerak.")
            return render(self.request, self.template_name, {'form': form})

        if not photo_file:
            messages.error(self.request, "Surat yuklanmagan. Iltimos, rasmni tanlang.")
            return render(self.request, self.template_name, {'form': form})

        # Rasmni vaqtinchalik saqlash
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
            for chunk in photo_file.chunks():
                tmp.write(chunk)
            tmp_file_path = tmp.name

        student.save()

        success, reason = add_user_to_devices(dormitory, str(student.id), full_name, tmp_file_path)

        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)

        if success:

            messages.success(self.request, "Talaba qurilmalarga muvaffaqiyatli qo‘shildi.")
            return redirect(self.success_url)
        else:
            student.delete()
            messages.error(self.request, f"Talaba qurilmalarga qo‘shilmadi: {reason}")
            return render(self.request, self.template_name, {'form': form})

    def form_invalid(self, form):
        messages.error(self.request, "Ma'lumotlarda xatolik mavjud.")
        return super().form_invalid(form)

def load_rooms_ajax(request):
    dormitory_id = request.GET.get('dormitory')
    rooms = Room.objects.filter(dormitory_id=dormitory_id)

    # Faqat to‘liq band bo‘lmagan xonalar
    rooms = rooms.annotate(occupied=Count('students')).filter(occupied__lt=models.F('size'))

    return JsonResponse(list(rooms.values('id', 'number')), safe=False)

@csrf_exempt
def toggle_block(request, pk):
    student = get_object_or_404(Student, pk=pk)
    Sid = str(student.id)
    print(Sid)
    if request.method == 'POST':
        if student.blocked:
            success, reason = open_user_on_devices(student.dormitory, Sid)
            if success:
                student.blocked = False
                student.save()
                messages.success(request, "Foydalanuvchi ochildi.")
            else:
                messages.error(request, f"Ochishda xatolik: {reason}")
        else:
            success, reason = block_user_on_devices(student.dormitory, Sid)
            if success:
                student.blocked = True
                student.save()
                messages.success(request, "Foydalanuvchi bloklandi.")
            else:
                messages.error(request, f"Bloklashda xatolik: {reason}")

    return redirect('student_detail', pk=student.pk)



class AddStudentsToDevicesView(View):
    def post(self, request, *args, **kwargs):
        dormitory_id = request.POST.get("dormitory_id")
        dormitory = Dormitory.objects.filter(id=dormitory_id, director=request.user.director).first()
        if not dormitory:
            return JsonResponse({"error": "Yotoqxona topilmadi yoki sizga tegishli emas!"}, status=400)

        students = Student.objects.filter(dormitory=dormitory, is_deleted=False)
        success_count = 0
        failed_count = 0

        for student in students:
            full_name = f"{student.first_name} {student.last_name}"
            image_path = student.image.path if student.image else ""
            success, error = add_user_to_devices(dormitory, str(student.id), full_name, image_path)
            if success:
                success_count += 1
            else:
                failed_count += 1
            time.sleep(0.7)  # 0.7 soniya interval (so‘ralgandek)

        return JsonResponse({
            "success_count": success_count,
            "failed_count": failed_count
        })

