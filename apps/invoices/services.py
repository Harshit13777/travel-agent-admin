from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.invoices.models import Invoice, InvoiceLine
from apps.invoices.choices import InvoiceStatus
from apps.bookings.models import Booking
from apps.bookings.choices import BookingStatus, BookingServiceStatus, BookingHistoryAction
from apps.common.number_generator import generate_invoice_number
from apps.bookings.services import log_booking_history
from django.core.exceptions import ValidationError

def generate_invoice(booking: Booking, user=None, applied_credit_notes=None) -> Invoice:
    """
    Generate an invoice for a confirmed booking.
    
    IMPORTANT:
    - Invoice is a permanent, immutable legal snapshot.
    - Booking data is never used again for accounting after invoice generation.
    - Credit Notes are the ONLY mechanism for post-invoice financial adjustments.
    - Payments never modify invoice totals, only the outstanding balance.
    
    Rules:
    - Validate Booking is CONFIRMED.
    - Validate Booking has at least one BookingService.
    - Prevent duplicate invoices.
    - Copy Booking financial totals into the Invoice.
    - Copy BookingServices to InvoiceLines for traceability.
    - Apply CreditNotes via CreditAllocation.
    - Generate Invoice Number using generate_invoice_number().
    - Set Booking.locked_at.
    - Log BookingHistory using INVOICE_GENERATED.
    - Run inside transaction.atomic().
    """
    if booking.status != BookingStatus.CONFIRMED:
        raise ValidationError("Booking must be Confirmed to generate an invoice.")
        
    if not booking.services.exists():
        raise ValidationError("Booking must have at least one service to generate an invoice.")
        
    if hasattr(booking, 'invoice'):
        raise ValidationError("An invoice already exists for this booking.")
    
    with transaction.atomic():
        # Calculate financial totals from active services
        services = booking.services.exclude(status=BookingServiceStatus.CANCELLED)
        if not services:
            raise ValidationError("No active services to invoice.")
            
        subtotal = sum((service.service_charge - service.discount) for service in services)
        gst_rate = Decimal("0.00")
        gst_amount = Decimal("0.00")
        original_total = subtotal + gst_amount
        credit_applied = Decimal("0.00")
        
        invoice_number = generate_invoice_number()
        
        invoice = Invoice.objects.create(
            booking=booking,
            invoice_number=invoice_number,
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date(),
            taxable_amount=subtotal,
            cgst_rate=gst_rate,
            cgst_amount=gst_amount,
            sgst_rate=Decimal("0.00"),
            sgst_amount=Decimal("0.00"),
            igst_rate=Decimal("0.00"),
            igst_amount=Decimal("0.00"),
            grand_total=original_total,
            original_total=original_total,
            credit_applied=Decimal("0.00"), # Will update below if allocations happen
            final_payable=original_total,
            status=InvoiceStatus.GENERATED
        )
        
        # Create Invoice Lines
        for service in services:
            service_total = service.service_charge - service.discount
            InvoiceLine.objects.create(
                invoice=invoice,
                booking_service=service,
                service_type=service.service_type.name,
                service_provider=service.service_provider,
                traveler_count=service.booking_travelers.exclude(passenger_status='CANCELLED').count(),
                taxable_amount=service_total,
                cgst_rate=gst_rate,
                cgst_amount=gst_amount,
                sgst_rate=Decimal("0.00"),
                sgst_amount=Decimal("0.00"),
                igst_rate=Decimal("0.00"),
                igst_amount=Decimal("0.00"),
                discount=service.discount,
                total=service_total + gst_amount
            )
        
        # Apply Credit Notes via CreditAllocation
        if applied_credit_notes:
            from apps.credit_notes.models import CreditAllocation
            from apps.credit_notes.choices import CreditNoteStatus
            
            for cn in applied_credit_notes:
                if cn.booking.customer != booking.customer:
                    raise ValidationError(f"Credit Note {cn.credit_note_number} belongs to a different customer.")
                
                remaining = cn.remaining_credit
                if remaining <= 0:
                    continue
                    
                # We can apply up to the remaining amount on the invoice
                amount_to_apply = remaining # For MVP, full credit note application or partial if logic dictates.
                
                if amount_to_apply > (original_total - credit_applied):
                    amount_to_apply = original_total - credit_applied
                
                if amount_to_apply <= 0:
                    continue
                    
                credit_applied += amount_to_apply
                
                CreditAllocation.objects.create(
                    credit_note=cn,
                    invoice=invoice,
                    amount=amount_to_apply
                )
                
                # Update Credit Note remaining balance manually
                cn.remaining_credit -= amount_to_apply
                
                if cn.remaining_credit <= 0:
                    cn.remaining_credit = Decimal("0.00")
                    cn.status = CreditNoteStatus.FULLY_APPLIED
                else:
                    cn.status = CreditNoteStatus.PARTIALLY_APPLIED
                cn.save(update_fields=['status', 'remaining_credit'])
                
        final_payable = original_total - credit_applied
        if final_payable < 0:
            final_payable = Decimal("0.00")
            
        booking.locked_at = timezone.now()
        booking.save(update_fields=['locked_at'])
        
        invoice.credit_applied = credit_applied
        invoice.final_payable = final_payable
        invoice.save(update_fields=['credit_applied', 'final_payable'])
        
        log_booking_history(
            booking=booking,
            action=BookingHistoryAction.INVOICE_GENERATED,
            description=f"Invoice {invoice_number} generated for {original_total}. Final payable: {final_payable}",
            metadata={
                "invoice_id": invoice.id,
                "original_total": str(original_total),
                "final_payable": str(final_payable)
            },
            user=user
        )
        return invoice

def cancel_invoice(invoice: Invoice, user=None) -> Invoice:
    """
    Cancel an invoice.
    """
    if invoice.status == InvoiceStatus.CANCELLED:
        return invoice
        
    with transaction.atomic():
        invoice.status = InvoiceStatus.CANCELLED
        invoice.save(update_fields=['status'])
        
        log_booking_history(
            booking=invoice.booking,
            action="INVOICE_CANCELLED",
            description=f"Invoice {invoice.invoice_number} was cancelled.",
            metadata={"invoice_id": invoice.id},
            user=user
        )
        return invoice

def update_invoice_status(invoice: Invoice) -> Invoice:
    """
    Update invoice status based on payments.
    This should be called whenever a payment is added or removed.
    """
    if invoice.status == InvoiceStatus.CANCELLED:
        return invoice
        
    with transaction.atomic():
        paid = invoice.paid_amount
        total = invoice.final_payable
        
        new_status = InvoiceStatus.GENERATED
        if paid >= total and total > 0:
            new_status = InvoiceStatus.PAID
        elif paid > 0:
            new_status = InvoiceStatus.PARTIALLY_PAID
            
        if invoice.status != new_status:
            invoice.status = new_status
            invoice.save(update_fields=['status'])
            
        return invoice
