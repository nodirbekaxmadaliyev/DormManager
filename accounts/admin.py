from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Director
from django.utils.translation import gettext_lazy as _


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'first_name', 'last_name', 'role', 'phone_number', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'phone_number')
    ordering = ('id',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Shaxsiy maʼlumotlar'), {
         'fields': ('first_name', 'last_name', 'phone_number', 'photo')}),
        (_('Lavozim va ish vaqti'), {
         'fields': ('role', 'work_start', 'work_end', 'hire_date', 'salary', 'is_in_dormitory')}),
        (_('Ruxsatlar'), {
         'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Muhim sanalar'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'first_name', 'last_name', 'role', 'phone_number', 'photo', 'is_staff', 'is_active'),
        }),
    )


@admin.register(Director)
class DirectorAdmin(admin.ModelAdmin):
    list_display = ('user_full_name',)
    search_fields = ('user__first_name', 'user__last_name', 'user__username')

    def user_full_name(self, obj):
        return obj.user.get_full_name()
    user_full_name.short_description = 'Direktor'
