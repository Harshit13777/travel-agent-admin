from django.db import models
from decimal import Decimal

class AuditModel(models.Model):
    """
    Abstract base class providing timestamp fields.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]

class NumberSequence(models.Model):
    """
    Sequence table for transaction-safe number generation.
    """
    prefix = models.CharField(max_length=10, unique=True)
    last_value = models.CharField(max_length=20)

    class Meta:
        verbose_name = "Number Sequence"
        verbose_name_plural = "Number Sequences"

class CompanySettings(AuditModel):
    """
    Singleton model for global company settings.
    """
    # Company Profile
    company_name = models.CharField(max_length=255, default="Travel Agency")
    gstin = models.CharField(max_length=50, blank=True)
    pan = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    
    # Financial Configuration
    currency = models.CharField(max_length=10, default="INR")
    gst_enabled = models.BooleanField(default=True)
    gst_type = models.CharField(max_length=50, default='CGST_SGST', choices=[('CGST_SGST', 'CGST + SGST'), ('IGST', 'IGST')])
    cgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('9.00'))
    sgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('9.00'))
    igst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('18.00'))
    # Tax Labels
    tax_label_1 = models.CharField(max_length=50, default="CGST")
    tax_label_2 = models.CharField(max_length=50, default="SGST")
    tax_label_3 = models.CharField(max_length=50, default="IGST")
    
    # Document Prefixes
    invoice_prefix = models.CharField(max_length=10, default="INV")
    credit_note_prefix = models.CharField(max_length=10, default="CN")

    class Meta:
        verbose_name = "Company Settings"
        verbose_name_plural = "Company Settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
