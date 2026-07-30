from decimal import Decimal
from django.db import models
from django.db.models import Sum
from apps.common.models import AuditModel
from apps.bookings.models import Booking, BookingService, BookingTraveler
from apps.invoices.choices import InvoiceStatus, InvoiceCancellationStatus, TravelerType

class Invoice(AuditModel):
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name='invoices')
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
    cgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('9.00'))
    sgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('9.00'))
    igst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('18.00'))
    tax_label_1 = models.CharField(max_length=50, default="CGST")
    tax_label_2 = models.CharField(max_length=50, default="SGST")
    tax_label_3 = models.CharField(max_length=50, default="IGST")
    
    # Financial Snapshots (immutable after generation)
    supplier_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    service_charge_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    subtotal_before_tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    taxable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    cgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    sgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    igst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    original_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    final_payable = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    
    status = models.CharField(max_length=50, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT, db_index=True)
    cancellation_status = models.CharField(max_length=50, choices=InvoiceCancellationStatus.choices, default=InvoiceCancellationStatus.NONE, db_index=True)
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
        return f"{self.invoice_number} - {self.booking.customer.name} (Balance Due: {self.currency} {self.balance_due})"
        
    @property
    def current_invoice_value(self):
        from apps.cancellations.models import BookingCancellation
        from django.db.models import Sum
        
        refunds = BookingCancellation.objects.filter(
            invoice_line_traveler__invoice_line__invoice=self
        ).aggregate(
            t_sup=Sum('supplier_refund'),
            t_ser=Sum('service_refund'),
            t_c=Sum('cgst_refund'),
            t_s=Sum('sgst_refund'),
            t_i=Sum('igst_refund')
        )
        
        total_refund = (
            (refunds['t_sup'] or Decimal("0.00")) +
            (refunds['t_ser'] or Decimal("0.00")) +
            (refunds['t_c'] or Decimal("0.00")) +
            (refunds['t_s'] or Decimal("0.00")) +
            (refunds['t_i'] or Decimal("0.00"))
        )
        return self.final_payable - total_refund

    @property
    def balance_due(self):
        from apps.credit_notes.choices import CreditNoteStatus
        payments_sum = sum(p.amount for p in self.payments.all())
        allocations_sum = sum(a.amount for a in self.credit_allocations.all())
        
        generated_credit_notes_sum = Decimal('0.00')
        if hasattr(self, 'issued_credit_note') and self.issued_credit_note:
            if self.issued_credit_note.status != CreditNoteStatus.VOID:
                generated_credit_notes_sum = self.issued_credit_note.amount
                
        return self.current_invoice_value - payments_sum - allocations_sum + generated_credit_notes_sum

    @property
    def payment_status(self):
        from apps.credit_notes.choices import CreditNoteStatus
        from apps.invoices.choices import InvoicePaymentStatus
        
        if self.balance_due <= Decimal('0.00'):
            return InvoicePaymentStatus.PAID
        payments_sum = sum(p.amount for p in self.payments.all())
        allocations_sum = sum(a.amount for a in self.credit_allocations.all())
        
        generated_credit_notes_sum = Decimal('0.00')
        if hasattr(self, 'issued_credit_note') and self.issued_credit_note:
            if self.issued_credit_note.status != CreditNoteStatus.VOID:
                generated_credit_notes_sum = self.issued_credit_note.amount
        
        if (payments_sum + allocations_sum + generated_credit_notes_sum) > Decimal('0.00'):
            return InvoicePaymentStatus.PARTIAL
        return InvoicePaymentStatus.UNPAID

class InvoiceLine(AuditModel):
    """
    Immutable legal snapshot of a service at the time of invoicing.
    Never reads from BookingService again.
    """
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='lines')
    booking_service = models.ForeignKey(BookingService, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoice_lines')
    service_type = models.CharField(max_length=100)
    service_provider = models.CharField(max_length=100, blank=True)
    
    supplier_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    service_charge = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    taxable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    
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

class InvoiceLineTraveler(AuditModel):
    """
    Every passenger gets their own financial snapshot at the time of invoicing.
    This eliminates proportional calculations during partial cancellations.
    """
    invoice_line = models.ForeignKey(InvoiceLine, on_delete=models.CASCADE, related_name='travelers')
    booking_traveler = models.ForeignKey(BookingTraveler, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoice_snapshots')
    traveler_sequence = models.PositiveIntegerField(default=1)
    traveler_type = models.CharField(max_length=50, choices=TravelerType.choices, default=TravelerType.ADULT)
    traveler_name = models.CharField(max_length=255)
    ticket_number = models.CharField(max_length=100, blank=True)
    
    currency = models.CharField(max_length=10, default='INR')
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal("1.0000"))
    
    supplier_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    service_charge = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    taxable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    
    cgst = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    sgst = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    igst = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        verbose_name = "Invoice Line Traveler"
        verbose_name_plural = "Invoice Line Travelers"
        ordering = ['invoice_line', 'traveler_sequence']

    def __str__(self):
        return f"{self.traveler_name} snapshot on {self.invoice_line}"
