class RetryService:
    """
    Only retry logic.
    """

    @classmethod
    def schedule_retry(cls, notification_id):
        pass

    @classmethod
    def calculate_backoff(cls, current_retry_count):
        pass

    @classmethod
    def mark_dead(cls, notification_id):
        pass
