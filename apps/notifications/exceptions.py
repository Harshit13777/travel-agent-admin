class NotificationException(Exception):
    """Base exception for notification module."""
    pass

class MissingRecipient(NotificationException):
    """Raised when a recipient address cannot be resolved."""
    pass

class ChannelDisabled(NotificationException):
    """Raised when a requested channel is disabled for the recipient."""
    pass

class TemplateMissing(NotificationException):
    """Raised when a required template cannot be found."""
    pass

class ProviderUnavailable(NotificationException):
    """Raised when a provider for a channel is not registered or unavailable."""
    pass

class VerificationFailed(NotificationException):
    """Raised when the contact information is not verified."""
    pass
