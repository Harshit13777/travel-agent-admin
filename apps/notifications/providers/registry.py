class ProviderRegistry:
    """
    Resolves the provider instance for a given channel.
    """
    _providers = {}

    @classmethod
    def register(cls, channel, provider_instance):
        cls._providers[channel] = provider_instance

    @classmethod
    def get(cls, channel):
        from apps.notifications.exceptions import ProviderUnavailable
        provider = cls._providers.get(channel)
        if not provider:
            raise ProviderUnavailable(f"No provider registered for channel {channel}")
        return provider
