class NotificationRuleResolver:
    """
    Layer 1: Notification Rules
    Responsible for answering 'Should this notification even exist?'
    """

    @classmethod
    def resolve(cls, event, recipient_type, recipient_id):
        pass


class RecipientResolver:
    """
    Layer 2: Recipient Resolver
    Responsible for answering 'Who receives it?'
    """

    @classmethod
    def resolve(cls, base_recipient):
        pass
