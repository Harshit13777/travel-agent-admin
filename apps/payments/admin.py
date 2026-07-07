from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = ['amount', 'invoice', 'date', 'method', 'received_by']
    search_fields = ['reference_number', 'invoice__invoice_number']
    list_filter = ['method']
    list_select_related = ['invoice', 'received_by']
    autocomplete_fields = ['invoice', 'received_by']
    
    def has_add_permission(self, request):
        return True # Handled in form validation or save_model normally, but we can't easily check invoice here since obj is None for add. Actually we can let them add, but they will fail in form clean if invoice is closed.

    def has_change_permission(self, request, obj=None):
        from apps.invoices.choices import InvoiceStatus
        if obj and obj.invoice.status == InvoiceStatus.CLOSED:
            return False
        return True
        
    def has_delete_permission(self, request, obj=None):
        from apps.invoices.choices import InvoiceStatus
        if obj and obj.invoice.status == InvoiceStatus.CLOSED:
            return False
        return True
        
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['invoice'] # Invoice shouldn't be changed after creation
        return []
        
    def save_model(self, request, obj, form, change):
        from apps.invoices.choices import InvoiceStatus
        if obj.invoice.status == InvoiceStatus.CLOSED:
            from django.core.exceptions import ValidationError
            raise ValidationError("Cannot add or edit payments for a CLOSED invoice.")
        super().save_model(request, obj, form, change)
