from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.bookings.models import Booking, BookingService, BookingTraveler, BookingHistory, ServiceType
from apps.credit_notes.models import CreditNote
from apps.vouchers.models import Voucher
from apps.invoices.models import Invoice
from apps.common.choices import InvoiceType
from apps.bookings.choices import BookingStatus, BookingServiceStatus, PassengerStatus, BookingHistoryAction
from apps.common.number_generator import generate_booking_number, generate_invoice_number, generate_credit_note_number, generate_voucher_number

def log_booking_history(booking, action, user, description="", metadata=None):
    """
    Centralized helper to log booking history events.
    Ensures all history is routed through a single point.
    """
    if metadata is None:
        metadata = {}
    return BookingHistory.objects.create(
        booking=booking,
        action=action,
        description=description,
        metadata=metadata,
        user=user
    )

def create_booking(customer, user=None, **kwargs) -> Booking:
    """
    Create a new booking and generate a unique booking number.
    
    Used when starting a new trip for a customer.
    """
    with transaction.atomic():
        # Generate booking number: BKG-YYYYMMDD-ID
        # For a truly race-safe sequence, PostgreSQL sequences or a dedicated counter model should be used.
        # For this MVP, a timestamp-based ID is sufficient and avoids locking the whole table.
        booking_number = generate_booking_number()
        
        booking = Booking.objects.create(
            booking_number=booking_number,
            customer=customer,
            **kwargs
        )
        
        log_booking_history(
            booking=booking,
            action=BookingHistoryAction.BOOKING_CREATED,
            description=f"Booking created for {customer.name}.",
            metadata={"booking_number": booking_number},
            user=user
        )
        return booking

def delete_booking_service(booking_service: BookingService, user=None) -> BookingService:
    """
    Delete a service completely from the booking.
    
    Only permitted before the booking is locked (invoiced).
    """
    booking = booking_service.booking
    if booking.is_locked:
        from django.core.exceptions import ValidationError
        raise ValidationError("Cannot delete a service after the booking is locked. Cancel it instead.")
        
    with transaction.atomic():
        service_name = booking_service.service_type.name
        service_id = booking_service.id
        booking_service.delete()
        log_booking_history(
            booking=booking,
            action=BookingHistoryAction.SERVICE_DELETED,
            description=f"Service {service_name} was deleted before invoice.",
            metadata={"service_id": service_id},
            user=user
        )
        return True

def delete_booking_traveler(booking_traveler: BookingTraveler, user=None) -> BookingTraveler:
    """
    Delete a passenger completely from the service.
    
    Only permitted before the booking is locked (invoiced).
    """
    booking = booking_traveler.booking_service.booking
    if booking.is_locked:
        from django.core.exceptions import ValidationError
        raise ValidationError("Cannot delete a passenger after the booking is locked. Cancel them instead.")
        
    with transaction.atomic():
        traveler_name = booking_traveler.traveler.full_name
        traveler_id = booking_traveler.traveler.id
        booking_traveler.delete()
        log_booking_history(
            booking=booking,
            action=BookingHistoryAction.PASSENGER_DELETED,
            description=f"Passenger {traveler_name} was deleted before invoice.",
            metadata={"traveler_id": traveler_id},
            user=user
        )
        return True

def cancel_passenger(booking_traveler: BookingTraveler, user=None, refund_amount: Decimal = Decimal('0.00'), create_credit_note: bool = False, create_voucher: bool = False, cancellation_reason: str = "") -> BookingTraveler:
    """
    Cancel a passenger and optionally generate a refund.
    
    This preserves the financial history without deleting the record.
    """
    with transaction.atomic():
        booking_traveler.passenger_status = PassengerStatus.CANCELLED
        booking_traveler.cancellation_reason = cancellation_reason
        booking_traveler.save()
        
        booking = booking_traveler.booking_service.booking
        history_msg = f"Passenger {booking_traveler.traveler.full_name} cancelled."
        metadata = {
            "traveler_id": booking_traveler.traveler.id,
            "service_id": booking_traveler.booking_service.id
        }

        if refund_amount > 0 and create_credit_note:
            cn_number = generate_credit_note_number()
            cn = CreditNote.objects.create(
                booking=booking,
                credit_note_number=cn_number,
                amount=refund_amount,
                remaining_amount=refund_amount,
                reason=f"Refund for passenger {booking_traveler.traveler.full_name}",
                issued_date=timezone.now().date(),
                voucher_created=create_voucher
            )
            history_msg += f" Refund ₹{refund_amount}. Credit Note {cn_number} created."
            metadata["refund_amount"] = str(refund_amount)
            metadata["credit_note_number"] = cn_number
            
            if create_voucher:
                vch_number = generate_voucher_number()
                vch = Voucher.objects.create(
                    customer=booking.customer,
                    credit_note=cn,
                    voucher_number=vch_number,
                    original_amount=refund_amount,
                    remaining_balance=refund_amount,
                    issued_date=timezone.now().date(),
                    reason=f"Voucher from CN {cn_number}"
                )
                history_msg += f" Voucher {vch_number} created."
                metadata["voucher_number"] = vch_number

        log_booking_history(
            booking=booking,
            action=BookingHistoryAction.PASSENGER_CANCELLED,
            description=history_msg,
            metadata=metadata,
            user=user
        )
        return booking_traveler

def cancel_service(booking_service: BookingService, user=None, cancel_passengers: bool = True) -> BookingService:
    """
    Cancel an entire service and optionally its passengers.
    
    This preserves the financial history without deleting the record.
    """
    with transaction.atomic():
        booking_service.status = BookingServiceStatus.CANCELLED
        booking_service.save()
        
        if cancel_passengers:
            for bt in booking_service.booking_travelers.all():
                bt.passenger_status = PassengerStatus.CANCELLED
                bt.save()
                
        log_booking_history(
            booking=booking_service.booking,
            action=BookingHistoryAction.SERVICE_CANCELLED,
            description=f"Service {booking_service.service_type.name} cancelled.",
            metadata={"service_id": booking_service.id},
            user=user
        )
        return booking_service

def cancel_booking(booking: Booking, user=None) -> Booking:
    """
    Cancel an entire booking and all underlying services.
    
    This preserves the financial history without deleting the record.
    """
    with transaction.atomic():
        booking.status = BookingStatus.CANCELLED
        booking.save()
        
        for service in booking.services.all():
            cancel_service(service, user, cancel_passengers=True)
            
        log_booking_history(
            booking=booking,
            action=BookingHistoryAction.BOOKING_CANCELLED,
            description=f"Entire Booking {booking.booking_number} cancelled.",
            metadata={"booking_number": booking.booking_number},
            user=user
        )
        return booking

def confirm_booking(booking: Booking, user=None) -> Booking:
    """
    Mark a booking as operationally confirmed.
    
    Trusts the agent's decision even if mixed statuses exist.
    """
    if booking.services.count() == 0:
        from django.core.exceptions import ValidationError
        raise ValidationError("Cannot confirm a booking with no services.")

    with transaction.atomic():
        booking.status = BookingStatus.CONFIRMED
        booking.save()
        log_booking_history(
            booking=booking,
            action=BookingHistoryAction.BOOKING_CONFIRMED,
            description="Booking confirmed manually.",
            user=user
        )
        return booking

def generate_invoice(booking: Booking, user=None, invoice_type=InvoiceType.TAX) -> Invoice:
    """
    Generate an invoice for a confirmed booking.

    This permanently locks the booking for financial edits.
    """
    if booking.status != BookingStatus.CONFIRMED:
        from django.core.exceptions import ValidationError
        raise ValidationError("Booking must be Confirmed to generate an invoice.")
    
    with transaction.atomic():
        total_selling_price = sum(service.selling_price - service.discount for service in booking.services.exclude(status=BookingServiceStatus.CANCELLED))
        
        invoice_number = generate_invoice_number()
        invoice = Invoice.objects.create(
            booking=booking,
            invoice_number=invoice_number,
            invoice_type=invoice_type,
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date(),
            total_amount=total_selling_price
        )
        
        booking.locked_at = timezone.now()
        booking.save(update_fields=['locked_at'])
        
        log_booking_history(
            booking=booking,
            action=BookingHistoryAction.INVOICE_GENERATED,
            description=f"Invoice {invoice_number} generated for {total_selling_price}.",
            metadata={
                "invoice_number": invoice_number,
                "total_amount": str(total_selling_price)
            },
            user=user
        )
        return invoice
