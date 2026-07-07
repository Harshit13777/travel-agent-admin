from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum

from apps.cancellations.models import BookingCancellation
from apps.invoices.models import Invoice, InvoiceLineTraveler
from apps.cancellations.choices import CancellationStatus

class CancellationValidationService:
    
    @classmethod
    def validate_components(cls, travelers, refund_data):
        """
        Validates that the proposed refunds do not exceed the remaining financial limits
        for each traveler.
        """
        for traveler in travelers:
            # Calculate previously ACTIVE refunds for this traveler
            active_cancellations = BookingCancellation.objects.filter(
                invoice_line_traveler=traveler,
                status=CancellationStatus.ACTIVE
            )
            
            prev_supplier = active_cancellations.aggregate(t=Sum('supplier_refund'))['t'] or Decimal("0.00")
            prev_service = active_cancellations.aggregate(t=Sum('service_refund'))['t'] or Decimal("0.00")
            prev_cgst = active_cancellations.aggregate(t=Sum('cgst_refund'))['t'] or Decimal("0.00")
            prev_sgst = active_cancellations.aggregate(t=Sum('sgst_refund'))['t'] or Decimal("0.00")
            prev_igst = active_cancellations.aggregate(t=Sum('igst_refund'))['t'] or Decimal("0.00")
            
            # Extract proposed refunds (assuming refund_data maps traveler_id to a dict of refunds, or applies a uniform refund)
            # For simplicity in this implementation, we assume refund_data provides the granular amounts per traveler.
            data = refund_data.get(traveler.id, {})
            proposed_supplier = data.get('supplier_refund', Decimal("0.00"))
            proposed_service = data.get('service_refund', Decimal("0.00"))
            proposed_cgst = data.get('cgst_refund', Decimal("0.00"))
            proposed_sgst = data.get('sgst_refund', Decimal("0.00"))
            proposed_igst = data.get('igst_refund', Decimal("0.00"))
            
            # Validate each component against traveler limits
            # Fallback to 0 if not present on traveler for some reason (though they should be required in schema)
            if (prev_supplier + proposed_supplier) > getattr(traveler, 'supplier_cost', Decimal('0.00')):
                raise ValidationError(f"Total supplier refund exceeds snapshot limit for traveler {traveler.id}")
                
            if (prev_service + proposed_service) > getattr(traveler, 'service_charge', Decimal('0.00')):
                raise ValidationError(f"Total service refund exceeds snapshot limit for traveler {traveler.id}")
                
            if (prev_cgst + proposed_cgst) > getattr(traveler, 'cgst', Decimal('0.00')):
                raise ValidationError(f"Total CGST refund exceeds snapshot limit for traveler {traveler.id}")
                
            if (prev_sgst + proposed_sgst) > getattr(traveler, 'sgst', Decimal('0.00')):
                raise ValidationError(f"Total SGST refund exceeds snapshot limit for traveler {traveler.id}")
                
            if (prev_igst + proposed_igst) > getattr(traveler, 'igst', Decimal('0.00')):
                raise ValidationError(f"Total IGST refund exceeds snapshot limit for traveler {traveler.id}")

class CancellationService:

    @classmethod
    @transaction.atomic
    def cancel_passengers(cls, travelers, refund_data, user, source='ADMIN', reason='', remarks=''):
        """
        Main entry point for passenger cancellations. 
        Enforces immutability, validates bounds, creates records, and optionally handles credit notes via external services.
        """
        if not travelers:
            raise ValidationError("No travelers provided for cancellation.")

        # 1. Lock the invoice to prevent race conditions
        # Assuming all travelers belong to the same invoice for a batch operation
        invoice_id = travelers[0].invoice_line.invoice_id
        invoice = Invoice.objects.select_for_update().get(id=invoice_id)
        
        # Ensure all travelers belong to the same locked invoice
        for traveler in travelers:
            if traveler.invoice_line.invoice_id != invoice.id:
                raise ValidationError("All travelers in a single cancellation request must belong to the same invoice.")
                
            # Prevent multiple ACTIVE cancellations per traveler (also enforced by DB constraints)
            if BookingCancellation.objects.filter(invoice_line_traveler=traveler, status=CancellationStatus.ACTIVE).exists():
                raise ValidationError(f"Traveler {traveler.id} already has an ACTIVE cancellation record.")
        
        # 2. Delegate to CancellationValidationService
        CancellationValidationService.validate_components(travelers, refund_data)
        
        # 3. Create immutable ACTIVE cancellation ledger rows
        cancellations = []
        for traveler in travelers:
            data = refund_data.get(traveler.id, {})
            cancellation = BookingCancellation(
                invoice_line_traveler=traveler,
                supplier_refund=data.get('supplier_refund', Decimal("0.00")),
                service_refund=data.get('service_refund', Decimal("0.00")),
                cgst_refund=data.get('cgst_refund', Decimal("0.00")),
                sgst_refund=data.get('sgst_refund', Decimal("0.00")),
                igst_refund=data.get('igst_refund', Decimal("0.00")),
                status=CancellationStatus.ACTIVE,
                reason=reason,
                remarks=remarks,
                source=source,
                created_by=user
            )
            cancellation.save() # Triggers DB checks and Unique constraints
            cancellations.append(cancellation)
            
            # Update the actual passenger status
            if traveler.booking_traveler:
                traveler.booking_traveler.passenger_status = 'CANCELLED'
                from apps.bookings.services import update_booking_traveler
                update_booking_traveler(traveler.booking_traveler, user=user)
            
        # Optional: You can call InvoiceCalculationService and CreditNoteService here if they exist in your project
        # from apps.invoices.services import InvoiceCalculationService
        # from apps.credit_notes.services import CreditNoteService
        # 
        # outstanding = InvoiceCalculationService.calculate_outstanding(invoice)
        # if outstanding < 0:
        #     CreditNoteService.generate_from_overpayment(invoice, abs(outstanding))
            
        return cancellations
