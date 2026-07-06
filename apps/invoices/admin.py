from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import Invoice, InvoiceLine, InvoiceLineTraveler

class InvoiceLineTravelerInline(TabularInline):
    model = InvoiceLineTraveler
    extra = 0
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False
        
    def has_change_permission(self, request, obj=None):
        return False
        
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

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
    list_display = ['invoice_number', 'booking', 'invoice_date', 'final_payable', 'current_invoice_value', 'balance_due', 'payment_status', 'cancellation_status', 'status']
    search_fields = ['invoice_number', 'booking__booking_number', 'booking__customer__name']
    list_filter = ['status', 'cancellation_status', 'invoice_date']
    autocomplete_fields = ['booking']
    list_select_related = ['booking', 'booking__customer']
    inlines = [InvoiceLineInline]
    
    def get_readonly_fields(self, request, obj=None):
        fields = [
            'invoice_number', 'currency', 'status', 'cancellation_status', 'invoice_date', 'due_date',
            'company_name', 'gstin', 'pan', 'address', 'phone', 'email',
            'gst_enabled', 'gst_type', 'cgst_rate', 'sgst_rate', 'igst_rate', 'tax_label_1', 'tax_label_2', 'tax_label_3',
            'supplier_total', 'service_charge_total', 'subtotal_before_tax', 'taxable_amount', 
            'cgst_amount', 'sgst_amount', 'igst_amount', 
            'grand_total', 'original_total', 'final_payable', 'booking',
            'current_invoice_value', 'balance_due', 'payment_status'
        ]
        return fields

    def has_add_permission(self, request):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return False

    actions = ['action_cancellation_wizard']

    @admin.action(description="Cancel Passengers or Services (Wizard)")
    def action_cancellation_wizard(self, request, queryset):
        from django.shortcuts import redirect
        from django.contrib import messages
        
        if queryset.count() != 1:
            messages.error(request, "Please select exactly one Invoice to initiate cancellation.")
            return
            
        invoice = queryset.first()
        return redirect('cancellation_wizard', invoice_id=invoice.id)
