from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from apps.common.models import AuditModel
from apps.common.choices import CustomerType

class Customer(AuditModel):
    name = models.CharField(max_length=255, db_index=True)
    customer_type = models.CharField(max_length=50, choices=CustomerType.choices, default=CustomerType.INDIVIDUAL)
    contact_person = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=15, blank=True, db_index=True)
    email = models.EmailField(blank=True, db_index=True)
    gst_number = models.CharField(max_length=15, blank=True, db_index=True)
    pan = models.CharField(max_length=10, blank=True)
    billing_address = models.TextField(blank=True)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True)
    assigned_agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_customers')
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def __str__(self):
        return f"{self.name} ({self.get_customer_type_display()})"

    @property
    def outstanding_amount(self):
        # Calculated read-only property (will implement logic once financial models are ready)
        return Decimal("0.00")


class Supplier(AuditModel):
    name = models.CharField(max_length=255, db_index=True)
    phone = models.CharField(max_length=15, blank=True, db_index=True)
    email = models.EmailField(blank=True, db_index=True)
    gst_number = models.CharField(max_length=15, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)
    remarks = models.TextField(blank=True)

    class Meta:
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"

    def __str__(self):
        return self.name
