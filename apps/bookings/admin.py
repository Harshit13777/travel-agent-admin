from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import Booking, ServiceType, BookingService, BookingTraveler, BookingHistory

class BookingServiceInline(TabularInline):
    model = BookingService
    extra = 1

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.has_invoice:
            return ['service_type', 'supplier_cost', 'selling_price', 'discount', 'currency']
        return []

class BookingTravelerInline(TabularInline):
    model = BookingTraveler
    extra = 1

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.booking.has_invoice:
            return ['traveler', 'passenger_status']
        return []

from apps.bookings.services import confirm_booking, generate_invoice

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
    inlines = [BookingServiceInline]
    actions = [action_confirm_booking, action_generate_invoice]

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.has_invoice:
            return ['customer', 'booking_source']
        return []

@admin.register(ServiceType)
class ServiceTypeAdmin(ModelAdmin):
    list_display = ['name']

@admin.register(BookingService)
class BookingServiceAdmin(ModelAdmin):
    list_display = ['booking', 'service_type', 'status', 'selling_price']
    inlines = [BookingTravelerInline]
    list_filter = ['status', 'service_type']

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.booking.has_invoice:
            return ['booking', 'service_type', 'supplier_cost', 'selling_price', 'discount', 'currency', 'supplier']
        return []

@admin.register(BookingHistory)
class BookingHistoryAdmin(ModelAdmin):
    list_display = ['booking', 'action', 'user', 'created_at']
