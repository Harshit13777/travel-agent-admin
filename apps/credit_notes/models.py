from decimal import Decimal
from django.db import models
from apps.common.models import AuditModel
from apps.bookings.models import Booking, BookingService, BookingTraveler
from apps.invoices.models import Invoice, InvoiceLine
from apps.credit_notes.choices import CreditNoteStatus

class CreditNote(AuditModel):
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name='credit_notes')
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='credit_notes', null=True, blank=True)
    
    credit_note_number = models.CharField(max_length=50, unique=True, db_index=True)
    issued_date = models.DateField()
    
    supplier_refund_expected = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    supplier_refund_received = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    supplier_refund_date = models.DateField(null=True, blank=True)
    
    taxable_refund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    cgst_refund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    sgst_refund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    igst_refund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    
    total_credit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    remaining_credit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    
    reason = models.TextField(blank=True)
    remarks = models.TextField(blank=True)
    status = models.CharField(max_length=50, choices=CreditNoteStatus.choices, default=CreditNoteStatus.ACTIVE, db_index=True)
    
    from django.conf import settings
    cancelled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='cancelled_credit_notes')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    voided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='voided_credit_notes')
    voided_at = models.DateTimeField(null=True, blank=True)
    void_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = "Credit Note"
        verbose_name_plural = "Credit Notes"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total_credit__gte=Decimal('0.00')),
                name='credit_note_total_gte_0'
            ),
            models.CheckConstraint(
                condition=models.Q(remaining_credit__gte=Decimal('0.00')),
                name='credit_note_remaining_gte_0'
            )
        ]

    def __str__(self):
        return f"{self.credit_note_number} - {self.booking.customer.name}"


class CreditNoteLine(AuditModel):
    """
    Detailed lines of what was refunded, optionally linked to specific services.
    """
    credit_note = models.ForeignKey(CreditNote, on_delete=models.PROTECT, related_name='lines')
    
    # Optional links
    invoice_line = models.ForeignKey(InvoiceLine, on_delete=models.SET_NULL, null=True, blank=True, related_name='credit_note_lines')
    booking_traveler = models.ForeignKey(BookingTraveler, on_delete=models.SET_NULL, null=True, blank=True, related_name='credit_note_lines')
    
    description = models.CharField(max_length=255)
    
    supplier_refund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    service_charge_refund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    
    taxable_refund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    cgst_refund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    sgst_refund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    igst_refund = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    
    class Meta:
        verbose_name = "Credit Note Line"
        verbose_name_plural = "Credit Note Lines"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total__gte=Decimal('0.00')),
                name='credit_note_line_total_gte_0'
            )
        ]


class CreditAllocation(AuditModel):
    """
    Tracks how a Credit Note was applied to an Invoice.
    """
    credit_note = models.ForeignKey(CreditNote, on_delete=models.PROTECT, related_name='allocations')
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='credit_allocations')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    class Meta:
        verbose_name = "Credit Allocation"
        verbose_name_plural = "Credit Allocations"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=Decimal('0.00')),
                name='credit_allocation_amount_gt_0'
            )
        ]
