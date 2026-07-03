from django.db import models

class CustomerType(models.TextChoices):
    CORPORATE = 'CORPORATE', 'Corporate'
    INDIVIDUAL = 'INDIVIDUAL', 'Individual'
    TRAVEL_AGENT = 'TRAVEL_AGENT', 'Travel Agent'

class Gender(models.TextChoices):
    MALE = 'M', 'Male'
    FEMALE = 'F', 'Female'
    OTHER = 'OTHER', 'Other'

class IdentityType(models.TextChoices):
    PASSPORT = 'PASSPORT', 'Passport'
    AADHAAR = 'AADHAAR', 'Aadhaar'
    PAN = 'PAN', 'PAN'
    DRIVING_LICENSE = 'DRIVING_LICENSE', 'Driving License'
    OTHER = 'OTHER', 'Other'

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

class InvoiceType(models.TextChoices):
    TAX = 'TAX', 'Tax Invoice'
    PROFORMA = 'PROFORMA', 'Proforma'

class InvoiceStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    UNPAID = 'UNPAID', 'Unpaid'
    PARTIAL = 'PARTIAL', 'Partially Paid'
    PAID = 'PAID', 'Paid'
    CANCELLED = 'CANCELLED', 'Cancelled'

class PaymentMethod(models.TextChoices):
    CASH = 'CASH', 'Cash'
    BANK_TRANSFER = 'BANK_TRANSFER', 'Bank Transfer'
    UPI = 'UPI', 'UPI'
    CREDIT_CARD = 'CREDIT_CARD', 'Credit Card'
    CHEQUE = 'CHEQUE', 'Cheque'

class VoucherStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    USED = 'USED', 'Used'
    EXPIRED = 'EXPIRED', 'Expired'
    CANCELLED = 'CANCELLED', 'Cancelled'
