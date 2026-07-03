from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import Booking, ServiceType, BookingService, BookingTraveler, BookingHistory

class BookingServiceInline(TabularInline):
    model = BookingService
    extra = 1

class BookingTravelerInline(TabularInline):
    model = BookingTraveler
    extra = 1

@admin.register(Booking)
class BookingAdmin(ModelAdmin):
    list_display = ['booking_number', 'customer', 'status', 'priority']
    search_fields = ['booking_number', 'customer__name']
    list_filter = ['status', 'priority', 'booking_source']
    inlines = [BookingServiceInline]

@admin.register(ServiceType)
class ServiceTypeAdmin(ModelAdmin):
    list_display = ['name']

@admin.register(BookingService)
class BookingServiceAdmin(ModelAdmin):
    list_display = ['booking', 'service_type', 'status', 'selling_price']
    inlines = [BookingTravelerInline]
    list_filter = ['status', 'service_type']

@admin.register(BookingHistory)
class BookingHistoryAdmin(ModelAdmin):
    list_display = ['booking', 'action', 'user', 'created_at']
