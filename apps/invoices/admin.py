from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import Invoice
from apps.payments.models import Payment

class PaymentInline(TabularInline):
    model = Payment
    extra = 1

@admin.register(Invoice)
class InvoiceAdmin(ModelAdmin):
    list_display = ['invoice_number', 'booking', 'invoice_type', 'total_amount', 'status']
    search_fields = ['invoice_number', 'booking__booking_number']
    list_filter = ['invoice_type', 'status']
    inlines = [PaymentInline]
