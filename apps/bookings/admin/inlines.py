from django import forms
from unfold.admin import TabularInline

from apps.bookings.models import BookingService, BookingTraveler

class BookingTravelerForm(forms.ModelForm):
    class Meta:
        model = BookingTraveler
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            from apps.cancellations.models import BookingCancellation
            has_cancellation = BookingCancellation.objects.filter(
                invoice_line_traveler__booking_traveler=self.instance
            ).exists()
            if has_cancellation:
                # Completely lock this row if the passenger is cancelled
                for field_name in self.fields:
                    self.fields[field_name].disabled = True

class BookingTravelerInline(TabularInline):
    model = BookingTraveler
    form = BookingTravelerForm
    extra = 1
    autocomplete_fields = ['traveler']
    exclude = ['is_deleted', 'deleted_at']

    def get_readonly_fields(self, request, obj=None):
        # obj is the parent BookingService
        base = ['cancellation_info']
        if obj and obj.booking.is_locked:
            base.extend(['traveler', 'supplier_cost', 'service_charge', 'is_gst_applicable'])
        return base
        
    def cancellation_info(self, obj):
        if not obj or not obj.pk:
            return "Active"
        from apps.cancellations.models import BookingCancellation
        cancellation = BookingCancellation.objects.filter(
            invoice_line_traveler__booking_traveler=obj
        ).first()
        if cancellation:
            from django.utils.html import format_html
            from django.urls import reverse
            edit_url = reverse('admin:cancellations_bookingcancellation_change', args=[cancellation.id])
            return format_html('<a href="{}" style="color:red;font-weight:bold;text-decoration:underline;">CANCELLED (Refund: {})</a>', edit_url, cancellation.total_refund)
            
        booking = obj.booking_service.booking
        if booking.is_locked:
            invoice_snapshot = obj.invoice_snapshots.first()
            if invoice_snapshot:
                from apps.invoices.choices import InvoiceStatus
                if invoice_snapshot.invoice_line.invoice.status != InvoiceStatus.CLOSED:
                    from django.utils.html import format_html
                    from django.urls import reverse
                    add_url = reverse('admin:cancellations_bookingcancellation_add') + f'?invoice_line_traveler={invoice_snapshot.id}'
                    return format_html('<a href="{}" style="background-color: #ef4444; color: white; padding: 4px 8px; text-decoration: none; border-radius: 4px; font-weight: bold;">Cancel Passenger</a>', add_url)
                else:
                    return "Active (Invoice Closed)"
                
        return "Active"
    cancellation_info.short_description = "Cancellation Status"
        
    def has_add_permission(self, request, obj=None):
        if obj and obj.booking.is_locked:
            return False
        return super().has_add_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.booking.is_locked:
            return False
        return super().has_delete_permission(request, obj)
