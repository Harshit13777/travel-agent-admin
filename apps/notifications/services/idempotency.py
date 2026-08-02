class IdempotencyService:
    """
    Generates idempotency keys to ensure we never duplicate a notification.
    """

    @classmethod
    def generate_key(cls, event, recipient_id, channel):
        pass
