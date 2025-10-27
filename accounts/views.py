import os
import tempfile
from django.conf import settings
from django.views.generic import ListView, CreateView
from django.views.generic import UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import CustomUser, Director
from .forms import CustomUserUpdateForm, EmployeeCreateForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import render, redirect
from  dormitory.models import Dormitory
import pandas as pd
from utils.hikvision import add_user_to_devices, delete_user_from_devices, update_user_on_devices, update_dormitory_status
from django.contrib import messages
from employee.models import Employee

class EmployeePage(ListView):
    model = Employee
    template_name = 'accounts/employees.html'
    context_object_name = 'employees'

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if hasattr(user, 'director'):
            queryset = queryset.filter(dormitory__director=user.director)
        else:
            queryset = queryset.filter(dormitory__employees__user=user)

        # Qidiruv filtrlari
        first_name_q = self.request.GET.get("first_name", "").strip()
        last_name_q = self.request.GET.get("last_name", "").strip()
        dormitory_name_q = self.request.GET.get("dormitory_name", "").strip()

        if first_name_q:
            queryset = queryset.filter(user__first_name__icontains=first_name_q)
        if last_name_q:
            queryset = queryset.filter(user__last_name__icontains=last_name_q)
        if dormitory_name_q:
            queryset = queryset.filter(dormitory__name__icontains=dormitory_name_q)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        context["total_count"] = queryset.count()
        context["device_errors"] = self.request.session.pop("device_errors", None)

        user = self.request.user
        role = getattr(user, 'role', None)
        director = getattr(user, 'director', None)
        employee = getattr(user, 'employee', None)

        if role == 'director' and director:
            dormitories = Dormitory.objects.filter(director=director)
            context["all_employee_count"] = Employee.objects.filter(
                dormitory__in=dormitories
            ).count()

            dormitory_stats = []
            for dorm in dormitories:
                total = dorm.employees.count()
                in_dorm = dorm.employees.filter(user__is_in_dormitory=True).count()
                dormitory_stats.append({
                    "name": dorm.name,
                    "total": total,
                    "in_dorm": in_dorm
                })
            context["dormitory_stats"] = dormitory_stats

        elif role == 'employee' and employee and employee.dormitory:
            dorm = employee.dormitory
            total = dorm.employees.count()
            in_dorm = dorm.employees.filter(user__is_in_dormitory=True).count()
            context["dormitory_stats"] = [{
                "name": dorm.name,
                "total": total,
                "in_dorm": in_dorm
            }]

        return context

class EmployeeUpdateView(UpdateView):
    model = CustomUser
    form_class = CustomUserUpdateForm
    template_name = 'accounts/employee_update.html'
    success_url = reverse_lazy('employees')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"{self.object.first_name} ma'lumotlarini tahrirlash"
        return context

    def form_valid(self, form):
        response = super().form_valid(form)

        employee_id = str(self.object.pk)
        full_name = f"{self.object.first_name} {self.object.last_name}"

        try:
            dormitory = self.object.employee.dormitory  # <-- to‘g‘ri aloqador modelga murojaat
        except AttributeError:
            messages.error(self.request, "Foydalanuvchining hodim ma'lumotlari topilmadi.")
            return redirect('employees')

        success, reason = update_user_on_devices(dormitory, employee_id, full_name)
        if not success:
            messages.error(self.request, f"Foydalanuvchini qurilmalarda yangilashda xatolik: {reason}")
            return redirect('employees')

        return response

class EmployeeDeleteView(DeleteView):
    model = CustomUser
    success_url = reverse_lazy('employees')

    def form_valid(self, request, *args, **kwargs):
        self.object = self.get_object()
        employee_id = str(self.object.pk)

        try:
            dormitory = self.object.employee.dormitory  # to‘g‘ri bog‘langan model
        except AttributeError:
            messages.error(request, "Foydalanuvchining hodim ma'lumotlari topilmadi.")
            return self.get(request, *args, **kwargs)

        success, reason = delete_user_from_devices(dormitory, employee_id)
        if not success:
            messages.error(request, f"Foydalanuvchi qurilmalardan o‘chmadi: {reason}")
            return self.get(request, *args, **kwargs)

        # Suratni o‘chirish
        if self.object.photo:
            photo_path = os.path.join(settings.MEDIA_ROOT, str(self.object.photo))
            if os.path.exists(photo_path):
                os.remove(photo_path)

        return super().delete(request, *args, **kwargs)

def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Parolingiz muvaffaqiyatli o\'zgartirildi!')
            return redirect('dashboard')  # O'zgartirishingiz mumkin
        else:
            messages.error(request, 'Iltimos, xatolarni to\'g\'rilang.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'accounts/change_password.html', {'form': form})

class EmployeeCreateView(CreateView):
    model = CustomUser
    form_class = EmployeeCreateForm
    template_name = 'accounts/employee_add.html'
    success_url = reverse_lazy('employees')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        try:
            kwargs['director'] = Director.objects.get(user=self.request.user)
        except Director.DoesNotExist:
            kwargs['director'] = None
        return kwargs

    def form_valid(self, form):
        user = form.save(commit=False)

        user.first_name = form.cleaned_data['first_name']
        user.last_name = form.cleaned_data['last_name']
        user.role = 'Xodim'

        photo_file = form.cleaned_data.get('photo')
        full_name = f"{form.cleaned_data['first_name']} {form.cleaned_data['last_name']}"
        dormitory = form.cleaned_data.get('dormitory')

        if not photo_file:
            messages.error(self.request, "Surat yuklanmagan. Iltimos, rasmni tanlang.")
            return render(self.request, self.template_name, {'form': form})

        # Faylni vaqtincha saqlaymiz
        tmp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg', mode='wb') as tmp:
                for chunk in photo_file.chunks():
                    tmp.write(chunk)
                tmp_file_path = tmp.name
            tmp.close()

            user.save()
            Employee.objects.create(user=user, dormitory=dormitory)

            success, reason = add_user_to_devices(dormitory, str(user.id), full_name, tmp_file_path)
            if os.path.exists(tmp_file_path):
                try:
                    os.remove(tmp_file_path)
                except Exception as e:
                    print(f"Faylni o‘chirishda xatolik: {e}")

            if success:
                messages.success(self.request, "Hodim saqlandi va qurilmalarga qo‘shildi.")
                return redirect(self.success_url)
            else:
                user.delete()
                messages.error(self.request, f"Hodim qurilmalarga qo‘shilmadi: {reason}")
                return render(self.request, self.template_name, {'form': form})

        except Exception as e:
            if tmp_file_path and os.path.exists(tmp_file_path):
                try:
                    os.remove(tmp_file_path)
                except Exception as e:
                    print(f"Faylni o‘chirishda xatolik: {e}")
            messages.error(self.request, f"Kutilmagan xatolik: {str(e)}")
            return render(self.request, self.template_name, {'form': form})

    def form_invalid(self, form):
        messages.error(self.request, f"Ma'lumotlarda xatolik mavjud. {form.errors}")
        return super().form_invalid(form)
