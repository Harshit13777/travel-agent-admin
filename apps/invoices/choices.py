from django.db import models

class InvoiceStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    GENERATED = 'GENERATED', 'Generated'
    PARTIALLY_PAID = 'PARTIALLY_PAID', 'Partially Paid'
    PAID = 'PAID', 'Paid'
    CANCELLED = 'CANCELLED', 'Cancelled'
