from django.db import transaction
from django.utils import timezone
from apps.invoices.models import Invoice
from apps.invoices.choices import InvoiceStatus
from apps.bookings.models import Booking
from apps.bookings.choices import BookingStatus, BookingServiceStatus, BookingHistoryAction
from apps.common.number_generator import generate_invoice_number
from apps.bookings.services import log_booking_history
from django.core.exceptions import ValidationError

def generate_invoice(booking: Booking, user=None) -> Invoice:
    """
    Generate an invoice for a confirmed booking.
    
    Rules:
    - Validate Booking is CONFIRMED.
    - Validate Booking has at least one BookingService.
    - Prevent duplicate invoices.
    - Copy Booking financial totals into the Invoice.
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
            
        subtotal = sum((service.selling_price - service.discount) for service in services)
        gst_rate = 0  # Assuming 0 for now as MVP didn't specify dynamic calculation
        gst_amount = 0
        grand_total = subtotal + gst_amount
        
        invoice_number = generate_invoice_number()
        
        invoice = Invoice.objects.create(
            booking=booking,
            invoice_number=invoice_number,
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date(),  # Could be customized if needed
            subtotal=subtotal,
            gst_rate=gst_rate,
            gst_amount=gst_amount,
            grand_total=grand_total,
            status=InvoiceStatus.PENDING
        )
        
        booking.locked_at = timezone.now()
        booking.save(update_fields=['locked_at'])
        
        log_booking_history(
            booking=booking,
            action=BookingHistoryAction.INVOICE_GENERATED,
            description=f"Invoice {invoice_number} generated for {grand_total}.",
            metadata={
                "invoice_number": invoice_number,
                "grand_total": str(grand_total)
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
        
        # Optionally unlock the booking or handle differently
        # For KISS MVP, we just mark it cancelled.
        log_booking_history(
            booking=invoice.booking,
            action="INVOICE_CANCELLED",  # Using generic string since we don't have it in BookingHistoryAction
            description=f"Invoice {invoice.invoice_number} was cancelled.",
            metadata={"invoice_number": invoice.invoice_number},
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
        total = invoice.grand_total
        
        new_status = InvoiceStatus.PENDING
        if paid >= total and total > 0:
            new_status = InvoiceStatus.PAID
        elif paid > 0:
            new_status = InvoiceStatus.PARTIALLY_PAID
            
        if invoice.status != new_status:
            invoice.status = new_status
            invoice.save(update_fields=['status'])
            
        return invoice
