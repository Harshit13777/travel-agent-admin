from django.db import models

class CancellationStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    VOID = 'VOID', 'Void'

class CancellationSource(models.TextChoices):
    ADMIN = 'ADMIN', 'Admin'
    API = 'API', 'API'
    IMPORT = 'IMPORT', 'Import'
    PORTAL = 'PORTAL', 'Portal'
    SYSTEM = 'SYSTEM', 'System'
