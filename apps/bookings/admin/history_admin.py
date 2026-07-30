from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.bookings.models import BookingHistory

@admin.register(BookingHistory)
class BookingHistoryAdmin(ModelAdmin):
    list_display = ['booking', 'action', 'user', 'created_at']
    list_select_related = ['booking', 'user']
    autocomplete_fields = ['booking', 'user']
    search_fields = ['booking__booking_number', 'action']
    
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
        
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]
