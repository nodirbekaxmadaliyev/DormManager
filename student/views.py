import tempfile
from django.db.models import Count, Q
import os
from django.views.generic import ListView, DetailView, UpdateView, DeleteView, CreateView
from django.urls import reverse_lazy, reverse
from .forms import StudentCreateForm
from dormitory.models import Dormitory, Room
from .models import Student
import pandas as pd
from django.http import HttpResponse
from datetime import datetime
from openpyxl import Workbook
from utils.hikvision import add_user_to_devices, delete_user_from_devices, update_dormitory_status
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.db import models

class StudentListView(ListView):
    model = Student
    template_name = 'student/home.html'
    context_object_name = 'object_list'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        # 👉 Dormitorylar ro‘yxatini aniqlash
        dormitories = []
        if hasattr(user, 'director'):
            dormitories = user.director.dormitories.all()
        elif hasattr(user, 'employee') and user.employee.dormitory:
            dormitories = [user.employee.dormitory]

        # 👉 Qurilma loglarini tekshirish va xatoliklarni sessionga saqlash
        if dormitories:
            _, errors = update_dormitory_status(dormitories)
            if errors:
                request.session["device_errors"] = errors
            else:
                request.session.pop("device_errors", None)

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()

        user = self.request.user

        # Foydalanuvchining direktor yoki hodimligiga qarab filtr
        if hasattr(user, 'director'):
            queryset = queryset.filter(dormitory__director=user.director)
        else:
            queryset = queryset.filter(dormitory__employees__user=user)

        # Status filter (ichkarida/tashqarida)
        status = self.request.GET.get('status', '')
        if status == 'in_dormitory':
            queryset = queryset.filter(is_in_dormitory=True)
        elif status == 'out_dormitory':
            queryset = queryset.filter(is_in_dormitory=False)

        # Qidiruv parametrlari
        dormitory = self.request.GET.get('dormitory', '')
        room = self.request.GET.get('room', '')
        first_name = self.request.GET.get('first_name', '')
        faculty = self.request.GET.get('faculty', '')

        if dormitory:
            queryset = queryset.filter(dormitory__name__icontains=dormitory)
        if room:
            queryset = queryset.filter(room__icontains=room)
        if first_name:
            queryset = queryset.filter(first_name__icontains=first_name)
        if faculty:
            queryset = queryset.filter(faculty__icontains=faculty)

        return queryset.order_by('dormitory__name', 'room', 'last_name', 'first_name')

    def get(self, request, *args, **kwargs):
        if request.GET.get("export") == "excel":
            queryset = self.get_queryset()

            # DataFrame yaratish
            df = pd.DataFrame(list(queryset.values(
                'first_name', 'last_name', 'dormitory__name', 'faculty', 'room',
                'phone_number', 'is_in_dormitory', 'arrival_time',
                'checkout_time', 'total_payment'
            )))

            df.index = df.index + 1
            df.insert(0, '№', df.index)

            # Sarlavhalarni o'zgartirish
            df.rename(columns={
                'first_name': 'Ismi',
                'last_name': 'Familiyasi',
                'dormitory__name': 'Yotoqxonasi',
                'faculty': 'Fakulteti',
                'room': 'Xonasi',
                'phone_number': 'Telefon raqami',
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

        # Statistikani qurish
        dormitory_stats = dormitories.annotate(
            total=Count('students'),
            in_dorm=Count('students', filter=Q(students__is_in_dormitory=True))
        )

        context['dormitory_stats'] = dormitory_stats
        context['all_student_count'] = Student.objects.count() if hasattr(user, 'director') else Student.objects.filter(
            dormitory__in=dormitories).count()
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

class StudentUpdateView(LoginRequiredMixin, UpdateView):
    model = Student
    template_name = 'student/student_update.html'
    form_class = StudentCreateForm  # fields o‘rniga forma klassidan foydalanamiz
    success_url = None  # get_success_url ishlaydi

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user  # Formaga foydalanuvchini yuborish
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Talaba ma'lumotlarini tahrirlash"
        return context

    def get_success_url(self):
        return reverse('student_detail', kwargs={'pk': self.object.pk})


class StudentDeleteView(DeleteView):
    model = Student
    template_name = 'student/student_delete.html'
    success_url = reverse_lazy('students')

    def form_valid(self, request, *args, **kwargs):
        self.object = self.get_object()
        employee_id = str(self.object.id)
        dormitory = self.object.dormitory
        success, reason = delete_user_from_devices(dormitory, employee_id)
        if not success:
            # Qurilmalardan o‘chirishda xatolik bo‘lsa, foydalanuvchini modeldan o‘chirmaymiz
            messages.error(request, f"Foydalanuvchi qurilmalardan o‘chmadi: {reason}")
            return self.get(request, *args, **kwargs)

        return super().delete(request, *args, **kwargs)

class StudentCreateView(LoginRequiredMixin, CreateView):
    model = Student
    template_name = 'student/student_add.html'
    form_class = StudentCreateForm
    success_url = reverse_lazy('students')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user  # Foydalanuvchini forma ichiga yuborish
        return kwargs

    def form_valid(self, form):
        student = form.save(commit=False)
        photo_file = form.cleaned_data.get('image')
        full_name = f"{form.cleaned_data['first_name']} {form.cleaned_data['last_name']}"
        dormitory = form.cleaned_data.get('dormitory')

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

