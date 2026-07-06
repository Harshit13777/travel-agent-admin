from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from apps.invoices.models import Invoice, InvoiceLine, InvoiceLineTraveler
from apps.cancellations.models import BookingCancellation
from apps.cancellations.choices import CancellationType

class CancellationWizardView(View):
    template_name = 'admin/cancellations/wizard.html'
    
    def get(self, request, invoice_id):
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        # Get existing cancellations to not show already cancelled ones (or show as cancelled)
        existing_cancellations = BookingCancellation.objects.filter(invoice=invoice)
        cancelled_traveler_ids = list(existing_cancellations.filter(type='PASSENGER').values_list('invoice_line_traveler_id', flat=True))
        cancelled_line_ids = list(existing_cancellations.filter(type='SERVICE').values_list('invoice_line_id', flat=True))
        
        lines = InvoiceLine.objects.filter(invoice=invoice)
        travelers = InvoiceLineTraveler.objects.filter(invoice_line__invoice=invoice)
        
        context = {
            'invoice': invoice,
            'lines': lines,
            'travelers': travelers,
            'cancelled_traveler_ids': cancelled_traveler_ids,
            'cancelled_line_ids': cancelled_line_ids,
            'title': f'Cancel Services/Passengers for {invoice.invoice_number}'
        }
        return render(request, self.template_name, context)

    def post(self, request, invoice_id):
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        cancel_type = request.POST.get('cancel_type')
        target_id = request.POST.get('target_id')
        
        try:
            service_refund = Decimal(request.POST.get('service_refund') or '0.00')
            cgst_refund = Decimal(request.POST.get('cgst_refund') or '0.00')
            sgst_refund = Decimal(request.POST.get('sgst_refund') or '0.00')
            igst_refund = Decimal(request.POST.get('igst_refund') or '0.00')
        except Exception:
            messages.error(request, "Invalid refund amounts entered.")
            return redirect('cancellation_wizard', invoice_id=invoice.id)
            
        reason = request.POST.get('reason', '')
        
        if cancel_type == 'PASSENGER':
            traveler = get_object_or_404(InvoiceLineTraveler, id=target_id)
            
            # Simple soft validation before creation
            if service_refund > traveler.service_charge:
                messages.error(request, f"Service refund ({service_refund}) cannot exceed original service charge ({traveler.service_charge}).")
                return redirect('cancellation_wizard', invoice_id=invoice.id)
                
            BookingCancellation.objects.create(
                booking=invoice.booking,
                invoice=invoice,
                type=CancellationType.PASSENGER,
                invoice_line_traveler=traveler,
                reason=reason,
                service_refund=service_refund,
                cgst_refund=cgst_refund,
                sgst_refund=sgst_refund,
                igst_refund=igst_refund,
                refund_gst=True,
                requested_by=request.user
            )
            messages.success(request, f"Cancellation requested for passenger {traveler.traveler_name}.")
            
        elif cancel_type == 'SERVICE':
            line = get_object_or_404(InvoiceLine, id=target_id)
            
            if service_refund > line.service_charge:
                messages.error(request, f"Service refund ({service_refund}) cannot exceed original service charge ({line.service_charge}).")
                return redirect('cancellation_wizard', invoice_id=invoice.id)
                
            BookingCancellation.objects.create(
                booking=invoice.booking,
                invoice=invoice,
                type=CancellationType.SERVICE,
                invoice_line=line,
                reason=reason,
                service_refund=service_refund,
                cgst_refund=cgst_refund,
                sgst_refund=sgst_refund,
                igst_refund=igst_refund,
                refund_gst=True,
                requested_by=request.user
            )
            messages.success(request, f"Cancellation requested for service {line.service_type}.")
            
        return redirect('cancellation_wizard', invoice_id=invoice.id)
