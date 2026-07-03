from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.bookings.models import Booking, BookingService, BookingTraveler, BookingHistory
from apps.credit_notes.models import CreditNote
from apps.vouchers.models import Voucher
from apps.invoices.models import Invoice
from apps.common.choices import BookingStatus, BookingServiceStatus, PassengerStatus, InvoiceType

def cancel_passenger(booking_traveler: BookingTraveler, user=None, refund_amount: Decimal = Decimal('0.00'), create_credit_note: bool = False, create_voucher: bool = False, cancellation_reason: str = ""):
    with transaction.atomic():
        booking_traveler.passenger_status = PassengerStatus.CANCELLED
        booking_traveler.cancellation_reason = cancellation_reason
        booking_traveler.save()
        
        booking = booking_traveler.booking_service.booking
        history_msg = f"Passenger {booking_traveler.traveler.full_name} cancelled."
        
        if refund_amount > 0 and create_credit_note:
            cn = CreditNote.objects.create(
                booking=booking,
                credit_note_number=f"CN-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                amount=refund_amount,
                remaining_amount=refund_amount,
                reason=f"Refund for passenger {booking_traveler.traveler.full_name}",
                issued_date=timezone.now().date(),
                voucher_created=create_voucher
            )
            history_msg += f" Refund ₹{refund_amount}. Credit Note {cn.credit_note_number} created."
            
            if create_voucher:
                vch = Voucher.objects.create(
                    customer=booking.customer,
                    credit_note=cn,
                    voucher_number=f"VCH-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                    original_amount=refund_amount,
                    remaining_balance=refund_amount,
                    issued_date=timezone.now().date(),
                    reason=f"Voucher from CN {cn.credit_note_number}"
                )
                history_msg += f" Voucher {vch.voucher_number} created."

        BookingHistory.objects.create(
            booking=booking,
            action="Passenger Cancelled",
            description=history_msg,
            user=user
        )
        return True

def cancel_service(booking_service: BookingService, user=None, cancel_passengers: bool = True):
    with transaction.atomic():
        booking_service.status = BookingServiceStatus.CANCELLED
        booking_service.save()
        
        if cancel_passengers:
            for bt in booking_service.booking_travelers.all():
                bt.passenger_status = PassengerStatus.CANCELLED
                bt.save()
                
        BookingHistory.objects.create(
            booking=booking_service.booking,
            action="Service Cancelled",
            description=f"Service {booking_service.service_type.name} cancelled.",
            user=user
        )
        return True

def cancel_booking(booking: Booking, user=None):
    with transaction.atomic():
        booking.status = BookingStatus.CANCELLED
        booking.save()
        
        for service in booking.services.all():
            cancel_service(service, user, cancel_passengers=True)
            
        BookingHistory.objects.create(
            booking=booking,
            action="Booking Cancelled",
            description=f"Entire Booking {booking.booking_number} cancelled.",
            user=user
        )
        return True

def confirm_booking(booking: Booking, user=None):
    if booking.services.count() == 0:
        raise ValueError("Cannot confirm a booking with no services.")

    with transaction.atomic():
        booking.status = BookingStatus.CONFIRMED
        booking.save()
        BookingHistory.objects.create(
            booking=booking,
            action="Booking Confirmed",
            description="Booking confirmed manually.",
            user=user
        )
        return True

def generate_invoice(booking: Booking, user=None, invoice_type=InvoiceType.TAX):
    if booking.status != BookingStatus.CONFIRMED:
        raise ValueError("Booking must be Confirmed to generate an invoice.")
    
    with transaction.atomic():
        total_selling_price = sum(service.selling_price - service.discount for service in booking.services.exclude(status=BookingServiceStatus.CANCELLED))
        
        invoice = Invoice.objects.create(
            booking=booking,
            invoice_number=f"INV-{timezone.now().strftime('%Y%m%d%H%M%S')}",
            invoice_type=invoice_type,
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date(),
            total_amount=total_selling_price
        )
        
        BookingHistory.objects.create(
            booking=booking,
            action="Invoice Generated",
            description=f"Invoice {invoice.invoice_number} generated for {total_selling_price}.",
            user=user
        )
        return invoice
