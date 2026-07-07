from decimal import Decimal
from django.db import models
from django.conf import settings
from apps.common.models import AuditModel
from apps.invoices.models import InvoiceLineTraveler
from apps.cancellations.choices import CancellationSource

class BookingCancellation(AuditModel):
    invoice_line_traveler = models.OneToOneField(InvoiceLineTraveler, on_delete=models.PROTECT, related_name='cancellation')
    
    # Granular Financial Components
    supplier_refund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    service_refund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    cgst_refund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    sgst_refund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    igst_refund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    
    reason = models.TextField(blank=True)
    
    # Audit trail
    remarks = models.TextField(blank=True)
    source = models.CharField(max_length=50, choices=CancellationSource.choices, default=CancellationSource.ADMIN)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_cancellations')

    class Meta:
        verbose_name = "Booking Cancellation"
        verbose_name_plural = "Booking Cancellations"
        constraints = [

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
        # Additional model-level validation can be added here
        pass

    def __str__(self):
        return f"Cancellation for Traveler {self.invoice_line_traveler.id}"
