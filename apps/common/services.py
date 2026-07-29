from apps.common.models import CompanySettings

def get_company_settings():
    """
    Retrieve the singleton CompanySettings instance.
    This acts as the single source of truth for global configuration.
    """
    return CompanySettings.load()

def save_company_settings(settings, user=None, change=False):
    settings.save()
    return settings
