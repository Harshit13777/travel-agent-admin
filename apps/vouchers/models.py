from decimal import Decimal
from django.db import models
from apps.common.models import AuditModel
from apps.customers.models import Customer
from apps.credit_notes.models import CreditNote
from apps.common.choices import VoucherStatus

class Voucher(AuditModel):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='vouchers')
    credit_note = models.OneToOneField(CreditNote, on_delete=models.PROTECT, null=True, blank=True, related_name='voucher')
    voucher_number = models.CharField(max_length=50, unique=True, db_index=True)
    original_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    remaining_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    issued_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    used_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=VoucherStatus.choices, default=VoucherStatus.ACTIVE)
    reason = models.TextField(blank=True)

    class Meta:
        verbose_name = "Voucher"
        verbose_name_plural = "Vouchers"

    def __str__(self):
        return f"{self.voucher_number} - {self.customer.name}"
