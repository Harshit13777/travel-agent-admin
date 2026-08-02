from django.db import models
from apps.common.models import TimestampedModel

class ResolverLog(TimestampedModel):
    event = models.CharField(max_length=100)
    recipient_type = models.CharField(max_length=50, help_text="AGENT or CUSTOMER")
    recipient_id = models.PositiveIntegerField()
    reason = models.TextField(help_text="e.g. Customer disabled email")

    def __str__(self):
        return f"Skipped {self.event} for {self.recipient_type} {self.recipient_id}: {self.reason}"
