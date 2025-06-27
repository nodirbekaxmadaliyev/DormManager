from django.views.generic import ListView, DetailView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from student.models import Student
from django.db.models import Count
from django.http import HttpResponse
from .models import Room, Dormitory
import pandas as pd
from datetime import datetime
from django.template.loader import render_to_string

from django.views.generic.edit import CreateView, DeleteView
from django.http import JsonResponse
from django.urls import reverse_lazy
from .forms import RoomForm
from django.db.models import Count, Sum, F, ExpressionWrapper, IntegerField, Value
from django.db.models.functions import Coalesce

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

class RoomListView(ListView):
    model = Room
    template_name = 'dormitory/rooms.html'
    context_object_name = 'object_list'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if hasattr(user, 'director'):
            queryset = queryset.filter(dormitory__director=user.director)
        elif hasattr(user, 'employee'):
            queryset = queryset.filter(dormitory=user.employee.dormitory)
        else:
            return Room.objects.none()

        dormitory = self.request.GET.get('dormitory', '').strip()
        number = self.request.GET.get('number', '').strip()

        if dormitory:
            queryset = queryset.filter(dormitory__name__icontains=dormitory)
        if number:
            queryset = queryset.filter(number__icontains=number)

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
            empty_slots = total_capacity - total_students

            dormitory_stats.append({
                'name': dorm.name,
                'room_count': total_rooms,
                'student_count': total_students,
                'empty_slots': empty_slots
            })

        context["dormitory_stats"] = dormitory_stats
        return context


class DirectorOnlyMixin(UserPassesTestMixin):
    def test_func(self):
        return hasattr(self.request.user, 'director')

class DormitorySelectView(LoginRequiredMixin, DirectorOnlyMixin, ListView):
    model = Dormitory
    template_name = 'dormitory/dormitory_select.html'
    context_object_name = 'dormitories'

    def get_queryset(self):
        return Dormitory.objects.filter(director=self.request.user.director)


class DormitoryDetailView(LoginRequiredMixin, DirectorOnlyMixin, DetailView):
    model = Dormitory
    template_name = 'dormitory/dormitory_detail.html'
    context_object_name = 'dorm'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dorm = self.get_object()
        students = Student.objects.filter(dormitory=dorm)

        total_required = 0
        total_paid = 0
        total_debt = 0

        from datetime import date
        from dateutil.relativedelta import relativedelta

        today = date.today()
        for student in students:
            if not student.arrival_time:
                continue

            checkout = student.checkout_time or today
            delta = relativedelta(checkout, student.arrival_time)
            months_passed = delta.years * 12 + delta.months + 1

            monthly = dorm.monthly_payment or 0
            min_required_months = dorm.default_monthly_payment or 0

            paid_total = student.total_payment or 0
            required_total = months_passed * monthly

            # Qarzdorlikni hisoblash - `DebtStatisticsView`ga mos
            delta = relativedelta(today, student.arrival_time)
            delta_month = delta.years * 12 + delta.months + 1 - min_required_months
            if delta_month <= 0:
                debt = required_total - paid_total
            else:
                debt = (min_required_months + delta_month) * monthly - paid_total

            # Jami qiymatlarni yig‘ish
            total_required += required_total
            total_paid += paid_total
            total_debt += max(debt, 0)

        context["total_required"] = total_required
        context["total_paid"] = total_paid
        context["total_debt"] = total_debt
        return context


class DormitoryUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
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


