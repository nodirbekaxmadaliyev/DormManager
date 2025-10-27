from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('student_name', 'amount', 'added_by', 'add_time')
    list_filter = ('add_time', 'added_by')
    search_fields = ('student_name', 'added_by__first_name', 'added_by__last_name')
    readonly_fields = ('student_name', 'added_by', 'add_time')
    date_hierarchy = 'add_time'

    def has_change_permission(self, request, obj=None):
        return False

