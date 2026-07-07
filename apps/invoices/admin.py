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
    
    fieldsets = (
        ('Financial Ledger (Statement)', {
            'fields': ('financial_ledger',)
        }),
        ('Invoice Summary', {
            'fields': (
                ('invoice_number', 'booking', 'status'),
                ('invoice_date', 'due_date', 'cancellation_status'),
                ('original_total', 'current_invoice_value', 'balance_due')
            )
        }),
        ('Tax Details', {
            'fields': (
                ('subtotal_before_tax', 'taxable_amount'),
                ('cgst_amount', 'sgst_amount', 'igst_amount'),
                ('grand_total', 'final_payable')
            ),
            'classes': ('collapse',)
        }),
        ('Company Info', {
            'fields': (
                ('company_name', 'gstin', 'pan'),
                ('address', 'phone', 'email')
            ),
            'classes': ('collapse',)
        })
    )
    
    def get_readonly_fields(self, request, obj=None):
        fields = [
            'invoice_number', 'currency', 'status', 'cancellation_status', 'invoice_date', 'due_date',
            'company_name', 'gstin', 'pan', 'address', 'phone', 'email',
            'gst_enabled', 'gst_type', 'cgst_rate', 'sgst_rate', 'igst_rate', 'tax_label_1', 'tax_label_2', 'tax_label_3',
            'supplier_total', 'service_charge_total', 'subtotal_before_tax', 'taxable_amount', 
            'cgst_amount', 'sgst_amount', 'igst_amount', 
            'grand_total', 'original_total', 'final_payable', 'booking',
            'current_invoice_value', 'balance_due', 'payment_status', 'financial_ledger'
        ]
        return fields
        
    def financial_ledger(self, obj):
        if not obj:
            return ""
            
        from django.utils.safestring import mark_safe
        from apps.cancellations.models import BookingCancellation
        
        # Build the HTML ledger
        html = '<div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; max-width: 600px; font-family: monospace;">'
        html += '<h3 style="margin-top: 0; margin-bottom: 16px; border-bottom: 2px solid #d1d5db; padding-bottom: 8px;">Financial Ledger</h3>'
        
        # 1. Original Amount
        html += f'<div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px;">'
        html += f'<span>Original Invoice Amount:</span>'
        html += f'<span style="font-weight: bold;">+ {obj.currency} {obj.final_payable}</span></div>'
        
        # 2. Cancellations
        cancellations = BookingCancellation.objects.filter(invoice_line_traveler__invoice_line__invoice=obj)
        for c in cancellations:
            html += f'<div style="display: flex; justify-content: space-between; margin-bottom: 4px; color: #ef4444; font-size: 13px;">'
            html += f'<span style="padding-left: 12px;">Refund (Traveler {c.invoice_line_traveler.traveler_name}):</span>'
            html += f'<span>- {obj.currency} {c.total_refund}</span></div>'
            
        # 3. Payments
        for p in obj.payments.all():
            from django.urls import reverse
            payment_url = reverse('admin:payments_payment_change', args=[p.id])
            html += f'<div style="display: flex; justify-content: space-between; margin-bottom: 4px; color: #10b981; font-size: 13px;">'
            html += f'<span style="padding-left: 12px;"><a href="{payment_url}" style="color: #10b981; text-decoration: underline;">Payment</a> ({p.date} - {p.get_method_display()}):</span>'
            html += f'<span>- {obj.currency} {p.amount}</span></div>'
            
        # 4. Credit Allocations
        for a in obj.credit_allocations.all():
            html += f'<div style="display: flex; justify-content: space-between; margin-bottom: 4px; color: #8b5cf6; font-size: 13px;">'
            html += f'<span style="padding-left: 12px;">Credit Note Applied ({a.credit_note.number}):</span>'
            html += f'<span>- {obj.currency} {a.amount}</span></div>'
            
        # 5. Generated Credit Notes
        for cn in obj.issued_credit_notes.filter(status='ACTIVE'):
            html += f'<div style="display: flex; justify-content: space-between; margin-bottom: 4px; color: #f59e0b; font-size: 13px;">'
            html += f'<span style="padding-left: 12px;">Credit Note Generated ({cn.number}):</span>'
            html += f'<span>+ {obj.currency} {cn.amount}</span></div>'
            
        # Divider
        html += '<div style="border-top: 1px dashed #d1d5db; margin: 12px 0;"></div>'
        
        # Total Outstanding
        color = "#10b981" if obj.balance_due <= 0 else "#ef4444"
        html += f'<div style="display: flex; justify-content: space-between; font-size: 16px; font-weight: bold;">'
        html += f'<span>TOTAL OUTSTANDING:</span>'
        html += f'<span style="color: {color};">{obj.currency} {obj.balance_due}</span></div>'
        
        html += '</div>'
        return mark_safe(html)
    
    financial_ledger.short_description = "Ledger / Statement"

    def has_add_permission(self, request):
        return False
        
    def has_change_permission(self, request, obj=None):
        from apps.invoices.choices import InvoiceStatus
        if obj and obj.status == InvoiceStatus.CLOSED:
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        return False

    actions = ['action_cancellation_wizard', 'action_close_invoice', 'action_generate_credit_note']

    @admin.action(description="Close Invoice (Lock Financials)")
    def action_close_invoice(self, request, queryset):
        from django.contrib import messages
        from apps.invoices.choices import InvoiceStatus
        count = 0
        for inv in queryset:
            if inv.status != InvoiceStatus.CLOSED:
                inv.status = InvoiceStatus.CLOSED
                inv.save(update_fields=['status'])
                count += 1
        messages.success(request, f"{count} invoice(s) closed and financially locked.")

    @admin.action(description="Generate Credit Note from Overpayment")
    def action_generate_credit_note(self, request, queryset):
        from django.shortcuts import redirect
        from django.contrib import messages
        from apps.credit_notes.services import CreditNoteService
        
        if queryset.count() != 1:
            messages.error(request, "Please select exactly one Invoice.")
            return
            
        invoice = queryset.first()
        from apps.invoices.choices import InvoiceStatus
        if invoice.status != InvoiceStatus.CLOSED:
            messages.error(request, "Invoice must be CLOSED before generating a Credit Note.")
            return
            
        if invoice.balance_due >= 0:
            messages.error(request, "Invoice does not have a negative balance.")
            return
            
        try:
            cn = CreditNoteService.generate_from_overpayment(invoice, request.user)
            messages.success(request, f"Credit Note {cn.number} generated successfully.")
            return redirect('admin:credit_notes_creditnote_change', cn.id)
        except Exception as e:
            messages.error(request, str(e))
            
    @admin.action(description="Cancel Passengers or Services (Wizard)")
    def action_cancellation_wizard(self, request, queryset):
        from django.shortcuts import redirect
        from django.contrib import messages
        
        if queryset.count() != 1:
            messages.error(request, "Please select exactly one Invoice to initiate cancellation.")
            return
            
        invoice = queryset.first()
        return redirect('cancellation_wizard', invoice_id=invoice.id)
