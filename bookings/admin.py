from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(ModelAdmin):
    list_display = ('pnr', 'customer', 'journey_date', 'status', 'total_amount')
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
