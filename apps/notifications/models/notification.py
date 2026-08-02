import uuid
from django.db import models
from apps.common.models import TimestampedModel
from .enums import NotificationChannel, NotificationStatus, NotificationPriority
from .notification_template import NotificationTemplate


class Notification(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    channel = models.CharField(max_length=50, choices=NotificationChannel.choices)
    status = models.CharField(
        max_length=50, 
        choices=NotificationStatus.choices, 
        default=NotificationStatus.PENDING,
        db_index=True
    )
    priority = models.CharField(
        max_length=50, 
        choices=NotificationPriority.choices, 
        default=NotificationPriority.NORMAL,
        db_index=True
    )

    # Note: recipient_type and recipient_id can be done with GenericForeignKey if strictly needed,
    # or by keeping the design from the final iteration: just recipient_address + optional FKs.
    # The architecture spec said:
    # recipient_type
    # recipient_id
    # recipient_address
    recipient_type = models.CharField(max_length=50, help_text="e.g. AGENT, CUSTOMER")
    recipient_id = models.PositiveIntegerField(null=True, blank=True)
    recipient_address = models.CharField(max_length=255, help_text="Email, phone number, etc.")

    subject = models.CharField(max_length=255, blank=True, null=True)
    body = models.TextField()

    template = models.ForeignKey(NotificationTemplate, null=True, blank=True, on_delete=models.SET_NULL)
    payload = models.JSONField(default=dict, blank=True)

    scheduled_at = models.DateTimeField(null=True, blank=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    retry_count = models.PositiveIntegerField(default=0)
    max_retry = models.PositiveIntegerField(default=3)
    
    next_retry_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_retry_at = models.DateTimeField(null=True, blank=True)
    
    processed_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)

    idempotency_key = models.CharField(max_length=255, unique=True)
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Notification {self.id} to {self.recipient_address}"
