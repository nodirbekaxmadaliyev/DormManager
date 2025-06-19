from django.contrib import admin
from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'first_name',
        'last_name',
        'faculty',
        'room',
        'phone_number',
        'is_in_dormitory',
        'arrival_time',
        'checkout_time',
        'total_payment',
        'dormitory_name',
        'has_image',
    )
    list_filter = (
        'is_in_dormitory',
        'faculty',
        'arrival_time',
        'checkout_time',
        'dormitory__name',
    )
    search_fields = (
        'first_name',
        'last_name',
        'faculty',
        'room',
        'phone_number',
        'parent_full_name',
        'parent_login',
    )
    readonly_fields = ('parent_login',)
    list_editable = ('is_in_dormitory',)
    date_hierarchy = 'arrival_time'
    ordering = ('-arrival_time',)

    def dormitory_name(self, obj):
        return obj.dormitory.name
    dormitory_name.short_description = "Yotoqxona"

    def has_image(self, obj):
        return bool(obj.image)
    has_image.boolean = True
    has_image.short_description = "Rasm mavjudmi?"
