from django import forms
from django.db.models import Sum
from django.utils import timezone
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .forms import ExpenseForm
from .models import Expense
from dormitory.models import Dormitory


class ExpenseListView(ListView):
    model = Expense
    template_name = "expenses/expense_list.html"
    context_object_name = "expenses"

    def get_queryset(self):
        user = self.request.user
        queryset = Expense.objects.all().order_by("-created_at")

        # Hodim bo‘lsa — faqat o‘z TTJsi chiqimlarini ko‘rsatish
        if hasattr(user, "employee"):
            queryset = queryset.filter(dormitory=user.employee.dormitory)

        # Direktor bo‘lsa — unga tegishli TTJlar chiqimlarini ko‘rsatish
        elif hasattr(user, "director"):
            queryset = queryset.filter(dormitory__director=user.director)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        now = timezone.now()

        # Statistikalar
        context["monthly_total"] = qs.filter(
            created_at__year=now.year,
            created_at__month=now.month
        ).aggregate(total=Sum("amount"))["total"] or 0

        context["yearly_total"] = qs.filter(
            created_at__year=now.year
        ).aggregate(total=Sum("amount"))["total"] or 0

        context["all_total"] = qs.aggregate(total=Sum("amount"))["total"] or 0

        # Direktor uchun — unga tegishli yotoqxonalarga filter
        user = self.request.user
        if hasattr(user, "director"):
            context["dormitories"] = Dormitory.objects.filter(director=user.director)
        elif hasattr(user, "employee"):
            context["dormitories"] = Dormitory.objects.filter(id=user.employee.dormitory.id)
        else:
            context["dormitories"] = Dormitory.objects.all()

        return context

class ExpenseCreateView(CreateView):
    model = Expense
    fields = ["amount", "note", "dormitory"]
    template_name = "expense/expense_form.html"
    success_url = reverse_lazy("expense_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Direktor – faqat o‘ziga biriktirilgan TTJlar
        if hasattr(user, "director"):
            context["dormitories"] = Dormitory.objects.filter(director=user.director)
        # Xodim – faqat o‘zi ishlayotgan TTJ
        elif hasattr(user, "employee"):
            context["dormitory"] = user.employee.dormitory
        else:
            context["dormitories"] = Dormitory.objects.none()

        return context

    def form_valid(self, form):
        user = self.request.user

        # Xodim uchun TTJ avtomatik biriktiriladi
        if hasattr(user, "employee"):
            form.instance.dormitory = user.employee.dormitory

        form.instance.created_by = user
        return super().form_valid(form)


class ExpenseUpdateView(UpdateView):
    model = Expense
    fields = ["amount", "note"]

    def test_func(self):
        return self.request.user.role == "director"

    def get_success_url(self):
        return reverse_lazy("expense_list")


class ExpenseDeleteView(DeleteView):
    model = Expense
    template_name = "expenses/expense_confirm_delete.html"

    def test_func(self):
        return self.request.user.role == "director"

    def get_success_url(self):
        return reverse_lazy("expense_list")
