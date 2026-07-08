from django.contrib import admin
from unfold.admin import ModelAdmin
from django import forms
from .models import Payment
from .services import PaymentService

class PaymentAdminForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        invoice = cleaned_data.get('invoice')
        if invoice:
            PaymentService.validate_payment(invoice)
        return cleaned_data

@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    form = PaymentAdminForm
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
        from apps.payments.services import PaymentService
        PaymentService.save_payment(obj, request.user, change)

    def delete_model(self, request, obj):
        from apps.payments.services import PaymentService
        PaymentService.delete_payment(obj, request.user)

    def response_add(self, request, obj, post_url_continue=None):
        next_url = request.GET.get('next')
        if next_url and '_addanother' not in request.POST and '_continue' not in request.POST:
            from django.http import HttpResponseRedirect
            return HttpResponseRedirect(next_url)
        return super().response_add(request, obj, post_url_continue)
