from decimal import Decimal
from django.db import models
from django.conf import settings
from apps.common.models import AuditModel
from apps.customers.models import Customer
from apps.invoices.models import Invoice
from apps.credit_notes.choices import CreditNoteStatus, CreditNoteSource

class CreditNote(AuditModel):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='credit_notes', null=True, blank=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='issued_credit_notes', help_text="The invoice this credit was generated from, if any.")
    
    number = models.CharField(max_length=50, unique=True, db_index=True, null=True, blank=True)
    source = models.CharField(max_length=50, choices=CreditNoteSource.choices, default=CreditNoteSource.CANCELLATION)
    
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    allocated_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    
    reason = models.TextField(blank=True)
    remarks = models.TextField(blank=True)
    status = models.CharField(max_length=50, choices=CreditNoteStatus.choices, default=CreditNoteStatus.ACTIVE, db_index=True)
    
    from django.utils import timezone
    issued_at = models.DateTimeField(default=timezone.now)
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='issued_credit_notes')
    
    voided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='voided_credit_notes')
    voided_at = models.DateTimeField(null=True, blank=True)
    void_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = "Credit Note"
        verbose_name_plural = "Credit Notes"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gte=Decimal('0.00')),
                name='credit_note_amount_gte_0'
            ),
            models.CheckConstraint(
                condition=models.Q(allocated_amount__gte=Decimal('0.00')),
                name='credit_note_allocated_amount_gte_0'
            )
        ]

    def __str__(self):
        customer_name = self.customer.name if self.customer else "Unknown Customer"
        return f"{self.number} - {customer_name} (Available: {self.remaining_amount})"
        
    @property
    def remaining_amount(self):
        return self.amount - self.allocated_amount

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

    def __str__(self):
        return f"Allocated {self.amount} from {self.credit_note.number} to {self.invoice.invoice_number}"
