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
        if obj and obj.invoice:
            from django.core.exceptions import ValidationError
            from apps.payments.services import PaymentService
            try:
                PaymentService.validate_payment(obj.invoice)
            except ValidationError:
                return False
        return True
        
    def has_delete_permission(self, request, obj=None):
        if obj and obj.invoice:
            from django.core.exceptions import ValidationError
            from apps.payments.services import PaymentService
            try:
                PaymentService.validate_payment(obj.invoice)
            except ValidationError:
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

    def delete_queryset(self, request, queryset):
        from apps.payments.services import PaymentService
        for obj in queryset:
            PaymentService.delete_payment(obj, request.user)

    def response_add(self, request, obj, post_url_continue=None):
        if '_addanother' not in request.POST and '_continue' not in request.POST:
            if obj and obj.invoice_id:
                from django.urls import reverse
                from django.http import HttpResponseRedirect
                return HttpResponseRedirect(reverse('admin:invoices_invoice_change', args=[obj.invoice_id]))
        return super().response_add(request, obj, post_url_continue)
        
    def response_change(self, request, obj):
        if '_addanother' not in request.POST and '_continue' not in request.POST:
            if obj and obj.invoice_id:
                from django.urls import reverse
                from django.http import HttpResponseRedirect
                return HttpResponseRedirect(reverse('admin:invoices_invoice_change', args=[obj.invoice_id]))
        return super().response_change(request, obj)
        
    def delete_view(self, request, object_id, extra_context=None):
        try:
            obj = self.get_object(request, object_id)
            invoice_id = obj.invoice_id if obj else None
        except Exception:
            invoice_id = None
            
        response = super().delete_view(request, object_id, extra_context)
        
        if request.method == 'POST' and invoice_id:
            from django.http import HttpResponseRedirect
            if isinstance(response, HttpResponseRedirect):
                from django.urls import reverse
                return HttpResponseRedirect(reverse('admin:invoices_invoice_change', args=[invoice_id]))
                
        return response
