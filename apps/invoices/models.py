from decimal import Decimal
from django.db import models
from apps.common.models import AuditModel
from apps.bookings.models import Booking
from apps.invoices.choices import InvoiceStatus

class Invoice(AuditModel):
    booking = models.OneToOneField(Booking, on_delete=models.PROTECT, related_name='invoice')
    invoice_number = models.CharField(max_length=50, unique=True, db_index=True)
    invoice_date = models.DateField()
    due_date = models.DateField()
    currency = models.CharField(max_length=3, default='INR', editable=False)
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"), help_text="Percentage GST rate (e.g., 5.00)")
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    
    status = models.CharField(max_length=50, choices=InvoiceStatus.choices, default=InvoiceStatus.PENDING)
    remarks = models.TextField(blank=True)

    class Meta:
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"

    def __str__(self):
        return f"{self.invoice_number} - {self.booking.customer.name}"
        
    @property
    def paid_amount(self):
        return sum(payment.amount for payment in self.payments.all())
        
    @property
    def balance_amount(self):
        return self.grand_total - self.paid_amount
        
    @property
    def is_paid(self):
        return self.status == InvoiceStatus.PAID
