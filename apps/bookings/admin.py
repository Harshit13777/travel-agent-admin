from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import Booking, ServiceType, BookingService, BookingTraveler, BookingHistory

class BookingServiceInline(TabularInline):
    model = BookingService
    extra = 1
    autocomplete_fields = ['service_type', 'supplier']

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.is_locked:
            return ['service_type', 'supplier_cost', 'selling_price', 'discount', 'currency']
        return []
        
    def has_add_permission(self, request, obj=None):
        if obj and obj.is_locked:
            return False
        return super().has_add_permission(request, obj)
        
    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_locked:
            return False
        return super().has_delete_permission(request, obj)

class BookingTravelerInline(TabularInline):
    model = BookingTraveler
    extra = 1
    autocomplete_fields = ['traveler']

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.booking.is_locked:
            return ['traveler', 'fare']
        return []
        
    def has_add_permission(self, request, obj=None):
        if obj and obj.booking.is_locked:
            return False
        return super().has_add_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.booking.is_locked:
            return False
        return super().has_delete_permission(request, obj)

from apps.bookings.services import confirm_booking
from apps.invoices.services import generate_invoice

@admin.action(description="Confirm selected bookings")
def action_confirm_booking(modeladmin, request, queryset):
    for booking in queryset:
        try:
            confirm_booking(booking, user=request.user)
            modeladmin.message_user(request, f"Booking {booking.booking_number} confirmed.")
        except Exception as e:
            from django.contrib import messages
            modeladmin.message_user(request, f"Error confirming {booking.booking_number}: {str(e)}", level=messages.ERROR)

@admin.action(description="Generate Invoice for selected bookings")
def action_generate_invoice(modeladmin, request, queryset):
    for booking in queryset:
        try:
            invoice = generate_invoice(booking, user=request.user)
            modeladmin.message_user(request, f"Invoice {invoice.invoice_number} generated for {booking.booking_number}.")
        except Exception as e:
            from django.contrib import messages
            modeladmin.message_user(request, f"Error generating invoice for {booking.booking_number}: {str(e)}", level=messages.ERROR)

@admin.register(Booking)
class BookingAdmin(ModelAdmin):
    list_display = ['booking_number', 'title', 'customer', 'status', 'priority']
    search_fields = ['booking_number', 'title', 'customer__name']
    list_filter = ['status', 'priority', 'booking_source']
    autocomplete_fields = ['customer', 'assigned_to']
    list_select_related = ['customer', 'assigned_to']
    inlines = [BookingServiceInline]
    actions = [action_confirm_booking, action_generate_invoice]

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return []
            
        readonly = ['booking_number', 'locked_at']
        if obj.is_locked:
            readonly.extend(['customer', 'booking_source'])
        return readonly

    def get_exclude(self, request, obj=None):
        if obj is None:
            return ['booking_number', 'locked_at']
        return []

    def save_model(self, request, obj, form, change):
        if not change:
            from apps.bookings.services import create_booking
            create_booking(booking=obj, user=request.user)
        else:
            super().save_model(request, obj, form, change)

@admin.register(ServiceType)
class ServiceTypeAdmin(ModelAdmin):
    list_display = ['name', 'display_order', 'is_active']
    list_editable = ['display_order', 'is_active']
    search_fields = ['name']

@admin.register(BookingService)
class BookingServiceAdmin(ModelAdmin):
    list_display = ['booking', 'service_type', 'status', 'selling_price']
    list_select_related = ['booking', 'service_type', 'supplier']
    autocomplete_fields = ['booking', 'service_type', 'supplier']
    search_fields = ['booking__booking_number', 'reference_number']
    inlines = [BookingTravelerInline]
    list_filter = ['status', 'service_type']

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.booking.is_locked:
            return ['booking', 'service_type', 'supplier_cost', 'selling_price', 'discount', 'currency', 'supplier']
        return []

@admin.register(BookingHistory)
class BookingHistoryAdmin(ModelAdmin):
    list_display = ['booking', 'action', 'user', 'created_at']
    list_select_related = ['booking', 'user']
    search_fields = ['booking__booking_number', 'action']
