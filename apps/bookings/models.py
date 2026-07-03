from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from apps.common.models import AuditModel
from apps.customers.models import Customer, Supplier
from apps.travelers.models import Traveler
from apps.common.choices import (
    BookingStatus, BookingServiceStatus,
    PassengerStatus, BookingSource, Priority
)

class Booking(AuditModel):
    booking_number = models.CharField(max_length=20, unique=True, db_index=True)
    title = models.CharField(max_length=200, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='bookings')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_bookings')
    booking_source = models.CharField(max_length=50, choices=BookingSource.choices, default=BookingSource.WALK_IN)
    priority = models.CharField(max_length=50, choices=Priority.choices, default=Priority.MEDIUM)
    journey_start = models.DateField(null=True, blank=True)
    journey_end = models.DateField(null=True, blank=True)
    expected_payment_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=BookingStatus.choices, default=BookingStatus.DRAFT)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Booking"
        verbose_name_plural = "Bookings"

    def clean(self):
        # clean() is only for model data validation (e.g., date checks).
        # Business workflow logic belongs in services.py
        if self.journey_start and self.journey_end and self.journey_end < self.journey_start:
            from django.core.exceptions import ValidationError
            raise ValidationError({'journey_end': 'Journey end cannot be before journey start.'})

    def __str__(self):
        title_str = f" - {self.title}" if self.title else ""
        return f"{self.booking_number}{title_str} ({self.customer.name})"

    @property
    def total_supplier_cost(self):
        return sum(service.supplier_cost for service in self.services.exclude(status=BookingServiceStatus.CANCELLED))

    @property
    def total_selling_price(self):
        return sum(service.selling_price for service in self.services.exclude(status=BookingServiceStatus.CANCELLED))
        
    @property
    def total_discount(self):
        return sum(service.discount for service in self.services.exclude(status=BookingServiceStatus.CANCELLED))

    @property
    def has_invoice(self):
        return self.invoices.exists()
        
    @property
    def is_locked(self):
        return self.has_invoice

    @property
    def invoice_total(self):
        return sum(inv.total_amount for inv in self.invoices.exclude(status='CANCELLED'))

    @property
    def paid_amount(self):
        # We will sum payments related to invoices. For now, assuming payment models can be queried.
        # This requires importing Payment or querying via reverse relations if set up.
        # A simpler way is sum(inv.paid_amount for inv in self.invoices) if invoice has paid_amount.
        return sum(inv.paid_amount for inv in self.invoices.exclude(status='CANCELLED'))

    @property
    def credit_note_amount(self):
        return sum(cn.amount for cn in self.credit_notes.all())

    @property
    def outstanding_amount(self):
        return self.invoice_total - self.paid_amount - self.credit_note_amount
        
    @property
    def total_profit(self):
        return self.total_selling_price - self.total_discount - self.total_supplier_cost


class ServiceType(AuditModel):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = "Service Type"
        verbose_name_plural = "Service Types"

    def __str__(self):
        return self.name


class BookingService(AuditModel):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='services')
    display_order = models.PositiveIntegerField(default=1)
    service_type = models.ForeignKey(ServiceType, on_delete=models.PROTECT)
    service_provider = models.CharField(max_length=100, blank=True)
    journey_start = models.DateTimeField(null=True, blank=True)
    journey_end = models.DateTimeField(null=True, blank=True)
    from_location = models.CharField(max_length=100, blank=True)
    to_location = models.CharField(max_length=100, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='booking_services')
    reference_number = models.CharField(max_length=50, blank=True, db_index=True)
    status = models.CharField(max_length=50, choices=BookingServiceStatus.choices, default=BookingServiceStatus.PENDING)
    currency = models.CharField(max_length=3, default='INR')
    supplier_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    remarks = models.TextField(blank=True)

    class Meta:
        verbose_name = "Booking Service"
        verbose_name_plural = "Booking Services"
        ordering = ['display_order']

    def __str__(self):
        return f"{self.service_type.name} for {self.booking.booking_number}"

    @property
    def net_price(self):
        return self.selling_price - self.discount

    @property
    def profit(self):
        return self.net_price - self.supplier_cost

    def clean(self):
        if self.journey_start and self.journey_end and self.journey_end < self.journey_start:
            raise ValidationError({'journey_end': 'Journey end cannot be before journey start.'})

class BookingTraveler(AuditModel):
    booking_service = models.ForeignKey(BookingService, on_delete=models.CASCADE, related_name='booking_travelers')
    traveler = models.ForeignKey(Traveler, on_delete=models.PROTECT, related_name='booking_travelers')
    passenger_status = models.CharField(max_length=50, choices=PassengerStatus.choices, default=PassengerStatus.CONFIRMED)
    ticket_number = models.CharField(max_length=50, blank=True)
    seat_details = models.CharField(max_length=20, blank=True)
    check_in_status = models.CharField(max_length=50, blank=True)
    fare = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    baggage = models.CharField(max_length=100, blank=True)
    cancellation_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = "Booking Traveler"
        verbose_name_plural = "Booking Travelers"
        constraints = [
            models.UniqueConstraint(
                fields=["booking_service", "traveler"],
                name="unique_booking_service_traveler"
            )
        ]

    def __str__(self):
        return f"{self.traveler.full_name} - {self.booking_service}"


class BookingHistory(AuditModel):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='history')
    action = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Booking History"
        verbose_name_plural = "Booking Histories"

    def __str__(self):
        return f"{self.booking.booking_number} - {self.action}"
