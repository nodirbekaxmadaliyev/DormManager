from datetime import datetime, timedelta
from django.views.generic import ListView
from utils.hikvision import getLogs
from dormitory.models import Dormitory
from django.http import HttpResponse
import pandas as pd
import io
import zipfile
from student.models import Student
from accounts.models import CustomUser


class LogListView(ListView):
    template_name = 'Logs/home.html'
    context_object_name = 'logs'

    def get_queryset(self):
        self.user = self.request.user
        self.dormitory_id = self.request.GET.get('dormitory')
        self.start_time_raw = self.request.GET.get('start_time')
        self.end_time_raw = self.request.GET.get('end_time')

        if self.start_time_raw:
            self.start_time = self.start_time_raw.replace('T', ' ')
        else:
            self.start_time = (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")

        if self.end_time_raw:
            self.end_time = self.end_time_raw.replace('T', ' ')
        else:
            self.end_time = datetime.now().strftime("%Y-%m-%d %H:%M")

        # 🎯 Yotoqxona obyektini olish
        self.dormitory = None
        if self.dormitory_id:
            try:
                if hasattr(self.user, 'director'):
                    self.dormitory = Dormitory.objects.get(id=self.dormitory_id, director=self.user.director)
                elif hasattr(self.user, 'employee'):
                    self.dormitory = Dormitory.objects.get(id=self.user.employee.dormitory.id)
            except Dormitory.DoesNotExist:
                self.dormitory = None

        # ✅ Loglarni olish
        if self.dormitory:
            self.logs, self.errors = getLogs(self.dormitory, self.start_time, self.end_time)
        else:
            self.logs, self.errors = [], ["Yotoqxona tanlanmagan yoki mavjud emas."]

        # 🔄 Foydalanuvchiga tegishli yotoxonalarni topish
        if hasattr(self.user, 'director'):
            dormitories = Dormitory.objects.filter(director=self.user.director)
        elif hasattr(self.user, 'employee'):
            dormitories = Dormitory.objects.filter(id=self.user.employee.dormitory.id) if self.user.employee.dormitory else Dormitory.objects.none()
        else:
            dormitories = Dormitory.objects.none()

        self.extra_context = {
            "errors": self.errors,
            "start_time_default": self.start_time,
            "end_time_default": self.end_time,
            "logsNumber": len(self.logs),
            "dormitories": dormitories,
            "selected_dormitory": int(self.dormitory_id) if self.dormitory_id else None,
        }

        return self.logs

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        if request.GET.get("export") == "excel" and queryset:
            employee_data = []
            student_data = []

            for log in queryset:
                try:
                    user_id = int(log.get("employeeNo", 0))
                except (ValueError, TypeError):
                    continue

                log_time = log.get("time", "")
                status = log.get("status", "")

                if user_id >= 10000:
                    # Student
                    try:
                        student = Student.objects.get(id=user_id)
                    except Student.DoesNotExist:
                        continue

                    student_data.append({
                        "ID": student.id,
                        "F.I.Sh.": f"{student.first_name} {student.last_name}",
                        "Fakulteti": student.faculty,
                        "Xonasi": student.room,
                        "Telefon": student.phone_number,
                        "Ota-ona F.I.Sh.": student.parent_full_name,
                        "Shartnoma raqami": student.contract_number,
                        "Kelgan vaqti": student.arrival_time,
                        "Chiqqan vaqti": student.checkout_time,
                        "Yotoqxona": student.dormitory.name,
                        "Ichkaridami": "Ha" if student.is_in_dormitory else "Yo‘q",
                        "Log vaqti": log_time,
                        "Harakat": status,
                    })
                else:
                    # Employee yoki direktor
                    try:
                        user = CustomUser.objects.get(id=user_id)
                    except CustomUser.DoesNotExist:
                        continue

                    if user.role == "director":
                        dorms = Dormitory.objects.filter(director__user=user)
                        location = ", ".join([d.name for d in dorms])
                    elif user.role == "employee" and hasattr(user, "employee") and user.employee.dormitory:
                        location = user.employee.dormitory.name
                    else:
                        location = "-"

                    employee_data.append({
                        "ID": user.id,
                        "F.I.Sh.": user.get_full_name(),
                        "Lavozimi": "Direktor" if user.role == "director" else "Xodim",
                        "Telefon": user.phone_number,
                        "Ish vaqti": f"{user.work_start} - {user.work_end}" if user.work_start and user.work_end else "-",
                        "Joylashuvi": location,
                        "Ichkaridami": "Ha" if user.is_in_dormitory else "Yo‘q",
                        "Log vaqti": log_time,
                        "Harakat": status,
                    })

            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                if employee_data:
                    df1 = pd.DataFrame(employee_data)
                    df1.index += 1
                    df1.insert(0, "№", df1.index)
                    excel_buffer = io.BytesIO()
                    df1.to_excel(excel_buffer, index=False)
                    zip_file.writestr("Hodimlar_loglari.xlsx", excel_buffer.getvalue())

                if student_data:
                    df2 = pd.DataFrame(student_data)
                    df2.index += 1
                    df2.insert(0, "№", df2.index)
                    excel_buffer = io.BytesIO()
                    df2.to_excel(excel_buffer, index=False)
                    zip_file.writestr("Talabalar_loglari.xlsx", excel_buffer.getvalue())

            zip_buffer.seek(0)
            response = HttpResponse(zip_buffer, content_type='application/zip')
            filename = f"loglar_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.zip"
            response['Content-Disposition'] = f'attachment; filename={filename}'
            return response

        return super().get(request, *args, **kwargs)

