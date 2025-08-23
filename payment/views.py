from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from student.models import Student
from datetime import date
from dateutil.relativedelta import relativedelta
from django.views.generic import ListView
from django.views import View
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.db.models import Q
from datetime import datetime
import pandas as pd
from .models import Payment, Student

from django.contrib import messages
from django.shortcuts import redirect
from utils.hikvision import block_user_on_devices, open_user_on_devices

class DebtStatisticsView(ListView):
    model = Student
    template_name = 'payment/statistics.html'
    context_object_name = 'students'

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        context = self.get_context_data()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            html = render_to_string("payment/statistics.html", context, request=request)
            return JsonResponse({'table_html': html})

        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """🔹 Qarzdorlarni bloklash yoki barcha talabani ochish"""
        action = request.POST.get("action")
        students = self.get_queryset()

        if action == "block_debtors":
            blocked = 0
            for student in students:
                if student.debt > 0:
                    ok, _ = block_user_on_devices(student.dormitory, str(student.pk))
                    if ok:
                        blocked += 1
            messages.success(request, f"{blocked} ta qarzdor bloklandi.")
            return redirect("debt_statistics")

        elif action == "open_all":
            opened = 0
            for student in students:
                ok, _ = open_user_on_devices(student.dormitory, str(student.pk))
                if ok:
                    opened += 1
            messages.success(request, f"{opened} ta talaba blokdan chiqarildi.")
            return redirect("debt_statistics")

        messages.error(request, "Noto‘g‘ri amal.")
        return redirect("debt_statistics")

    def get_queryset(self):
        # 🔹 Siz yozganidek o‘zgarishsiz
        user = self.request.user

        if hasattr(user, 'director'):
            dormitories = user.director.dormitories.all()
        elif hasattr(user, 'employee'):
            dormitories = [user.employee.dormitory]
        else:
            return Student.objects.none()

        queryset = Student.objects.filter(dormitory__in=dormitories)

        q = self.request.GET.get('q', '').strip()
        debt_filter = self.request.GET.get('debt_filter', '')

        if q:
            queryset = queryset.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q))

        results = []
        today = date.today()

        for student in queryset:
            if not student.arrival_time:
                continue

            checkout = student.checkout_time or today
            monthly = student.dormitory.monthly_payment or 0
            min_required_months = student.dormitory.default_monthly_payment or 0
            paid_total = student.total_payment or 0

            delta = relativedelta(checkout, student.arrival_time)
            months_passed = delta.years * 12 + delta.months
            extra_days = (checkout - (student.arrival_time + relativedelta(months=months_passed))).days

            daily_payment = monthly / 30

            if months_passed < min_required_months:
                required_total = months_passed * monthly + extra_days * daily_payment
            else:
                required_total = min_required_months * monthly
                remaining_months = months_passed - min_required_months
                required_total += remaining_months * monthly + extra_days * daily_payment

            debt = max(required_total - paid_total, 0)

            if (
                debt_filter == 'debtors' and debt > 0
                or debt_filter == 'no_debt' and debt == 0
                or debt_filter == ''
            ):
                student.months_passed = months_passed
                student.extra_days = extra_days
                student.required_total = round(required_total, 2)
                student.paid_total = paid_total
                student.debt = round(debt, 2)
                results.append(student)

        return results

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['q'] = self.request.GET.get('q', '')
        context['debt_filter'] = self.request.GET.get('debt_filter', '')

        students = context['students']
        context['total_required'] = sum(s.required_total for s in students)
        context['total_paid'] = sum(s.paid_total for s in students)
        context['total_debt'] = sum(s.debt for s in students)

        return context


class StudentSearchAPIView(View):
    def get(self, request):
        q = request.GET.get("q", "")
        user = request.user

        if hasattr(user, 'director'):
            students = Student.objects.filter(
                Q(first_name__icontains=q) | Q(last_name__icontains=q),
                dormitory__director=user.director
            )

        elif hasattr(user, 'employee'):
            dormitory = user.employee.dormitory
            students = Student.objects.filter(
                Q(first_name__icontains=q) | Q(last_name__icontains=q),
                dormitory=dormitory
            )

        else:
            students = Student.objects.none()

        results = [
            {"id": s.id, "text": f"{s.first_name} {s.last_name} ({s.room})"}
            for s in students[:20]
        ]
        return JsonResponse({"results": results})

class PaymentListView(ListView):
    model = Payment
    template_name = 'payment/home.html'
    context_object_name = 'object_list'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if hasattr(user, 'employee'):
            queryset = queryset.filter(student__dormitory=user.employee.dormitory)
        elif hasattr(user, 'director'):
            dormitories = user.director.dormitories.all()
            queryset = queryset.filter(student__dormitory__in=dormitories)

        # 🔍 Qidiruv parametrlari
        student_name = self.request.GET.get('student_name', '').strip()
        amount = self.request.GET.get('amount', '').strip()
        added_by = self.request.GET.get('added_by', '').strip()

        if student_name:
            queryset = queryset.filter(student_name__icontains=student_name)

        if amount:
            queryset = queryset.filter(amount__icontains=amount)  # matn sifatida

        if added_by:
            queryset = queryset.filter(
                Q(added_by__first_name__icontains=added_by) |
                Q(added_by__last_name__icontains=added_by)
            )

        return queryset.order_by('-add_time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_count'] = self.get_queryset().count()

        context['student_name'] = self.request.GET.get('student_name', '')
        context['amount'] = self.request.GET.get('amount', '')
        context['added_by'] = self.request.GET.get('added_by', '')

        user = self.request.user
        if hasattr(user, 'director'):
            dormitories = user.director.dormitories.all()
            context['students'] = Student.objects.filter(dormitory__in=dormitories)
        elif hasattr(user, 'employee'):
            context['students'] = Student.objects.filter(dormitory=user.employee.dormitory)
        else:
            context['students'] = Student.objects.none()

        return context

    def get(self, request, *args, **kwargs):
        if request.GET.get("export") == "excel":
            return self.export_to_excel()

        self.object_list = self.get_queryset()
        context = self.get_context_data()

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            html = render_to_string("payment/_payments_table.html", context, request=request)
            return HttpResponse(html)

        return self.render_to_response(context)

    def export_to_excel(self):
        queryset = self.get_queryset()

        df = pd.DataFrame(list(queryset.values(
            'student__first_name', 'student__last_name', 'student__room',
            'amount', 'add_time'
        )))

        df.index += 1
        df.insert(0, '№', df.index)

        df.rename(columns={
            'student__first_name': 'Ismi',
            'student__last_name': 'Familiyasi',
            'student__room': 'Xonasi',
            'amount': 'To‘lov miqdori',
            'add_time': 'Qo‘shilgan vaqt'
        }, inplace=True)

        df['Qo‘shilgan vaqt'] = pd.to_datetime(df['Qo‘shilgan vaqt']).dt.strftime('%Y-%m-%d %H:%M')

        now = datetime.now().strftime("%Y-%m-%d_%H-%M")
        filename = f"tolovlar_{now}.xlsx"

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename={filename}'
        df.to_excel(response, index=False)
        return response

class PaymentCreateView(LoginRequiredMixin, CreateView):
    model = Payment
    fields = ['student', 'amount']

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user

        if hasattr(user, 'director'):
            # Agar direktor bo‘lsa, u boshqaradigan yotoqxonalardagi talabalarni chiqarish
            dormitories = user.director.dormitories.all()
            form.fields['student'].queryset = Student.objects.filter(dormitory__in=dormitories)

        elif hasattr(user, 'employee'):
            # Agar xodim bo‘lsa, faqat o‘z yotoqxonasidagi talabalarni ko‘rsatish
            dormitory = user.employee.dormitory
            form.fields['student'].queryset = Student.objects.filter(dormitory=dormitory)

        else:
            # Admin yoki boshqa foydalanuvchilar uchun barcha talabalar
            form.fields['student'].queryset = Student.objects.none()

        return form

    def form_valid(self, form):
        self.object = form.save(commit=False)
        student = self.object.student
        self.object.student_name = f"{student.first_name} {student.last_name}"
        self.object.added_by = self.request.user
        self.object.save()

        student.total_payment = (student.total_payment or 0) + float(self.object.amount)
        student.save()

        return JsonResponse({'success': True})

    def form_invalid(self, form):
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)


