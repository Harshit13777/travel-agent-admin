from django.db import models

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
