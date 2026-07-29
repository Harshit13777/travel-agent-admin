from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import CompanySettings

@admin.register(CompanySettings)
class CompanySettingsAdmin(ModelAdmin):
    list_display = ['company_name', 'gstin', 'pan', 'gst_enabled', 'gst_type']
    
    def has_add_permission(self, request):
        # Allow adding only if there's no settings object yet (singleton pattern)
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)

    def save_model(self, request, obj, form, change):
        from .services import save_company_settings
        save_company_settings(obj, user=request.user, change=change)
