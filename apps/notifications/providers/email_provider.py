from .base import BaseProvider

class EmailProvider(BaseProvider):
    def send(self, notification):
        pass

    def health_check(self):
        pass
