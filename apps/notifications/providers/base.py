class BaseProvider:
    """
    Abstract base provider. 
    Every provider only knows how to send.
    """

    def send(self, notification):
        raise NotImplementedError("Subclasses must implement send()")

    def health_check(self):
        raise NotImplementedError("Subclasses must implement health_check()")
