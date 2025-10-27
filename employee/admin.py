# employees/admin.py
from django.contrib import admin
from .models import Employee
from accounts.models import CustomUser

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('user_full_name', 'get_username', 'get_role', 'dormitory')
    readonly_fields = ('user_info',)

    def user_full_name(self, obj):
        return obj.user.get_full_name()
    def get_username(self, obj):
        return obj.user.username
    def get_role(self, obj):
        return obj.user.get_role_display()

    user_full_name.short_description = "F.I.Sh"
    get_username.short_description = "Username"
    get_role.short_description = "Lavozimi"

    def user_info(self, obj):
        return f"""
        -- Foydalanuvchi ismi: {obj.user.first_name} {obj.user.last_name}<br>
        -- Username: {obj.user.username}<br>
        -- Email: {obj.user.email}<br>
        -- Telefon: {obj.user.phone_number}<br>
        -- Lavozim: {obj.user.get_role_display()}<br>
        -- Ish vaqti: {obj.user.work_start} - {obj.user.work_end}<br>
        -- Maosh: {obj.user.salary} so‘m<br>
        -- Ishga kirgan sana: {obj.user.hire_date}
        """
    user_info.allow_tags = True
    user_info.short_description = "Foydalanuvchi ma’lumotlari"
