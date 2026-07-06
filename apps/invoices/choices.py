from django.db import models

class InvoiceStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    ISSUED = 'ISSUED', 'Issued'
    PAID = 'PAID', 'Paid'
    VOID = 'VOID', 'Void'

class InvoiceCancellationStatus(models.TextChoices):
    NONE = 'NONE', 'None'
    PARTIAL = 'PARTIAL', 'Partial'
    FULL = 'FULL', 'Full'

class TravelerType(models.TextChoices):
    ADULT = 'ADULT', 'Adult'
    CHILD = 'CHILD', 'Child'
    INFANT = 'INFANT', 'Infant'
