from decimal import Decimal
from django.db import models
from apps.common.models import AuditModel
from apps.bookings.models import Booking, BookingService
from apps.invoices.choices import InvoiceStatus

class Invoice(AuditModel):
    booking = models.OneToOneField(Booking, on_delete=models.PROTECT, related_name='invoice')
    invoice_number = models.CharField(max_length=50, unique=True, db_index=True)
    invoice_date = models.DateField(db_index=True)
    due_date = models.DateField()
    # Company Identity & Settings Config Snapshot
    company_name = models.CharField(max_length=255, default="Travel Agency")
    gstin = models.CharField(max_length=50, blank=True)
    pan = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    
    currency = models.CharField(max_length=10, default='INR', editable=False)
    gst_enabled = models.BooleanField(default=True)
    gst_type = models.CharField(max_length=50, default='CGST_SGST')
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('18.00'))
    tax_label_1 = models.CharField(max_length=50, default="CGST")
    tax_label_2 = models.CharField(max_length=50, default="SGST")
    tax_label_3 = models.CharField(max_length=50, default="IGST")
    
    # Financial Snapshots
    supplier_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    service_charge_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    subtotal_before_tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    taxable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    cgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    sgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    igst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    original_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    credit_applied = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    final_payable = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    
    status = models.CharField(max_length=50, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT, db_index=True)
    remarks = models.TextField(blank=True)

    class Meta:
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(grand_total__gte=Decimal('0.00')),
                name='invoice_grand_total_gte_0'
            )
        ]

    def __str__(self):
        return f"{self.invoice_number} - {self.booking.customer.name}"
        
    @property
    def paid_amount(self):
        return sum(payment.amount for payment in self.payments.all())
        
    @property
    def balance_amount(self):
        return self.final_payable - self.paid_amount
        
    @property
    def is_paid(self):
        return self.status == InvoiceStatus.PAID


class InvoiceLine(AuditModel):
    """
    Immutable legal snapshot of a service at the time of invoicing.
    Never reads from BookingService again.
    """
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='lines')
    booking_service = models.ForeignKey(BookingService, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoice_lines')
    service_type = models.CharField(max_length=100)
    service_provider = models.CharField(max_length=100, blank=True)
    traveler_count = models.PositiveIntegerField(default=1)
    
    supplier_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    service_charge = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    is_taxable = models.BooleanField(default=True)
    taxable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    
    # Line level tax calculations
    cgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    sgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    igst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    
    class Meta:
        verbose_name = "Invoice Line"
        verbose_name_plural = "Invoice Lines"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total__gte=Decimal('0.00')),
                name='invoice_line_total_gte_0'
            )
        ]

    def __str__(self):
        return f"{self.service_type} for {self.invoice.invoice_number}"
