from django import forms
from django.db.models import Sum
from django.utils import timezone
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .forms import ExpenseForm
from .models import Expense
from dormitory.models import Dormitory


class ExpenseListView(LoginRequiredMixin, ListView):
    model = Expense
    template_name = "expenses/expense_list.html"
    context_object_name = "expenses"

    def get_queryset(self):
        return Expense.objects.all().order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        now = timezone.now()

        context["monthly_total"] = qs.filter(
            created_at__year=now.year,
            created_at__month=now.month
        ).aggregate(total=Sum("amount"))["total"] or 0

        context["yearly_total"] = qs.filter(
            created_at__year=now.year
        ).aggregate(total=Sum("amount"))["total"] or 0

        context["dormitories"] = Dormitory.objects.all()

        context["all_total"] = qs.aggregate(total=Sum("amount"))["total"] or 0
        return context

class ExpenseCreateView(CreateView):
    model = Expense
    fields = ["amount", "note", 'dormitory']
    success_url = reverse_lazy("expense_list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user

        if hasattr(self.request.user, "role") and self.request.user.role == "employee":
            form.instance.dormitory = self.request.user.dormitory

        return super().form_valid(form)

class ExpenseUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Expense
    fields = ["amount", "note"]

    def test_func(self):
        return self.request.user.role == "director"

    def get_success_url(self):
        return reverse_lazy("expense_list")


class ExpenseDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Expense
    template_name = "expenses/expense_confirm_delete.html"

    def test_func(self):
        return self.request.user.role == "director"

    def get_success_url(self):
        return reverse_lazy("expense_list")
