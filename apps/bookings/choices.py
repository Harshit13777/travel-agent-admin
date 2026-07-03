from django.db import models

class BookingStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    CONFIRMED = 'CONFIRMED', 'Confirmed'
    COMPLETED = 'COMPLETED', 'Completed'
    CANCELLED = 'CANCELLED', 'Cancelled'

class BookingServiceStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    CONFIRMED = 'CONFIRMED', 'Confirmed'
    CANCELLED = 'CANCELLED', 'Cancelled'
    COMPLETED = 'COMPLETED', 'Completed'

class PassengerStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    CONFIRMED = 'CONFIRMED', 'Confirmed'
    WAITING = 'WAITING', 'Waiting'
    CANCELLED = 'CANCELLED', 'Cancelled'
    CHECKED_IN = 'CHECKED_IN', 'Checked In'
    BOARDED = 'BOARDED', 'Boarded'
    COMPLETED = 'COMPLETED', 'Completed'

class BookingSource(models.TextChoices):
    WALK_IN = 'WALK_IN', 'Walk In'
    WHATSAPP = 'WHATSAPP', 'WhatsApp'
    PHONE = 'PHONE', 'Phone'
    WEBSITE = 'WEBSITE', 'Website'
    CORPORATE = 'CORPORATE', 'Corporate'
    REFERENCE = 'REFERENCE', 'Reference'

class Priority(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    URGENT = 'URGENT', 'Urgent'

class BookingHistoryAction(models.TextChoices):
    BOOKING_CREATED = 'BOOKING_CREATED', 'Booking Created'
    BOOKING_CONFIRMED = 'BOOKING_CONFIRMED', 'Booking Confirmed'
    BOOKING_CANCELLED = 'BOOKING_CANCELLED', 'Booking Cancelled'
    SERVICE_CANCELLED = 'SERVICE_CANCELLED', 'Service Cancelled'
    SERVICE_DELETED = 'SERVICE_DELETED', 'Service Deleted'
    PASSENGER_CANCELLED = 'PASSENGER_CANCELLED', 'Passenger Cancelled'
    PASSENGER_DELETED = 'PASSENGER_DELETED', 'Passenger Deleted'
    INVOICE_GENERATED = 'INVOICE_GENERATED', 'Invoice Generated'
    INVOICE_CANCELLED = 'INVOICE_CANCELLED', 'Invoice Cancelled'
    CREDIT_NOTE_GENERATED = 'CREDIT_NOTE_GENERATED', 'Credit Note Generated'
    CREDIT_NOTE_VOIDED = 'CREDIT_NOTE_VOIDED', 'Credit Note Voided'
