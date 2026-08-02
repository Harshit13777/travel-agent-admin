class RetryPolicy:
    """
    Encapsulates retry logic and backoff calculation.
    """

    @classmethod
    def can_retry(cls, current_retry_count, max_retry):
        return current_retry_count < max_retry

    @classmethod
    def next_retry(cls, current_retry_count):
        # Default exponential backoff or similar
        pass
