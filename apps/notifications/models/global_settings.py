from django.db import models
from apps.common.models import TimestampedModel
from django.contrib.postgres.fields import ArrayField
from .enums import NotificationPriority, NotificationChannel

class NotificationGlobalSetting(TimestampedModel):
    event = models.CharField(max_length=100, unique=True, help_text="e.g. PAYMENT_RECEIVED")
    enabled = models.BooleanField(default=True)
    
    default_channels = ArrayField(
        models.CharField(max_length=50, choices=NotificationChannel.choices),
        default=list,
        help_text="Channels that are enabled by default for this event"
    )
    
    priority = models.CharField(
        max_length=50, 
        choices=NotificationPriority.choices, 
        default=NotificationPriority.NORMAL
    )

    def __str__(self):
        return f"{self.event} (Enabled: {self.enabled})"
