class NotificationRepository:
    """
    Encapsulates all database access for notifications.
    Never contains business logic.
    """

    @classmethod
    def create(cls, **kwargs):
        pass

    @classmethod
    def update_status(cls, notification_id, status):
        pass

    @classmethod
    def mark_sent(cls, notification_id):
        pass

    @classmethod
    def mark_failed(cls, notification_id, error_message):
        pass

    @classmethod
    def find_pending(cls):
        pass
