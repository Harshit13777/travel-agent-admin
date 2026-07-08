from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import CreditNote, CreditAllocation

class CreditAllocationInline(TabularInline):
    model = CreditAllocation
    extra = 0
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False
        
    def has_change_permission(self, request, obj=None):
        return False
        
    def get_readonly_fields(self, request, obj=None):
        return ['invoice_link', 'amount', 'created_at']
        
    def invoice_link(self, obj):
        if not obj or not obj.invoice:
            return "-"
        from django.urls import reverse
        from django.utils.html import format_html
        url = reverse('admin:invoices_invoice_change', args=[obj.invoice.id])
        return format_html('<a href="{}" style="color: #3b82f6; font-weight: bold;">{}</a>', url, obj.invoice.invoice_number)
    invoice_link.short_description = "Allocated Invoice"

@admin.register(CreditNote)
class CreditNoteAdmin(ModelAdmin):
    list_display = ['number', 'customer', 'invoice', 'amount', 'allocated_amount', 'remaining_amount', 'status']
    search_fields = ['number', 'customer__name', 'customer__email', 'customer__phone', 'invoice__invoice_number']
    list_filter = ['source', 'issued_at']
    autocomplete_fields = ['customer', 'invoice']
    list_select_related = ['customer', 'invoice']
    inlines = [CreditAllocationInline]
    
    def get_readonly_fields(self, request, obj=None):
        base = [f.name for f in self.model._meta.fields]
        return base + ['credit_summary']
        
    def credit_summary(self, obj):
        if not obj or not obj.pk:
            return "N/A"
            
        from django.utils.html import format_html
        from django.utils.safestring import mark_safe
        
        currency = obj.invoice.currency if obj.invoice else "INR"
        
        html = '<div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; width: 100%; max-width: 500px; font-family: sans-serif;">'
        
        # Original Amount
        html += f'<div style="display: flex; justify-content: space-between; margin-bottom: 12px; font-size: 15px;">'
        html += f'<span style="color: #64748b;">Original Credit Value:</span>'
        html += f'<span style="font-weight: bold; color: #0f172a;">{currency} {obj.amount}</span></div>'
        
        # Allocated Amount
        html += f'<div style="display: flex; justify-content: space-between; margin-bottom: 12px; font-size: 15px;">'
        html += f'<span style="color: #64748b;">Amount Used (Allocated):</span>'
        html += f'<span style="font-weight: bold; color: #ef4444;">- {currency} {obj.allocated_amount}</span></div>'
        
        # Divider
        html += '<div style="border-top: 1px dashed #cbd5e1; margin: 12px 0;"></div>'
        
        # Remaining Amount
        color = "#10b981" if obj.remaining_amount > 0 else "#64748b"
        html += f'<div style="display: flex; justify-content: space-between; font-size: 18px; font-weight: bold;">'
        html += f'<span style="color: #0f172a;">AVAILABLE BALANCE:</span>'
        html += f'<span style="color: {color};">{currency} {obj.remaining_amount}</span></div>'
        
        html += '</div>'
        return mark_safe(html)
        
    credit_summary.short_description = "Credit Summary"
        
    def has_add_permission(self, request):
        return False
        
    def has_delete_permission(self, request, obj=None):
        if obj and obj.allocated_amount == 0:
            return True
        return False

    def delete_model(self, request, obj):
        from apps.credit_notes.services import CreditNoteService
        CreditNoteService.delete_credit_note(obj.id, user=request.user)

    def delete_queryset(self, request, queryset):
        from apps.credit_notes.services import CreditNoteService
        for obj in queryset:
            CreditNoteService.delete_credit_note(obj.id, user=request.user)

from django import forms

class CreditAllocationForm(forms.ModelForm):
    class Meta:
        model = CreditAllocation
        fields = ['credit_note', 'invoice', 'amount']
        
    def clean(self):
        cleaned_data = super().clean()
        cn = cleaned_data.get('credit_note')
        invoice = cleaned_data.get('invoice')
        amount = cleaned_data.get('amount')
        
        if not cn or not invoice or not amount:
            return cleaned_data
            
        from apps.credit_notes.services import CreditNoteService
        CreditNoteService.validate_allocation(cn, invoice, amount)
            
        return cleaned_data

@admin.register(CreditAllocation)
class CreditAllocationAdmin(ModelAdmin):
    form = CreditAllocationForm
    list_display = ['credit_note', 'invoice', 'amount', 'created_at']
    autocomplete_fields = ['credit_note', 'invoice']
    
    def has_change_permission(self, request, obj=None):
        return False # Immutability - Allocations should only be created or deleted
        
    def has_delete_permission(self, request, obj=None):
        if obj and obj.invoice:
            from apps.invoices.choices import InvoiceStatus
            if obj.invoice.status == InvoiceStatus.CLOSED:
                return False
            return True
        return True # Allow bulk delete UI to show up, we will validate in delete_queryset
        
    def save_model(self, request, obj, form, change):
        from apps.credit_notes.services import CreditNoteService
        # Route through the Service Layer instead of saving directly
        allocation = CreditNoteService.allocate_credit(
            credit_note_id=obj.credit_note.id,
            invoice_id=obj.invoice.id,
            amount=obj.amount,
            user=request.user
        )
        obj.pk = allocation.pk
        obj.id = allocation.id

    def delete_model(self, request, obj):
        from apps.credit_notes.services import CreditNoteService
        CreditNoteService.deallocate_credit(obj.id, user=request.user)

    def delete_queryset(self, request, queryset):
        from apps.credit_notes.services import CreditNoteService
        for obj in queryset:
            CreditNoteService.deallocate_credit(obj.id, user=request.user)
            
    def response_add(self, request, obj, post_url_continue=None):
        next_url = request.GET.get('next')
        if next_url and '_addanother' not in request.POST and '_continue' not in request.POST:
            from django.http import HttpResponseRedirect
            return HttpResponseRedirect(next_url)
        return super().response_add(request, obj, post_url_continue)
        

    def response_delete(self, request, obj_display, obj_id):
        next_url = request.GET.get('next')
        if next_url:
            from django.http import HttpResponseRedirect
            return HttpResponseRedirect(next_url)
        return super().response_delete(request, obj_display, obj_id)
