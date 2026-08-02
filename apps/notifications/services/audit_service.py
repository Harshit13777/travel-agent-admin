class NotificationAuditService:
    """
    Replaces raw NotificationLog.objects.create(). 
    Provides clean methods for logging delivery attempts and skip decisions.
    """

    @classmethod
    def log_created(cls, notification_id):
        pass

    @classmethod
    def log_sent(cls, notification_id, provider, response):
        pass

    @classmethod
    def log_failed(cls, notification_id, provider, error):
        pass

    @classmethod
    def log_skipped(cls, event, recipient, reason):
        pass

    @classmethod
    def log_retry(cls, notification_id, attempt_no):
        pass
