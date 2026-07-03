from decimal import Decimal
from django.db import models
from apps.common.models import AuditModel
from apps.bookings.models import Booking
from apps.common.choices import INVOICE_TYPE_CHOICES, INVOICE_STATUS_CHOICES

class Invoice(AuditModel):
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name='invoices')
    invoice_number = models.CharField(max_length=50, unique=True, db_index=True)
    invoice_type = models.CharField(max_length=50, choices=INVOICE_TYPE_CHOICES, default='TAX')
    invoice_date = models.DateField()
    due_date = models.DateField()
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    
    status = models.CharField(max_length=50, choices=INVOICE_STATUS_CHOICES, default='DRAFT')
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"

    def __str__(self):
        return f"{self.invoice_number} ({self.get_invoice_type_display()}) - {self.booking.customer.name}"
