from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Invoice

@admin.register(Invoice)
class InvoiceAdmin(ModelAdmin):
    list_display = ['invoice_number', 'booking', 'invoice_date', 'grand_total', 'status']
    search_fields = ['invoice_number', 'booking__booking_number', 'booking__customer__name']
    list_filter = ['status', 'invoice_date']
    autocomplete_fields = ['booking']
    list_select_related = ['booking', 'booking__customer']
    
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['invoice_number', 'booking', 'currency', 'status', 'subtotal', 'gst_rate', 'gst_amount', 'grand_total']
        return ['invoice_number', 'currency', 'status', 'subtotal', 'gst_rate', 'gst_amount', 'grand_total']

    def get_exclude(self, request, obj=None):
        if obj is None:
            return ['invoice_number']
        return []
        
    def has_add_permission(self, request):
        return False
