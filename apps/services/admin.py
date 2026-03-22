from django.contrib import admin
from .models import Service, Doctor, QueueCounter


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['code', 'label', 'prefix', 'icon', 'is_active', 'display_order']
    list_editable = ['is_active', 'display_order']


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'specialization', 'room_number', 'availability']
    list_filter = ['availability']
    list_editable = ['availability']
    search_fields = ['first_name', 'last_name', 'specialization']


@admin.register(QueueCounter)
class QueueCounterAdmin(admin.ModelAdmin):
    list_display = ['service', 'date', 'count']
    list_filter = ['date', 'service']
    readonly_fields = ['service', 'date', 'count']
