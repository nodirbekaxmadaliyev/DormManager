from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy# modelingiz joylashgan joyga qarab sozlang
from django.views.generic import ListView, DetailView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from student.models import Student
from dormitory.models import Dormitory  # yoki sizdagi joylashuvga qarab

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


