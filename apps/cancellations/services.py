from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum

from apps.cancellations.models import BookingCancellation
from apps.invoices.models import Invoice, InvoiceLineTraveler


class CancellationValidationService:
    
    @classmethod
    def validate_components(cls, travelers, refund_data):
        """
        Validates that the proposed refunds do not exceed the remaining financial limits
        for each traveler.
        """
        for traveler in travelers:
            
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
            if proposed_supplier > getattr(traveler, 'supplier_cost', Decimal('0.00')):
                raise ValidationError(f"Total supplier refund exceeds snapshot limit for traveler {traveler.id}")
                
            if proposed_service > getattr(traveler, 'service_charge', Decimal('0.00')):
                raise ValidationError(f"Total service refund exceeds snapshot limit for traveler {traveler.id}")
                
            if proposed_cgst > getattr(traveler, 'cgst', Decimal('0.00')):
                raise ValidationError(f"Total CGST refund exceeds snapshot limit for traveler {traveler.id}")
                
            if proposed_sgst > getattr(traveler, 'sgst', Decimal('0.00')):
                raise ValidationError(f"Total SGST refund exceeds snapshot limit for traveler {traveler.id}")
                
            if proposed_igst > getattr(traveler, 'igst', Decimal('0.00')):
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
        
        from apps.invoices.choices import InvoiceStatus
        if invoice.status == InvoiceStatus.CLOSED:
            raise ValidationError("Cannot cancel passengers for a CLOSED invoice.")
        
        # Ensure all travelers belong to the same locked invoice
        for traveler in travelers:
            if traveler.invoice_line.invoice_id != invoice.id:
                raise ValidationError("All travelers in a single cancellation request must belong to the same invoice.")
                
            # Prevent multiple ACTIVE cancellations per traveler (also enforced by OneToOne)
            if hasattr(traveler, 'cancellation') and traveler.cancellation.pk is not None:
                raise ValidationError(f"Traveler {traveler.id} already has a cancellation record.")
        
        # 2. Delegate to CancellationValidationService
        CancellationValidationService.validate_components(travelers, refund_data)
        
        # 3. Create immutable ACTIVE cancellation ledger rows
        cancellations = []
        from apps.bookings.services import log_booking_history
        for traveler in travelers:
            data = refund_data.get(traveler.id, {})
            cancellation = BookingCancellation(
                invoice_line_traveler=traveler,
                supplier_refund=data.get('supplier_refund', Decimal("0.00")),
                service_refund=data.get('service_refund', Decimal("0.00")),
                cgst_refund=data.get('cgst_refund', Decimal("0.00")),
                sgst_refund=data.get('sgst_refund', Decimal("0.00")),
                igst_refund=data.get('igst_refund', Decimal("0.00")),
                reason=reason,
                remarks=remarks,
                source=source,
                created_by=user
            )
            cancellation.save() # Triggers DB checks and Unique constraints
            cancellations.append(cancellation)
            
            log_booking_history(
                booking=invoice.booking,
                action="CANCELLATION_ADDED",
                description=f"Passenger {traveler.traveler_name} cancelled. Refund: {cancellation.total_refund}.",
                user=user
            )
            

        # Optional: You can call InvoiceCalculationService and CreditNoteService here if they exist in your project
        # from apps.invoices.services import InvoiceCalculationService
        # from apps.credit_notes.services import CreditNoteService
        # 
        # outstanding = InvoiceCalculationService.calculate_outstanding(invoice)
        # if outstanding < 0:
        #     CreditNoteService.generate_from_overpayment(invoice, abs(outstanding))
            
        return cancellations

    @classmethod
    @transaction.atomic
    def update_cancellation(cls, cancellation, refund_data, user, source='ADMIN', reason='', remarks=''):
        """
        Updates an existing cancellation record via the service layer.
        """
        # Validate using the central validation service
        CancellationValidationService.validate_components([cancellation.invoice_line_traveler], refund_data)
        
        from apps.invoices.choices import InvoiceStatus
        if cancellation.invoice_line_traveler.invoice_line.invoice.status == InvoiceStatus.CLOSED:
            raise ValidationError("Cannot update cancellations for a CLOSED invoice.")
            
        data = refund_data.get(cancellation.invoice_line_traveler_id, {})
        cancellation.supplier_refund = data.get('supplier_refund', cancellation.supplier_refund)
        cancellation.service_refund = data.get('service_refund', cancellation.service_refund)
        cancellation.cgst_refund = data.get('cgst_refund', cancellation.cgst_refund)
        cancellation.sgst_refund = data.get('sgst_refund', cancellation.sgst_refund)
        cancellation.igst_refund = data.get('igst_refund', cancellation.igst_refund)
        cancellation.reason = reason or cancellation.reason
        cancellation.remarks = remarks or cancellation.remarks
        cancellation.source = source
        cancellation.save()
        
        from apps.bookings.services import log_booking_history
        log_booking_history(
            booking=cancellation.invoice_line_traveler.invoice_line.invoice.booking,
            action="CANCELLATION_UPDATED",
            description=f"Cancellation for {cancellation.invoice_line_traveler.traveler_name} updated. New Refund: {cancellation.total_refund}.",
            user=user
        )
        
        return cancellation

    @classmethod
    @transaction.atomic
    def delete_cancellation(cls, cancellation, user=None):
        from apps.invoices.choices import InvoiceStatus
        if cancellation.invoice_line_traveler.invoice_line.invoice.status == InvoiceStatus.CLOSED:
            raise ValidationError("Cannot delete cancellations for a CLOSED invoice.")
            
        booking = cancellation.invoice_line_traveler.invoice_line.invoice.booking
        passenger_name = cancellation.invoice_line_traveler.traveler_name
        refund = cancellation.total_refund
        
        cancellation.delete()
        
        from apps.bookings.services import log_booking_history
        log_booking_history(
            booking=booking,
            action="CANCELLATION_DELETED",
            description=f"Cancellation for {passenger_name} deleted. Refund of {refund} reverted.",
            user=user
        )
