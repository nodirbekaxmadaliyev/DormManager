from django.contrib import admin
from .models import Student

# 🔹 1. Rasm mavjud yoki yo‘qligiga qarab filter yaratamiz
class HasImageFilter(admin.SimpleListFilter):
    title = 'Rasm mavjudligi'
    parameter_name = 'has_image'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Rasmi bor'),
            ('no', 'Rasmi yo‘q'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(image__isnull=True).exclude(image__exact='')
        if self.value() == 'no':
            return queryset.filter(image__isnull=True) | queryset.filter(image__exact='')
        return queryset


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
        HasImageFilter,  # 🔥 Yangi filter shu yerda
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
