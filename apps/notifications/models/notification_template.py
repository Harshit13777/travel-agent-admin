from django.db import models
from apps.common.models import TimestampedModel


class NotificationTemplate(TimestampedModel):
    code = models.CharField(max_length=100, db_index=True)
    channel = models.CharField(max_length=50, choices=models.TextChoices('Channel', 'EMAIL WHATSAPP SMS IN_APP').choices) # Can use enum here later, but typically string is fine or import from enums
    language = models.CharField(max_length=10, default="en")
    
    subject_template = models.CharField(max_length=255, blank=True, null=True)
    body_template = models.TextField()
    
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('code', 'channel', 'language')

    def __str__(self):
        return f"{self.code} ({self.channel} - {self.language})"
