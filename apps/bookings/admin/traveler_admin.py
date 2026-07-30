from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.bookings.models import BookingTraveler

@admin.register(BookingTraveler)
class BookingTravelerAdmin(ModelAdmin):
    list_display = ['traveler', 'booking_service', 'passenger_status']
    list_select_related = ['traveler', 'booking_service']
    search_fields = ['traveler__first_name', 'traveler__last_name', 'booking_service__reference_number']
    autocomplete_fields = ['traveler', 'booking_service']
    exclude = ['is_deleted', 'deleted_at']
