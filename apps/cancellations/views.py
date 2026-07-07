from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from apps.invoices.models import Invoice, InvoiceLine, InvoiceLineTraveler
from apps.cancellations.models import BookingCancellation
from apps.cancellations.choices import CancellationStatus
from apps.cancellations.services import CancellationService
from django.core.exceptions import ValidationError

class CancellationWizardView(View):
    template_name = 'admin/cancellations/wizard.html'
    
    def get(self, request, invoice_id):
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        # Get existing ACTIVE cancellations
        existing_cancellations = BookingCancellation.objects.filter(
            invoice_line_traveler__invoice_line__invoice=invoice,
            status=CancellationStatus.ACTIVE
        )
        cancelled_traveler_ids = list(existing_cancellations.values_list('invoice_line_traveler_id', flat=True))
        
        lines = InvoiceLine.objects.filter(invoice=invoice)
        travelers = InvoiceLineTraveler.objects.filter(invoice_line__invoice=invoice)
        
        context = {
            'invoice': invoice,
            'lines': lines,
            'travelers': travelers,
            'cancelled_traveler_ids': cancelled_traveler_ids,
            'title': f'Cancel Passengers for {invoice.invoice_number}'
        }
        return render(request, self.template_name, context)

    def post(self, request, invoice_id):
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        target_id = request.POST.get('target_id')
        traveler = get_object_or_404(InvoiceLineTraveler, id=target_id)
        
        try:
            refund_data = {
                traveler.id: {
                    'supplier_refund': Decimal(request.POST.get('supplier_refund') or '0.00'),
                    'service_refund': Decimal(request.POST.get('service_refund') or '0.00'),
                    'cgst_refund': Decimal(request.POST.get('cgst_refund') or '0.00'),
                    'sgst_refund': Decimal(request.POST.get('sgst_refund') or '0.00'),
                    'igst_refund': Decimal(request.POST.get('igst_refund') or '0.00'),
                }
            }
        except Exception:
            messages.error(request, "Invalid refund amounts entered.")
            return redirect('cancellation_wizard', invoice_id=invoice.id)
            
        reason = request.POST.get('reason', '')
        
        try:
            CancellationService.cancel_passengers(
                travelers=[traveler],
                refund_data=refund_data,
                user=request.user,
                source='ADMIN',
                reason=reason
            )
            messages.success(request, f"Cancellation completed for passenger {traveler.traveler_name}.")
        except ValidationError as e:
            messages.error(request, f"Validation Error: {e.messages[0] if hasattr(e, 'messages') else str(e)}")
            
        return redirect('cancellation_wizard', invoice_id=invoice.id)
