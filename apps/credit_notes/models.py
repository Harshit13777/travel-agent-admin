from decimal import Decimal
from django.db import models
from apps.common.models import AuditModel
from apps.bookings.models import Booking

class CreditNote(AuditModel):
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name='credit_notes')
    credit_note_number = models.CharField(max_length=50, unique=True, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    remaining_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    reason = models.TextField(blank=True)
    issued_date = models.DateField()
    voucher_created = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Credit Note"
        verbose_name_plural = "Credit Notes"

    def __str__(self):
        return f"{self.credit_note_number} - {self.booking.customer.name}"
