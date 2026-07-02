from django.contrib import admin
from unfold.admin import ModelAdmin
from django.utils.html import format_html
from django.urls import reverse
from .models import Booking

@admin.register(Booking)
class BookingAdmin(ModelAdmin):
    list_display = ('pnr', 'customer_link', 'journey_date', 'status', 'total_amount', 'edit_button')
    list_display_links = ('pnr',)
    search_fields = ('pnr', 'customer__name', 'customer__phone', 'train_no', 'train_name')
    list_filter = ('status', 'journey_date', 'travel_class')
    
    # Using autocomplete_fields for ForeignKeys and ManyToMany fields for dynamic search dropdowns
    autocomplete_fields = ('customer', 'passengers')
    
    # Organize fields nicely
    fieldsets = (
        ('General Information', {
            'fields': ('customer', 'passengers', 'status', 'created_by')
        }),
        ('Journey Details', {
            'fields': ('journey_date', 'train_no', 'train_name', 'travel_class', 'from_station', 'to_station', 'pnr')
        }),
        ('Financials', {
            'fields': ('fare_amount', 'conv_fee', 'commission', 'tax_amount', 'total_amount')
        }),
    )

    def customer_link(self, obj):
        if obj.customer:
            url = reverse("admin:crm_customer_change", args=[obj.customer.id])
            return format_html('<a class="font-medium text-primary-600 hover:text-primary-500" href="{}">{}</a>', url, obj.customer.name)
        return "-"
    customer_link.short_description = 'Customer'

    def edit_button(self, obj):
        url = reverse("admin:bookings_booking_change", args=[obj.id])
        return format_html('<a class="font-medium text-primary-600 hover:text-primary-500" href="{}">Edit</a>', url)
    edit_button.short_description = 'Action'
