from django.db import models

class CancellationType(models.TextChoices):
    PASSENGER = 'PASSENGER', 'Passenger'
    SERVICE = 'SERVICE', 'Service'
    OTHER = 'OTHER', 'Other'

class CancellationStatus(models.TextChoices):
    REQUESTED = 'REQUESTED', 'Requested'
    SUPPLIER_PENDING = 'SUPPLIER_PENDING', 'Supplier Pending'
    PARTIALLY_SETTLED = 'PARTIALLY_SETTLED', 'Partially Settled'
    READY_TO_FINALIZE = 'READY_TO_FINALIZE', 'Ready to Finalize'
    FINALIZED = 'FINALIZED', 'Finalized'

class SettlementStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
