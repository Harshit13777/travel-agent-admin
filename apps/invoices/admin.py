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
    search_fields = ['invoice_number', 'booking__booking_number', 'booking__customer__name', 'booking__customer__email', 'booking__customer__phone']
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
        if cancellations.exists():
            total_cancel = sum(c.total_refund for c in cancellations)
            html += f'<details style="margin-bottom: 8px; color: #ef4444; font-size: 13px;">'
            html += f'<summary style="display: flex; justify-content: space-between; cursor: pointer; outline: none;">'
            html += f'<strong>Cancellations/Refunds</strong><span>- {obj.currency} {total_cancel}</span></summary>'
            html += '<div style="padding-left: 20px; margin-top: 4px;">'
            for c in cancellations:
                html += f'<div style="display: flex; justify-content: space-between; margin-bottom: 2px;">'
                html += f'<span>Traveler {c.invoice_line_traveler.traveler_name}:</span>'
                html += f'<span>- {obj.currency} {c.total_refund}</span></div>'
            html += '</div></details>'
            
        # 3. Payments
        payments = obj.payments.all()
        if payments.exists():
            total_pay = sum(p.amount for p in payments)
            html += f'<details style="margin-bottom: 8px; color: #10b981; font-size: 13px;">'
            html += f'<summary style="display: flex; justify-content: space-between; cursor: pointer; outline: none;">'
            html += f'<strong>Payments Received</strong><span>- {obj.currency} {total_pay}</span></summary>'
            html += '<div style="padding-left: 20px; margin-top: 4px;">'
            for p in payments:
                from django.urls import reverse
                payment_url = reverse('admin:payments_payment_change', args=[p.id])
                html += f'<div style="display: flex; justify-content: space-between; margin-bottom: 2px;">'
                html += f'<span><a href="{payment_url}" style="color: #10b981; text-decoration: underline;">{p.date} - {p.get_method_display()}</a>:</span>'
                html += f'<span>- {obj.currency} {p.amount}</span></div>'
            html += '</div></details>'
            
        # 4. Credit Allocations
        allocations = obj.credit_allocations.all()
        if allocations.exists():
            total_alloc = sum(a.amount for a in allocations)
            html += f'<details style="margin-bottom: 8px; color: #8b5cf6; font-size: 13px;">'
            html += f'<summary style="display: flex; justify-content: space-between; cursor: pointer; outline: none;">'
            html += f'<strong>Credit Notes Applied</strong><span>- {obj.currency} {total_alloc}</span></summary>'
            html += '<div style="padding-left: 20px; margin-top: 4px;">'
            for a in allocations:
                from django.urls import reverse
                from apps.invoices.choices import InvoiceStatus
                next_url = reverse('admin:invoices_invoice_change', args=[obj.id])
                
                cn_url = reverse('admin:credit_notes_creditnote_change', args=[a.credit_note.id])
                del_url = reverse('admin:credit_notes_creditallocation_delete', args=[a.id]) + f'?next={next_url}'
                
                actions_html = ""
                if obj.status != InvoiceStatus.CLOSED:
                    actions_html += f'<a href="{del_url}" style="color: #ef4444; font-size: 10px; margin-left: 8px; text-decoration: none; border: 1px solid #ef4444; padding: 1px 4px; border-radius: 3px;" title="Deallocate">❌ Remove</a>'
                    
                html += f'<div style="display: flex; justify-content: space-between; margin-bottom: 2px; align-items: center;">'
                html += f'<span><a href="{cn_url}" style="color: #8b5cf6; text-decoration: underline;">{a.credit_note.number}</a> {actions_html}</span>'
                html += f'<span>- {obj.currency} {a.amount}</span></div>'
            html += '</div></details>'
            
        # 5. Generated Credit Notes
        from apps.credit_notes.choices import CreditNoteStatus
        issued_cns = obj.issued_credit_notes.filter(status=CreditNoteStatus.ACTIVE)
        if issued_cns.exists():
            total_issued = sum(cn.amount for cn in issued_cns)
            html += f'<details style="margin-bottom: 8px; color: #f59e0b; font-size: 13px;">'
            html += f'<summary style="display: flex; justify-content: space-between; cursor: pointer; outline: none;">'
            html += f'<strong>Credit Notes Generated</strong><span>+ {obj.currency} {total_issued}</span></summary>'
            html += '<div style="padding-left: 20px; margin-top: 4px;">'
            for cn in issued_cns:
                from django.urls import reverse
                cn_url = reverse('admin:credit_notes_creditnote_change', args=[cn.id])
                html += f'<div style="display: flex; justify-content: space-between; margin-bottom: 2px;">'
                html += f'<span><a href="{cn_url}" style="color: #f59e0b; text-decoration: underline;">{cn.number}</a>:</span>'
                html += f'<span>+ {obj.currency} {cn.amount}</span></div>'
            html += '</div></details>'
            
        # Divider
        html += '<div style="border-top: 1px dashed #d1d5db; margin: 12px 0;"></div>'
        
        # Total Outstanding
        color = "#10b981" if obj.balance_due <= 0 else "#ef4444"
        html += f'<div style="display: flex; justify-content: space-between; font-size: 16px; font-weight: bold; margin-bottom: 16px;">'
        html += f'<span>TOTAL OUTSTANDING:</span>'
        html += f'<span style="color: {color};">{obj.currency} {obj.balance_due}</span></div>'
        
        # Action Buttons
        from django.urls import reverse
        from apps.invoices.choices import InvoiceStatus
        
        buttons_html = '<div style="display: flex; gap: 10px;">'
        
        if obj.status != InvoiceStatus.CLOSED:
            close_url = reverse('admin:invoices_invoice_close_btn', args=[obj.id])
            buttons_html += f'<a href="{close_url}" style="display: inline-block; background-color: #f59e0b; color: white; padding: 8px 12px; border-radius: 4px; text-decoration: none; font-family: sans-serif; font-size: 13px; font-weight: bold;">🔒 Close Invoice (Lock Financials)</a>'
            
            # Apply Credit Note Button & Add Payment Button
            if obj.balance_due > 0:
                next_url = reverse('admin:invoices_invoice_change', args=[obj.id])
                apply_url = reverse('admin:credit_notes_creditallocation_add') + f'?invoice={obj.id}&next={next_url}'
                buttons_html += f'<a href="{apply_url}" style="display: inline-block; background-color: #10b981; color: white; padding: 8px 12px; border-radius: 4px; text-decoration: none; font-family: sans-serif; font-size: 13px; font-weight: bold; margin-left: 10px;">💰 Apply Credit Note</a>'
                
                payment_url = reverse('admin:payments_payment_add') + f'?invoice={obj.id}&next={next_url}'
                buttons_html += f'<a href="{payment_url}" style="display: inline-block; background-color: #3b82f6; color: white; padding: 8px 12px; border-radius: 4px; text-decoration: none; font-family: sans-serif; font-size: 13px; font-weight: bold; margin-left: 10px;">💸 Add Payment</a>'
        elif obj.status == InvoiceStatus.CLOSED:
            # Reopen Button
            reopen_url = reverse('admin:invoices_invoice_reopen_btn', args=[obj.id])
            
            from apps.credit_notes.choices import CreditNoteStatus
            active_cns = obj.issued_credit_notes.filter(status=CreditNoteStatus.ACTIVE)
            if active_cns.exists():
                if any(cn.allocated_amount > 0 for cn in active_cns):
                    onclick = "return confirm('Warning: Credit Notes generated by this invoice have already been allocated. You must remove those allocations first before you can re-open. Proceed anyway?');"
                else:
                    onclick = f"return confirm('WARNING: Re-opening this invoice will PERMANENTLY DELETE {active_cns.count()} unallocated Credit Note(s) generated by it. Are you sure you want to proceed?');"
            else:
                onclick = "return confirm('Are you sure you want to re-open this invoice and unlock its financials?');"
                
            buttons_html += f'<a href="{reopen_url}" onclick="{onclick}" style="display: inline-block; background-color: #3b82f6; color: white; padding: 8px 12px; border-radius: 4px; text-decoration: none; font-family: sans-serif; font-size: 13px; font-weight: bold;">🔓 Re-open Invoice</a>'
            
            # Credit Note Button (if negative balance)
            if obj.balance_due < 0:
                cn_url = reverse('admin:invoices_invoice_generate_cn_btn', args=[obj.id])
                buttons_html += f'<a href="{cn_url}" style="display: inline-block; background-color: #8b5cf6; color: white; padding: 8px 12px; border-radius: 4px; text-decoration: none; font-family: sans-serif; font-size: 13px; font-weight: bold; margin-left: 10px;">✨ Generate Credit Note</a>'
            
            
        buttons_html += '</div>'
        
        html += buttons_html
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

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/close-invoice/', self.admin_site.admin_view(self.close_invoice_view), name='invoices_invoice_close_btn'),
            path('<path:object_id>/reopen-invoice/', self.admin_site.admin_view(self.reopen_invoice_view), name='invoices_invoice_reopen_btn'),
            path('<path:object_id>/generate-credit-note/', self.admin_site.admin_view(self.generate_cn_view), name='invoices_invoice_generate_cn_btn'),
        ]
        return custom_urls + urls
        
    def close_invoice_view(self, request, object_id):
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        from apps.invoices.choices import InvoiceStatus
        
        invoice = get_object_or_404(Invoice, pk=object_id)
        if invoice.status != InvoiceStatus.CLOSED:
            invoice.status = InvoiceStatus.CLOSED
            invoice.save(update_fields=['status'])
            messages.success(request, f"Invoice {invoice.invoice_number} closed and financially locked.")
        else:
            messages.info(request, "Invoice is already closed.")
            
        return redirect('admin:invoices_invoice_change', object_id)
        
    def reopen_invoice_view(self, request, object_id):
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        from apps.invoices.choices import InvoiceStatus
        
        invoice = get_object_or_404(Invoice, pk=object_id)
        
        from apps.credit_notes.choices import CreditNoteStatus
        active_cns = invoice.issued_credit_notes.filter(status=CreditNoteStatus.ACTIVE)
        if active_cns.exists():
            if any(cn.allocated_amount > 0 for cn in active_cns):
                messages.error(request, "Cannot re-open: This invoice has generated Credit Notes that have already been allocated. Please remove their allocations first.")
                return redirect('admin:invoices_invoice_change', object_id)
            else:
                count = active_cns.count()
                active_cns.delete()
                messages.warning(request, f"Automatically deleted {count} unallocated Credit Note(s) previously generated by this invoice.")
            
        if invoice.status == InvoiceStatus.CLOSED:
            invoice.status = InvoiceStatus.ISSUED
            invoice.save(update_fields=['status'])
            messages.success(request, f"Invoice {invoice.invoice_number} re-opened successfully. Financials are unlocked.")
        else:
            messages.info(request, "Invoice is not closed.")
            
        return redirect('admin:invoices_invoice_change', object_id)

    def generate_cn_view(self, request, object_id):
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        from apps.invoices.choices import InvoiceStatus
        from apps.credit_notes.services import CreditNoteService
        
        invoice = get_object_or_404(Invoice, pk=object_id)
        if invoice.status != InvoiceStatus.CLOSED:
            messages.error(request, "Invoice must be CLOSED before generating a Credit Note.")
            return redirect('admin:invoices_invoice_change', object_id)
            
        if invoice.balance_due >= 0:
            messages.error(request, "Invoice does not have a negative balance.")
            return redirect('admin:invoices_invoice_change', object_id)
            
        try:
            cn = CreditNoteService.generate_from_overpayment(invoice, request.user)
            messages.success(request, f"Credit Note {cn.number} generated successfully.")
            return redirect('admin:invoices_invoice_change', object_id)
        except Exception as e:
            messages.error(request, str(e))
            return redirect('admin:invoices_invoice_change', object_id)

    actions = ['action_cancellation_wizard']
    def action_cancellation_wizard(self, request, queryset):
        from django.shortcuts import redirect
        from django.contrib import messages
        
        if queryset.count() != 1:
            messages.error(request, "Please select exactly one Invoice to initiate cancellation.")
            return
            
        invoice = queryset.first()
        return redirect('cancellation_wizard', invoice_id=invoice.id)
