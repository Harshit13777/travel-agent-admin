import uuid
from django.db import models
from .notification import Notification
from .enums import NotificationStatus


class NotificationLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='logs')
    
    attempt_no = models.PositiveIntegerField(default=1)
    provider = models.CharField(max_length=100)
    
    status = models.CharField(max_length=50, choices=NotificationStatus.choices)
    
    request_payload = models.JSONField(null=True, blank=True)
    response_payload = models.JSONField(null=True, blank=True)
    
    response_code = models.CharField(max_length=50, null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Log for Notification {self.notification_id} (Attempt {self.attempt_no})"
