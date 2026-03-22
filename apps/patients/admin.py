from django.contrib import admin
from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['hrn_number', 'last_name', 'first_name', 'sex', 'age', 'phone_number']
    search_fields = ['hrn_number', 'last_name', 'first_name', 'phone_number']
    list_filter = ['sex', 'civil_status']
    readonly_fields = ['created_at', 'updated_at']
