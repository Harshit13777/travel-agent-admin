from django.contrib import admin
from unfold.admin import ModelAdmin
from apps.notifications.models import (
    Notification, NotificationTemplate, NotificationLog,
    ResolverLog, NotificationGlobalSetting, NotificationPreference
)

@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(ModelAdmin):
    list_display = ('code', 'channel', 'language', 'is_active')
    list_filter = ('channel', 'language', 'is_active')
    search_fields = ('code', 'subject_template')


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ('id', 'channel', 'status', 'priority', 'recipient_address', 'scheduled_at')
    list_filter = ('status', 'channel', 'priority', 'created_at')
    search_fields = ('recipient_address', 'idempotency_key')
    
    # Read-only as per specification
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(NotificationLog)
class NotificationLogAdmin(ModelAdmin):
    list_display = ('id', 'notification', 'attempt_no', 'provider', 'status', 'created_at')
    list_filter = ('status', 'provider', 'created_at')
    search_fields = ('notification__recipient_address', 'provider', 'error_message')

    # Read-only as per specification
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ResolverLog)
class ResolverLogAdmin(ModelAdmin):
    list_display = ('id', 'event', 'recipient_type', 'recipient_id', 'created_at')
    list_filter = ('event', 'recipient_type', 'created_at')
    search_fields = ('reason',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(NotificationGlobalSetting)
class NotificationGlobalSettingAdmin(ModelAdmin):
    list_display = ('event', 'enabled', 'priority')
    list_filter = ('enabled', 'priority')
    search_fields = ('event',)


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(ModelAdmin):
    list_display = ('recipient_type', 'recipient_id', 'notification_type', 'channel', 'enabled')
    list_filter = ('recipient_type', 'channel', 'enabled')
    search_fields = ('notification_type',)
