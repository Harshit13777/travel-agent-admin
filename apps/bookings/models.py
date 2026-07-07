from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from apps.common.models import AuditModel
from apps.common.constants import ZERO_AMOUNT
from apps.customers.models import Customer, Supplier
from apps.travelers.models import Traveler
from apps.bookings.choices import (
    BookingStatus, PassengerStatus, BookingSource, Priority
)

class Booking(AuditModel):
    booking_number = models.CharField(max_length=20, unique=True, db_index=True)
    title = models.CharField(max_length=200, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='bookings')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_bookings')
    status = models.CharField(max_length=50, choices=BookingStatus.choices, default=BookingStatus.INQUIRY)
    booking_source = models.CharField(max_length=50, choices=BookingSource.choices, default=BookingSource.WALK_IN)
    priority = models.CharField(max_length=50, choices=Priority.choices, default=Priority.MEDIUM)
    journey_start = models.DateField(null=True, blank=True, db_index=True)
    journey_end = models.DateField(null=True, blank=True)
    expected_payment_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Booking"
        verbose_name_plural = "Bookings"

    def __str__(self):
        title_str = f" - {self.title}" if self.title else ""
        return f"{self.booking_number}{title_str} ({self.customer.name})"



    @property
    def total_supplier_cost(self):
        return sum(service.total_supplier_cost for service in self.services.all())

    @property
    def total_service_charge(self):
        return sum(service.total_service_charge for service in self.services.all())
        
    @property
    def has_invoice(self):
        return self.invoices.exists()
        
    @property
    def is_locked(self):
        return self.locked_at is not None

    @property
    def invoice_total(self):
        return sum(inv.total_amount for inv in self.invoices.exclude(status='CANCELLED'))

    @property
    def paid_amount(self):
        return sum(inv.paid_amount for inv in self.invoices.exclude(status='CANCELLED'))

    @property
    def credit_note_amount(self):
        return sum(cn.amount for cn in self.credit_notes.all())

    @property
    def outstanding_amount(self):
        return self.invoice_total - self.paid_amount - self.credit_note_amount
        
    @property
    def total_profit(self):
        return self.total_service_charge - self.total_supplier_cost


class ServiceType(AuditModel):
    name = models.CharField(max_length=50, unique=True)
    display_order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Service Type"
        verbose_name_plural = "Service Types"
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


class BookingService(AuditModel):
    booking = models.ForeignKey(
        Booking, 
        on_delete=models.CASCADE, 
        related_name='services',
        limit_choices_to={'locked_at__isnull': True}
    )
    display_order = models.PositiveIntegerField(default=1)
    service_type = models.ForeignKey(ServiceType, on_delete=models.PROTECT)
    service_provider = models.CharField(max_length=100, blank=True)
    journey_start = models.DateTimeField(null=True, blank=True)
    journey_end = models.DateTimeField(null=True, blank=True)
    from_location = models.CharField(max_length=100, blank=True)
    to_location = models.CharField(max_length=100, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='booking_services')
    reference_number = models.CharField(max_length=50, blank=True, db_index=True)
    currency = models.CharField(max_length=3, default='INR', editable=False)
    remarks = models.TextField(blank=True)

    class Meta:
        verbose_name = "Booking Service"
        verbose_name_plural = "Booking Services"
        ordering = ['display_order']

    def __str__(self):
        return f"{self.service_type.name} for {self.booking.booking_number}"

    @property
    def total_supplier_cost(self):
        return sum(t.supplier_cost for t in self.booking_travelers.exclude(passenger_status='CANCELLED'))

    @property
    def total_service_charge(self):
        return sum(t.service_charge for t in self.booking_travelers.exclude(passenger_status='CANCELLED'))

    @property
    def profit(self):
        return self.total_service_charge - self.total_supplier_cost


class BookingTraveler(AuditModel):
    booking_service = models.ForeignKey(BookingService, on_delete=models.CASCADE, related_name='booking_travelers')
    traveler = models.ForeignKey(Traveler, on_delete=models.PROTECT, related_name='booking_travelers')
    passenger_status = models.CharField(max_length=50, choices=PassengerStatus.choices, default=PassengerStatus.CONFIRMED)
    ticket_number = models.CharField(max_length=50, blank=True)
    seat_details = models.CharField(max_length=20, blank=True)
    check_in_status = models.CharField(max_length=50, blank=True)
    
    supplier_cost = models.DecimalField(max_digits=12, decimal_places=2, default=ZERO_AMOUNT)
    service_charge = models.DecimalField(max_digits=12, decimal_places=2, default=ZERO_AMOUNT)
    is_gst_applicable = models.BooleanField(default=True)
    
    baggage = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Booking Traveler"
        verbose_name_plural = "Booking Travelers"
        constraints = [
            models.UniqueConstraint(
                fields=["booking_service", "traveler"],
                name="unique_booking_service_traveler"
            ),
            models.CheckConstraint(
                condition=models.Q(supplier_cost__gte=ZERO_AMOUNT),
                name='booking_traveler_supplier_cost_gte_0'
            ),
            models.CheckConstraint(
                condition=models.Q(service_charge__gte=ZERO_AMOUNT),
                name='booking_traveler_service_charge_gte_0'
            )
        ]

    def __str__(self):
        return f"{self.traveler.full_name} - {self.booking_service}"

class BookingHistory(AuditModel):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='history')
    action = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Booking History"
        verbose_name_plural = "Booking Histories"
        indexes = [
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.booking.booking_number} - {self.action}"
