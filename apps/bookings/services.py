from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.bookings.models import Booking, BookingService, BookingTraveler, BookingHistory, ServiceType
from apps.credit_notes.models import CreditNote

from apps.invoices.models import Invoice
from apps.bookings.choices import BookingStatus, BookingServiceStatus, PassengerStatus, BookingHistoryAction
from apps.common.number_generator import generate_booking_number, generate_invoice_number, generate_credit_note_number

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

def create_booking(booking: Booking, user=None) -> Booking:
    """
    Create a new booking and generate a unique booking number.
    
    Used when starting a new trip for a customer.
    """
    with transaction.atomic():
        # Generate booking number: BKG-YYYYMMDD-ID
        # For a truly race-safe sequence, PostgreSQL sequences or a dedicated counter model should be used.
        # For this MVP, a timestamp-based ID is sufficient and avoids locking the whole table.
        booking_number = generate_booking_number()
        
        booking.booking_number = booking_number
        booking.save()
        
        log_booking_history(
            booking=booking,
            action=BookingHistoryAction.BOOKING_CREATED,
            description=f"Booking created for {booking.customer.name}.",
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

def cancel_passenger_with_credit(traveler: BookingTraveler, data: dict, user=None):
    """
    Cancel a passenger and optionally generate a Credit Note.
    
    IMPORTANT:
    - Booking = operational workflow. Bookings remain manually cancellable even when all services are cancelled.
    - Invoice = immutable legal snapshot.
    - Payment = money received.
    - Credit Note = financial adjustment.
    - BookingHistory = audit trail.
    """
    if traveler.passenger_status == PassengerStatus.CANCELLED:
        from django.core.exceptions import ValidationError
        raise ValidationError(f"Passenger {traveler.traveler.first_name} is already cancelled.")
        
    with transaction.atomic():
        traveler.passenger_status = PassengerStatus.CANCELLED
        traveler.cancel_reason = data.get('reason', '')
        traveler.cancelled_by = user
        traveler.cancelled_at = timezone.now()
        traveler.save(update_fields=['passenger_status', 'cancel_reason', 'cancelled_by', 'cancelled_at'])
        
        booking_service = traveler.booking_service
        booking = booking_service.booking
        
        # Check if booking service should be cancelled
        if not booking_service.booking_travelers.exclude(passenger_status=PassengerStatus.CANCELLED).exists():
            booking_service.status = BookingServiceStatus.CANCELLED
            booking_service.save(update_fields=['status'])
        
        # We no longer auto-cancel the Booking here.
        
        log_booking_history(
            booking=booking,
            action=BookingHistoryAction.PASSENGER_CANCELLED,
            description=f"Passenger {traveler.traveler.first_name} cancelled on service {booking_service.service_type.name}. Reason: {data.get('reason')}",
            metadata={
                "booking_service_id": booking_service.id,
                "traveler_id": traveler.traveler.id
            },
            user=user
        )
        
        if data.get('issue_credit_note'):
            if user and not user.has_perm('credit_notes.add_creditnote'):
                from django.core.exceptions import ValidationError
                raise ValidationError("You do not have permission to generate a Credit Note.")
                
            from apps.credit_notes.models import CreditNote, CreditNoteLine
            from apps.common.number_generator import generate_credit_note_number
            from apps.credit_notes.choices import CreditNoteStatus
            from apps.invoices.services import update_invoice_status
            from decimal import Decimal
            
            total_refund = (
                data['taxable_refund'] +
                data['cgst_amount'] +
                data['sgst_amount'] +
                data['igst_amount']
            )
            
            # Validate supplier refund
            supplier_expected = data['supplier_refund_expected']
            if supplier_expected < Decimal("0.00"):
                from django.core.exceptions import ValidationError
                raise ValidationError("Supplier refund expected cannot be negative.")
            
            invoice = getattr(booking, 'invoice', None)
            invoice_line = None
            
            if invoice:
                invoice_line = invoice.lines.filter(booking_service=booking_service).first()
                if invoice_line:
                    from django.db.models import Sum
                    already_refunded = CreditNoteLine.objects.filter(invoice_line=invoice_line).aggregate(sum_total=Sum('total'))['sum_total'] or Decimal("0.00")
                    if already_refunded + total_refund > invoice_line.total:
                        from django.core.exceptions import ValidationError
                        raise ValidationError(f"Total refund ({total_refund}) plus already refunded amount ({already_refunded}) cannot exceed the invoice line total ({invoice_line.total}).")
            
            cn = CreditNote.objects.create(
                booking=booking,
                invoice=invoice,
                credit_note_number=generate_credit_note_number(),
                issued_date=timezone.now().date(),
                supplier_refund_expected=supplier_expected,
                supplier_refund_received=Decimal("0.00"),
                total_credit=total_refund,
                remaining_credit=total_refund,
                reason=data['reason'],
                cancelled_by=user,
                cancelled_at=timezone.now(),
                status=CreditNoteStatus.ACTIVE
            )
            
            cn_line = CreditNoteLine.objects.create(
                credit_note=cn,
                invoice_line=invoice_line,
                booking_traveler=traveler,
                description=f"Refund for passenger {traveler.traveler.first_name}",
                taxable_refund=data['taxable_refund'],
                cgst_rate=data['cgst_rate'],
                cgst_amount=data['cgst_amount'],
                sgst_rate=data['sgst_rate'],
                sgst_amount=data['sgst_amount'],
                igst_rate=data['igst_rate'],
                igst_amount=data['igst_amount'],
                total=total_refund
            )
            
            action = getattr(BookingHistoryAction, 'CREDIT_NOTE_GENERATED', BookingHistoryAction.BOOKING_UPDATED)
            
            log_booking_history(
                booking=booking,
                action=action,
                description=f"Credit Note {cn.credit_note_number} generated for {total_refund}.",
                metadata={
                    "credit_note_id": cn.id,
                    "refund_amount": str(total_refund),
                    "invoice_line_id": invoice_line.id if invoice_line else None,
                    "invoice_id": invoice.id if invoice else None,
                    "traveler_id": traveler.traveler.id
                },
                user=user
            )

