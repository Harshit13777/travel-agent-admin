from decimal import Decimal
from django.db import models
from django.conf import settings
from apps.common.models import AuditModel
from apps.invoices.models import InvoiceLineTraveler
from apps.cancellations.choices import CancellationStatus, CancellationSource

class BookingCancellation(AuditModel):
    # Foreign Keys strictly PROTECTED. Invoice FK is removed to prevent redundancy.
    invoice_line_traveler = models.ForeignKey(InvoiceLineTraveler, on_delete=models.PROTECT, related_name='cancellations')
    
    # Granular Financial Components
    supplier_refund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    service_refund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    cgst_refund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    sgst_refund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    igst_refund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    
    # Soft Delete & State
    status = models.CharField(max_length=50, choices=CancellationStatus.choices, default=CancellationStatus.ACTIVE)
    reason = models.TextField(blank=True)
    
    # Audit trail
    remarks = models.TextField(blank=True)
    source = models.CharField(max_length=50, choices=CancellationSource.choices, default=CancellationSource.ADMIN)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_cancellations')

    class Meta:
        verbose_name = "Booking Cancellation"
        verbose_name_plural = "Booking Cancellations"
        constraints = [
            # 1-to-1 Active Rule
            models.UniqueConstraint(
                fields=["invoice_line_traveler"],
                condition=models.Q(status="ACTIVE"),
                name="unique_active_cancellation"
            ),
            # Absolute Zero Checks
            models.CheckConstraint(condition=models.Q(supplier_refund__gte=0), name="supplier_refund_positive"),
            models.CheckConstraint(condition=models.Q(service_refund__gte=0), name="service_refund_positive"),
            models.CheckConstraint(condition=models.Q(cgst_refund__gte=0), name="cgst_refund_positive"),
            models.CheckConstraint(condition=models.Q(sgst_refund__gte=0), name="sgst_refund_positive"),
            models.CheckConstraint(condition=models.Q(igst_refund__gte=0), name="igst_refund_positive"),
        ]

    @property
    def total_refund(self):
        return self.supplier_refund + self.service_refund + self.cgst_refund + self.sgst_refund + self.igst_refund

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Enforce Immutability on Update
        if self.pk:
            orig = BookingCancellation.objects.get(pk=self.pk)
            # You can only change status
            if (self.supplier_refund != orig.supplier_refund or
                self.service_refund != orig.service_refund or
                self.cgst_refund != orig.cgst_refund or
                self.sgst_refund != orig.sgst_refund or
                self.igst_refund != orig.igst_refund or
                self.invoice_line_traveler_id != orig.invoice_line_traveler_id):
                raise ValidationError("Financial fields and traveler reference on a cancellation are immutable. To correct mistakes, VOID this cancellation and create a new one.")
            
            # Cannot change from VOID to ACTIVE
            if orig.status == CancellationStatus.VOID and self.status == CancellationStatus.ACTIVE:
                # Need to check manually here in case they try to bypass the service
                if BookingCancellation.objects.filter(invoice_line_traveler=self.invoice_line_traveler, status=CancellationStatus.ACTIVE).exclude(pk=self.pk).exists():
                    raise ValidationError("Another ACTIVE cancellation already exists for this traveler.")

    def __str__(self):
        return f"Cancellation for Traveler {self.invoice_line_traveler.id}"
