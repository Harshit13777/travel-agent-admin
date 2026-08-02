class ContactVerificationService:
    """
    Layer 3: Contact Verification
    Responsible for answering 'Can we actually send?'
    Does NOT store duplicate verification states. Queries the domain (Customer/User).
    """

    @classmethod
    def is_channel_available(cls, recipient_type, recipient_id, channel):
        pass
