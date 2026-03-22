from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['pk', 'patient', 'patient_type', 'payment_method', 'is_complete', 'created_at']
    list_filter = ['patient_type', 'payment_method', 'is_complete', 'created_at']
    filter_horizontal = ['services']
    readonly_fields = ['queue_numbers', 'signature_image', 'created_at', 'updated_at']
    search_fields = ['patient__last_name', 'patient__hrn_number']
