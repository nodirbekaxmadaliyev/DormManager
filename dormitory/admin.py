from django.contrib import admin
from .models import Dormitory, Device, Room


@admin.register(Dormitory)
class DormitoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'director_full_name')
    search_fields = ('name', 'address', 'director__user__first_name', 'director__user__last_name')

    def director_full_name(self, obj):
        return obj.director.user.get_full_name()
    director_full_name.short_description = "Direktor"


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('id', 'dormitory_name', 'ipaddress', 'username', 'entrance')
    search_fields = ('ipaddress', 'username', 'dormitory__name')
    list_filter = ('entrance',)

    def dormitory_name(self, obj):
        return obj.dormitory.name
    dormitory_name.short_description = "Yotoqxona"

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('number', 'dormitory', 'size')
    list_filter = ('dormitory',)
    search_fields = ('number', 'dormitory__name')
    ordering = ('dormitory__name', 'number')
