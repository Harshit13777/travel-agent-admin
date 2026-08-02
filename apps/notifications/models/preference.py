from django.db import models
from apps.common.models import TimestampedModel
from .enums import NotificationChannel

class NotificationPreference(TimestampedModel):
    recipient_type = models.CharField(max_length=50, help_text="e.g. AGENT, CUSTOMER")
    recipient_id = models.PositiveIntegerField()
    
    notification_type = models.CharField(max_length=100, help_text="e.g. PAYMENT_RECEIVED")
    channel = models.CharField(max_length=50, choices=NotificationChannel.choices)
    
    enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = ('recipient_type', 'recipient_id', 'notification_type', 'channel')

    def __str__(self):
        return f"{self.recipient_type} {self.recipient_id} - {self.notification_type} ({self.channel}): {self.enabled}"
