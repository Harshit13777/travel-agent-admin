from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = ['amount', 'invoice', 'date', 'method', 'received_by']
    search_fields = ['reference_number', 'invoice__invoice_number']
    list_filter = ['method']
