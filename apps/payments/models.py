from decimal import Decimal
from django.db import models
from django.conf import settings
from apps.common.models import AuditModel
from apps.invoices.models import Invoice
from apps.common.choices import PaymentMethod

class Payment(AuditModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    date = models.DateField(db_index=True)
    method = models.CharField(max_length=50, choices=PaymentMethod.choices, default=PaymentMethod.BANK_TRANSFER)
    reference_number = models.CharField(max_length=100, blank=True, db_index=True)
    remarks = models.TextField(blank=True)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_payments')

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=Decimal('0.00')),
                name='payment_amount_gt_0'
            )
        ]

    def __str__(self):
        return f"{self.amount} for {self.invoice.invoice_number}"


