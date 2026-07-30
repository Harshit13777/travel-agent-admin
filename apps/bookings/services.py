from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.bookings.models import Booking, BookingService, BookingTraveler, BookingHistory, ServiceType
from apps.credit_notes.models import CreditNote

from django.forms.models import model_to_dict
from apps.invoices.models import Invoice
from apps.bookings.choices import BookingStatus, PassengerStatus, BookingHistoryAction
from apps.common.number_generator import generate_booking_number, generate_invoice_number, generate_credit_note_number

def log_booking_history(booking, action, user, description="", metadata=None, old_state=None, new_state=None):
    """
    Centralized helper to log booking history events.
    Ensures all history is routed through a single point.
    """
    if metadata is None:
        metadata = {}
        
    if old_state and new_state:
        diff = {}
        for key in new_state:
            old_val = old_state.get(key)
            new_val = new_state.get(key)
            if old_val != new_val:
                # Convert values to strings for JSON serialization if they are not basic types
                diff[key] = {"old": str(old_val) if old_val is not None else None, 
                             "new": str(new_val) if new_val is not None else None}
        if diff:
            metadata["state_changes"] = diff
            
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
            metadata={"booking_id": booking.id},
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
        booking_service.soft_delete()
        log_booking_history(
            booking=booking,
            action=BookingHistoryAction.SERVICE_DELETED,
            description=f"Service {service_name} was deleted before invoice.",
            metadata={"booking_service_id": service_id},
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
        booking_traveler.soft_delete()
        log_booking_history(
            booking=booking,
            action=BookingHistoryAction.PASSENGER_DELETED,
            description=f"Passenger {traveler_name} was deleted before invoice.",
            metadata={"traveler_id": traveler_id},
            user=user
        )
        return True





def confirm_booking(booking: Booking, user=None) -> Booking:
    """
    Mark a booking as operationally confirmed.
    
    Trusts the agent's decision even if mixed statuses exist.
    """
    if booking.services.count() == 0:
        from django.core.exceptions import ValidationError
        raise ValidationError("Cannot confirm a booking with no services.")

    with transaction.atomic():
        log_booking_history(
            booking=booking,
            action=BookingHistoryAction.BOOKING_CONFIRMED,
            description="Booking confirmed manually.",
            metadata={"booking_id": booking.id},
            user=user
        )
        return booking





def update_booking_traveler(booking_traveler, user=None):
    """
    Validates and updates a BookingTraveler.
    Business logic: Cannot modify financial fields once invoiced.
    """
    is_new = not booking_traveler.pk
    old_state = None
    booking = booking_traveler.booking_service.booking
    
    if not is_new:
        original = BookingTraveler.objects.get(pk=booking_traveler.pk)
        old_state = model_to_dict(original)
        
        # Check if they have an active cancellation
        from apps.cancellations.models import BookingCancellation
        has_cancellation = BookingCancellation.objects.filter(
            invoice_line_traveler__booking_traveler=booking_traveler
        ).exists()
        
        if has_cancellation:
            from django.core.exceptions import ValidationError
            raise ValidationError(f"Cannot modify passenger {original.traveler.first_name} because they are cancelled.")
            
        if booking.is_locked:
            if (original.supplier_cost != booking_traveler.supplier_cost or 
                original.service_charge != booking_traveler.service_charge or 
                original.is_gst_applicable != booking_traveler.is_gst_applicable or
                original.traveler_id != booking_traveler.traveler_id):
                from django.core.exceptions import ValidationError
                raise ValidationError("Cannot modify financial fields or traveler reference after the booking is invoiced.")
        
    booking_traveler.save()
    
    new_state = model_to_dict(booking_traveler)
    # Audit log
    action = BookingHistoryAction.PASSENGER_ADDED if is_new else BookingHistoryAction.PASSENGER_UPDATED
    log_booking_history(
        booking=booking,
        action=action,
        description=f"Passenger {booking_traveler.traveler.full_name} details updated.",
        metadata={
            "booking_service_id": booking_traveler.booking_service.id,
            "traveler_id": booking_traveler.traveler.id
        },
        old_state=old_state,
        new_state=new_state,
        user=user
    )


def update_booking(booking, user=None):
    old_state = None
    if booking.pk:
        old_state = model_to_dict(Booking.objects.get(pk=booking.pk))
        
            
    if booking.journey_start and booking.journey_end and booking.journey_end < booking.journey_start:
        from django.core.exceptions import ValidationError
        raise ValidationError({'journey_end': 'Journey end cannot be before journey start.'})
    booking.save()
    new_state = model_to_dict(booking)
    
    log_booking_history(
        booking=booking,
        action=BookingHistoryAction.BOOKING_UPDATED,
        description=f"Booking {booking.booking_number} details updated.",
        metadata={"booking_id": booking.id},
        old_state=old_state,
        new_state=new_state,
        user=user
    )

def update_booking_service(booking_service, user=None):
    is_new = not booking_service.pk
    old_state = None
    if not is_new:
        original = BookingService.objects.get(pk=booking_service.pk)
        old_state = model_to_dict(original)
        if original.booking.is_locked:
            if original.booking_id != booking_service.booking_id or original.service_type_id != booking_service.service_type_id or original.supplier_id != booking_service.supplier_id:
                from django.core.exceptions import ValidationError
                raise ValidationError("Cannot modify booking, service type, or supplier after the booking is invoiced.")
            
    if booking_service.journey_start and booking_service.journey_end and booking_service.journey_end < booking_service.journey_start:
        from django.core.exceptions import ValidationError
        raise ValidationError({'journey_end': 'Journey end cannot be before journey start.'})
    booking_service.save()
    new_state = model_to_dict(booking_service)
    
    action = BookingHistoryAction.SERVICE_CREATED if is_new else BookingHistoryAction.SERVICE_UPDATED
    log_booking_history(
        booking=booking_service.booking,
        action=action,
        description=f"Service {booking_service.service_type.name} details updated.",
        metadata={"booking_service_id": booking_service.id},
        old_state=old_state,
        new_state=new_state,
        user=user
    )



def delete_booking(booking, user=None):
    from django.core.exceptions import ValidationError
    if booking.is_locked:
        raise ValidationError("Cannot delete a booking after an invoice has been generated.")
        
    booking_number = booking.booking_number
    # Log before delete since it might cascade
    log_booking_history(
        booking=booking,
        action=BookingHistoryAction.BOOKING_DELETED,
        description=f"Booking {booking_number} deleted.",
        metadata={"booking_id": booking.id},
        user=user
    )
    booking.soft_delete()
