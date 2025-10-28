from student.models import Student
from decimal import Decimal
from datetime import date
from dateutil.relativedelta import relativedelta
from django.views.generic import ListView, DetailView, UpdateView

from django.contrib import messages
from django.http import HttpResponse
from .models import Room, Dormitory
import pandas as pd
from datetime import datetime
from django.template.loader import render_to_string
from django.shortcuts import redirect
from django.views.generic.edit import CreateView, DeleteView
from django.http import JsonResponse
from django.urls import reverse_lazy
from .forms import RoomForm
from django.db.models import Count, F, IntegerField, Value, Case, When
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from dateutil.relativedelta import relativedelta
from django.views.generic import DetailView
from utils.utils import filter_by_user_role

def load_rooms(request):
    dormitory_id = request.GET.get('dormitory')
    rooms = Room.objects.filter(dormitory_id=dormitory_id).values('id', 'number')
    return JsonResponse(list(rooms), safe=False)

class RoomCreateView(CreateView):
    model = Room
    form_class = RoomForm
    template_name = 'dormitory/room_form.html'  # ishlatilmaydi, modalda AJAX bo'ladi
    success_url = reverse_lazy('rooms')

    def get(self, request, *args, **kwargs):
        form = self.get_form()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            html = render_to_string('dormitory/room_form.html', {'form': form}, request=request)
            return JsonResponse({'form_html': html})
        return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'errors': form.errors}, status=400)
        return super().form_invalid(form)

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'message': 'Xona qo‘shildi!'})
        return super().form_valid(form)

class RoomUpdateView(UpdateView):
    model = Room
    form_class = RoomForm
    template_name = 'dormitory/room_update.html'
    success_url = reverse_lazy('rooms')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

class RoomDetailView(DetailView):
    model = Room
    template_name = 'dormitory/room_detail.html'
    context_object_name = 'room'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        room = self.object
        students = room.students.all()
        context['students'] = students
        context['empty_slots'] = room.size - students.count()
        return context

class RoomDeleteView(DeleteView):
    model = Room
    success_url = reverse_lazy('rooms')
    template_name = 'dormitory/room_confirm_delete.html'

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Agar xonada talaba bo‘lsa
        if hasattr(self.object, 'students') and self.object.students.exists():
            messages.error(request, "❌ Bu xonada talaba joylashgan, uni o‘chirib bo‘lmaydi.")
            return redirect(self.success_url)

        return super().post(request, *args, **kwargs)

class RoomListView(ListView):
    model = Room
    template_name = 'dormitory/rooms.html'
    context_object_name = 'object_list'
    paginate_by = 20


    def get_queryset(self):

        queryset = super().get_queryset()
        queryset = filter_by_user_role(queryset, self.request.user)

        dormitory_q = self.request.GET.get('dormitory', '').strip()
        number_q = self.request.GET.get('number', '').strip()
        status_q = self.request.GET.get('status', '').strip()

        # Har bir xonadagi talabalar sonini hisoblash
        queryset = queryset.annotate(occupied_count=Count('students'))

        # 🔹 Bo‘sh joylar sonini hisoblash (room.empty_slots)
        queryset = queryset.annotate(
            empty_slots=Case(
                When(size__gt=F('occupied_count'), then=F('size') - F('occupied_count')),
                default=Value(0),
                output_field=IntegerField()
            )
        )

        # Filtrlar
        if dormitory_q:
            queryset = queryset.filter(dormitory__name__icontains=dormitory_q)
        if number_q:
            queryset = queryset.filter(number__icontains=number_q)

        if status_q == 'free':
            queryset = queryset.filter(occupied_count__lt=F('size'))
        elif status_q == 'full':
            queryset = queryset.filter(occupied_count__gte=F('size'))

        return queryset.order_by('dormitory__name', 'number')

    def get(self, request, *args, **kwargs):
        if request.GET.get("export") == "excel":
            return self.export_to_excel(self.get_queryset())
        return super().get(request, *args, **kwargs)

    def export_to_excel(self, queryset):
        df = pd.DataFrame(list(queryset.values(
            'dormitory__name', 'number', 'size'
        )))
        df.index = df.index + 1
        df.insert(0, '№', df.index)
        df.rename(columns={
            'dormitory__name': 'Yotoqxona',
            'number': 'Xona raqami',
            'size': 'Sig‘imi'
        }, inplace=True)

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        now = datetime.now().strftime("%Y-%m-%d_%H-%M")
        filename = f"xonalar_{now}.xlsx"
        response['Content-Disposition'] = f'attachment; filename={filename}'
        df.to_excel(response, index=False)
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if hasattr(user, 'director'):
            dormitories = Dormitory.objects.filter(director=user.director).prefetch_related('rooms')
        elif hasattr(user, 'employee'):
            dormitories = Dormitory.objects.filter(id=user.employee.dormitory_id).prefetch_related('rooms')
        else:
            dormitories = Dormitory.objects.none()

        context["total_count"] = self.get_queryset().count()
        context["dormitories"] = dormitories

        dormitory_stats = []
        for dorm in dormitories:
            rooms = dorm.rooms.all().annotate(occupied_count=Count('students'))
            total_rooms = rooms.count()
            total_students = sum(room.occupied_count for room in rooms)
            total_capacity = sum(room.size for room in rooms)
            empty_slots = max(0, total_capacity - total_students)

            dormitory_stats.append({
                'name': dorm.name,
                'room_count': total_rooms,
                'student_count': total_students,
                'capacity': total_capacity,
                'empty_slots': empty_slots,
            })

        context["dormitory_stats"] = dormitory_stats
        return context

class DormitorySelectView(ListView):
    model = Dormitory
    template_name = 'dormitory/dormitory_select.html'
    context_object_name = 'dormitories'

    def get_queryset(self):
        user = self.request.user

        # Agar foydalanuvchi direktor bo‘lsa — barcha o‘z yotoqxonalari
        if hasattr(user, 'director'):
            return Dormitory.objects.filter(director=user.director)

        # Agar foydalanuvchi xodim bo‘lsa — faqat o‘zi bog‘langan yotoqxona
        elif hasattr(user, 'employee') and user.employee.dormitory:
            return Dormitory.objects.filter(pk=user.employee.dormitory.pk)

        # Aks holda — hech narsa qaytarilmaydi
        return Dormitory.objects.none()


class DormitoryDetailView(DetailView):
    model = Dormitory
    template_name = 'dormitory/dormitory_detail.html'
    context_object_name = 'dorm'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dorm = self.get_object()
        students = Student.objects.filter(dormitory=dorm).select_related('dormitory')

        total_required = Decimal('0.00')
        total_paid = Decimal('0.00')
        total_debt = Decimal('0.00')

        this_year = date.today().year
        july1_this_year = date(this_year, 7, 1)
        today = july1_this_year if date.today() < july1_this_year else date(this_year + 1, 7, 1)
        TWO_PLACES = Decimal('0.01')

        for student in students:
            if not student.arrival_time:
                continue

            checkout = student.checkout_time or today
            monthly = Decimal(dorm.monthly_payment or 0)
            min_required_months = Decimal(dorm.default_monthly_payment or 0)
            paid_total = Decimal(student.total_payment or 0)

            delta = relativedelta(checkout, student.arrival_time)
            months_passed = delta.years * 12 + delta.months
            extra_days = (checkout - (student.arrival_time + relativedelta(months=months_passed))).days

            daily_payment = monthly / Decimal(30) if monthly else Decimal(0)

            # 🔹 Xuddi DebtStatisticsView dagidek mantiq:
            if Decimal(months_passed) < min_required_months:
                required_total = Decimal(months_passed) * monthly + Decimal(extra_days) * daily_payment
            else:
                required_total = min_required_months * monthly

            debt = max(required_total - paid_total, Decimal(0))

            # 🔹 Yaxlitlash
            required_total = required_total.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            paid_total = paid_total.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            debt = debt.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

            total_required += required_total
            total_paid += paid_total
            total_debt += debt

        context["total_required"] = total_required.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        context["total_paid"] = total_paid.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        context["total_debt"] = total_debt.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        return context

class DormitoryUpdateView(UpdateView):
    model = Dormitory
    fields = ['name', 'address', 'monthly_payment', 'default_monthly_payment']
    template_name = 'dormitory/update.html'

    def get_success_url(self):
        return reverse_lazy('dormitory_detail', kwargs={'pk': self.object.pk})

    def test_func(self):
        user = self.request.user
        if hasattr(user, 'director'):
            return self.get_object().director == user.director
        return False


