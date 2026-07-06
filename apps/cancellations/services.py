from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum

from apps.cancellations.models import BookingCancellation, CancellationSettlement
from apps.invoices.models import Invoice, InvoiceLineTraveler, InvoiceLine
from apps.credit_notes.models import CreditNote
from apps.cancellations.choices import CancellationStatus, SettlementStatus
from apps.credit_notes.choices import CreditNoteSource

class CancellationValidationService:
    
    @classmethod
    def validate_cancellation_totals(cls, cancellation: BookingCancellation):
        """
        Ensures that a single cancellation does not exceed the remaining snapshot value.
        """
        # Determine the snapshot target
        if cancellation.type == 'PASSENGER' and cancellation.invoice_line_traveler:
            snapshot = cancellation.invoice_line_traveler
            related_cancellations = BookingCancellation.objects.filter(
                invoice_line_traveler=snapshot,
                status='FINALIZED'
            ).exclude(id=cancellation.id)
        elif cancellation.type == 'SERVICE' and cancellation.invoice_line:
            snapshot = cancellation.invoice_line
            related_cancellations = BookingCancellation.objects.filter(
                invoice_line=snapshot,
                status='FINALIZED'
            ).exclude(id=cancellation.id)
        else:
            # OTHER types don't have a strict snapshot cost constraint like a service
            return

        # Calculate previously finalized refunds
        prev_service = related_cancellations.aggregate(t=Sum('service_refund'))['t'] or Decimal("0.00")
        prev_cgst = related_cancellations.aggregate(t=Sum('cgst_refund'))['t'] or Decimal("0.00")
        prev_sgst = related_cancellations.aggregate(t=Sum('sgst_refund'))['t'] or Decimal("0.00")
        prev_igst = related_cancellations.aggregate(t=Sum('igst_refund'))['t'] or Decimal("0.00")
        prev_supplier = related_cancellations.aggregate(t=Sum('supplier_refund'))['t'] or Decimal("0.00")

        # Validate against snapshot
        if (cancellation.service_refund + prev_service) > snapshot.service_charge:
            raise ValidationError(f"Total service refund exceeds snapshot service charge of {snapshot.service_charge}.")
            
        if cancellation.refund_gst:
            # We assume cgst, sgst, igst are stored on the snapshot (e.g., cgst_amount or cgst)
            cgst_limit = getattr(snapshot, 'cgst', getattr(snapshot, 'cgst_amount', Decimal('0.00')))
            if (cancellation.cgst_refund + prev_cgst) > cgst_limit:
                raise ValidationError("Total CGST refund exceeds snapshot CGST.")
                
        # We temporarily calculate supplier refund sum for validation
        current_supplier = cancellation.settlements.filter(status=SettlementStatus.APPROVED).aggregate(
            t=Sum('settled_supplier_refund')
        )['t'] or Decimal('0.00')
        
        if (current_supplier + prev_supplier) > snapshot.supplier_cost:
            raise ValidationError(f"Total supplier refund exceeds snapshot supplier cost of {snapshot.supplier_cost}.")


class CancellationFinalizationService:
    
    @classmethod
    @transaction.atomic
    def finalize_cancellation(cls, cancellation_id, finalized_by_user=None):
        """
        The absolute single source of truth for finalizing a cancellation.
        """
        # 1. Lock rows
        cancellation = BookingCancellation.objects.select_for_update().get(id=cancellation_id)
        
        if cancellation.status == CancellationStatus.FINALIZED:
            raise ValidationError("Cancellation is already finalized.")
            
        invoice = Invoice.objects.select_for_update().get(id=cancellation.invoice_id)
        booking = invoice.booking
        
        # 2. Validate Refunds
        CancellationValidationService.validate_cancellation_totals(cancellation)
        
        # 3. Freeze Supplier Refund (SUM of APPROVED settlements)
        approved_supplier_refund = cancellation.settlements.filter(status=SettlementStatus.APPROVED).aggregate(
            t=Sum('settled_supplier_refund')
        )['t'] or Decimal('0.00')
        
        cancellation.supplier_refund = approved_supplier_refund
        
        # 4. Freeze Total Refund
        total_tax_refund = Decimal('0.00')
        if cancellation.refund_gst:
            total_tax_refund = cancellation.cgst_refund + cancellation.sgst_refund + cancellation.igst_refund
            
        cancellation.total_refund = cancellation.service_refund + total_tax_refund + approved_supplier_refund
        
        # We temporarily set the status so current_invoice_value recalculates correctly
        cancellation.status = CancellationStatus.FINALIZED
        cancellation.finalized_at = timezone.now()
        cancellation.finalized_by = finalized_by_user
        
        # Save so the DB aggregate captures it for current_invoice_value
        cancellation.save() 
        
        # 5. Freeze finalized_invoice_value
        # Note: invoice.current_invoice_value will now include this newly finalized cancellation
        # because we just saved it as FINALIZED above.
        cancellation.finalized_invoice_value = invoice.current_invoice_value
        cancellation.save(update_fields=['finalized_invoice_value'])
        
        # 6. Update Booking & Invoice Statuses
        # Simplistic cascade: Since at least one cancellation finalized, set to PARTIALLY_CANCELLED
        booking.status = 'PARTIALLY_CANCELLED'
        booking.save(update_fields=['status'])
        
        invoice.cancellation_status = 'PARTIAL'
        invoice.save(update_fields=['cancellation_status'])
        
        # 7. Calculate Invoice.balance_due
        balance_due = invoice.balance_due
        
        # 8. Generate Credit Note if Balance Due < 0
        if balance_due < Decimal('0.00'):
            credit_amount = abs(balance_due)
            cn = CreditNote.objects.create(
                customer=booking.customer,
                invoice=invoice,
                number=f"CN-{invoice.invoice_number}-{cancellation.id}",
                source=CreditNoteSource.CANCELLATION,
                amount=credit_amount,
                issued_by=finalized_by_user,
                reason=f"Generated from cancellation #{cancellation.id}"
            )
            
        return cancellation
