from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import Invoice, InvoiceLine

class InvoiceLineInline(TabularInline):
    model = InvoiceLine
    extra = 0
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False
        
    def has_change_permission(self, request, obj=None):
        return False
        
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

@admin.register(Invoice)
class InvoiceAdmin(ModelAdmin):
    list_display = ['invoice_number', 'booking', 'invoice_date', 'original_total', 'credit_applied', 'final_payable', 'status']
    search_fields = ['invoice_number', 'booking__booking_number', 'booking__customer__name']
    list_filter = ['status', 'invoice_date']
    autocomplete_fields = ['booking']
    list_select_related = ['booking', 'booking__customer']
    inlines = [InvoiceLineInline]
    
    def get_readonly_fields(self, request, obj=None):
        fields = [
            'invoice_number', 'currency', 'status', 'invoice_date', 'due_date',
            'company_name', 'gstin', 'pan', 'address', 'phone', 'email',
            'gst_enabled', 'gst_type', 'cgst_rate', 'sgst_rate', 'igst_rate', 'tax_label_1', 'tax_label_2', 'tax_label_3',
            'supplier_total', 'service_charge_total', 'subtotal_before_tax', 'taxable_amount', 
            'cgst_amount', 'sgst_amount', 'igst_amount', 
            'grand_total', 'original_total', 'credit_applied', 'final_payable', 'booking'
        ]
        return fields

    def has_add_permission(self, request):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return False
