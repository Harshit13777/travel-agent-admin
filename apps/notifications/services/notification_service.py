class NotificationService:
    """
    Service responsible ONLY for creating notification records.
    No sending logic here.
    """

    @classmethod
    def create(cls, **kwargs):
        pass

    @classmethod
    def cancel(cls, notification_id):
        pass

    @classmethod
    def expire(cls, notification_id):
        pass

    @classmethod
    def schedule(cls, notification_id, scheduled_at):
        pass
