from django.db import models

class CreditNoteStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    PARTIALLY_APPLIED = 'PARTIALLY_APPLIED', 'Partially Applied'
    FULLY_APPLIED = 'FULLY_APPLIED', 'Fully Applied'
    VOID = 'VOID', 'Void'

class CreditNoteSource(models.TextChoices):
    CANCELLATION = 'CANCELLATION', 'Cancellation'
    MANUAL = 'MANUAL', 'Manual'
    PRICE_ADJUSTMENT = 'PRICE_ADJUSTMENT', 'Price Adjustment'
    GOODWILL = 'GOODWILL', 'Goodwill'
    OVERPAYMENT = 'OVERPAYMENT', 'Overpayment'
