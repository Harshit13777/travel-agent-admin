from decimal import Decimal
from django.db import models
from django.db.models import Sum
from django.conf import settings
from apps.common.models import AuditModel
from apps.bookings.models import Booking
from apps.invoices.models import Invoice, InvoiceLine, InvoiceLineTraveler
from apps.cancellations.choices import CancellationType, CancellationStatus, SettlementStatus

class BookingCancellation(AuditModel):
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name='cancellations', blank=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='cancellations')
    invoice_line = models.ForeignKey(InvoiceLine, on_delete=models.PROTECT, related_name='cancellations', null=True, blank=True)
    invoice_line_traveler = models.ForeignKey(InvoiceLineTraveler, on_delete=models.PROTECT, related_name='cancellations', null=True, blank=True)
    
    type = models.CharField(max_length=50, choices=CancellationType.choices)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=50, choices=CancellationStatus.choices, default=CancellationStatus.REQUESTED)
    
    refund_gst = models.BooleanField(default=True)
    
    # Base Refunds
    service_refund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    cgst_refund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    sgst_refund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    igst_refund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    
    # Snapshotted Properties (permanently frozen at finalization)
    supplier_refund = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Stored permanently upon finalization")
    total_refund = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Stored permanently upon finalization")
    finalized_invoice_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Stored permanently upon finalization")
    
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='requested_cancellations')
    requested_at = models.DateTimeField(null=True, blank=True)
    finalized_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='finalized_cancellations')
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Booking Cancellation"
        verbose_name_plural = "Booking Cancellations"

    def clean(self):
        from django.core.exceptions import ValidationError
        
        if hasattr(self, 'invoice') and self.invoice:
            self.booking = self.invoice.booking
            
        if self.type == CancellationType.PASSENGER and not self.invoice_line_traveler:
            raise ValidationError("Passenger cancellations must reference an invoice line traveler.")
        if self.type == CancellationType.SERVICE and not self.invoice_line:
            raise ValidationError("Service cancellations must reference an invoice line.")
        if not self.refund_gst:
            if self.cgst_refund != 0 or self.sgst_refund != 0 or self.igst_refund != 0:
                raise ValidationError("Tax refunds must be 0 if refund_gst is False.")

    def __str__(self):
        return f"Cancellation for {self.invoice.invoice_number}"

class CancellationSettlement(AuditModel):
    booking_cancellation = models.ForeignKey(BookingCancellation, on_delete=models.CASCADE, related_name='settlements')
    settlement_number = models.CharField(max_length=50, unique=True, db_index=True, blank=True)
    supplier = models.CharField(max_length=255, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.settlement_number:
            from django.utils import timezone
            import random
            timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
            self.settlement_number = f"SET-{timestamp}-{random.randint(100, 999)}"
        super().save(*args, **kwargs)
    
    currency = models.CharField(max_length=10, default='INR')
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal("1.0000"))
    
    settled_supplier_refund = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal("0.00"),
        verbose_name="Supplier Refund (To Customer)",
        help_text="This is the supplier refund amount that will be ADDED to the customer's total refund when finalized."
    )
    received_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    received_currency = models.CharField(max_length=10, default='INR')
    
    supplier_reference = models.CharField(max_length=255, blank=True)
    bank_reference = models.CharField(max_length=255, blank=True)
    attachment = models.FileField(upload_to='settlements/', null=True, blank=True)
    remarks = models.TextField(blank=True)
    
    status = models.CharField(max_length=50, choices=SettlementStatus.choices, default=SettlementStatus.PENDING)
    
    amount_received_date = models.DateField(null=True, blank=True)
    approved_date = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_settlements')

    class Meta:
        verbose_name = "Cancellation Settlement"
        verbose_name_plural = "Cancellation Settlements"

    def clean(self):
        pass

    def __str__(self):
        return f"Settlement {self.settlement_number} for {self.booking_cancellation}"
