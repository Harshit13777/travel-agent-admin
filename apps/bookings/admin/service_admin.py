from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.bookings.models import ServiceType, BookingService
from apps.bookings.admin.inlines import BookingTravelerInline

@admin.register(ServiceType)
class ServiceTypeAdmin(ModelAdmin):
    list_display = ['name', 'display_order', 'is_active']
    list_editable = ['display_order', 'is_active']
    search_fields = ['name']

@admin.register(BookingService)
class BookingServiceAdmin(ModelAdmin):
    list_display = ['booking', 'service_type', 'total_service_charge']
    list_select_related = ['booking', 'service_type', 'supplier']
    autocomplete_fields = ['booking', 'service_type', 'supplier']
    search_fields = ['booking__booking_number', 'reference_number']
    inlines = [BookingTravelerInline]
    list_filter = ['service_type']
    exclude = ['display_order', 'is_deleted', 'deleted_at']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('booking_travelers')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # If navigating from the Booking page (which passes from_booking=1), hide the booking dropdown
        # so the user can't accidentally change the parent booking.
        if 'from_booking' in request.GET:
            if 'booking' in form.base_fields:
                from django import forms
                form.base_fields['booking'].widget = forms.HiddenInput()
        return form

    def get_readonly_fields(self, request, obj=None):
        readonly = ['total_supplier_cost', 'total_service_charge', 'currency']
        if obj and obj.booking.is_locked:
            readonly.extend(['service_type', 'supplier'])
        return readonly

    def has_delete_permission(self, request, obj=None):
        if obj and obj.booking.is_locked:
            return False
        return super().has_delete_permission(request, obj)
        
    def delete_model(self, request, obj):
        from apps.bookings.services import delete_booking_service
        delete_booking_service(obj, user=request.user)

    def delete_queryset(self, request, queryset):
        from apps.bookings.services import delete_booking_service
        for obj in queryset:
            delete_booking_service(obj, user=request.user)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "booking":
            from apps.bookings.models import Booking
            kwargs["queryset"] = Booking.objects.filter(locked_at__isnull=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        from apps.bookings.models import BookingTraveler
        from apps.bookings.services import update_booking_traveler, delete_booking_traveler
        for obj in formset.deleted_objects:
            delete_booking_traveler(obj, user=request.user)
        for instance in instances:
            if isinstance(instance, BookingTraveler):
                update_booking_traveler(instance, user=request.user)
            else:
                instance.save()
        formset.save_m2m()

    def response_add(self, request, obj, post_url_continue=None):
        res = super().response_add(request, obj, post_url_continue)
        if "_continue" in request.POST and "from_booking" in request.GET:
            if "?" in res['Location']:
                res['Location'] += '&from_booking=1'
            else:
                res['Location'] += '?from_booking=1'
        elif "_addanother" not in request.POST and "_continue" not in request.POST and "_popup" not in request.POST:
            from django.urls import reverse
            res['Location'] = reverse('admin:bookings_booking_change', args=[obj.booking.id])
        return res

    def response_change(self, request, obj):
        res = super().response_change(request, obj)
        if "_continue" in request.POST and "from_booking" in request.GET:
            if "?" in res['Location']:
                res['Location'] += '&from_booking=1'
            else:
                res['Location'] += '?from_booking=1'
        elif "_addanother" not in request.POST and "_continue" not in request.POST and "_popup" not in request.POST:
            from django.urls import reverse
            res['Location'] = reverse('admin:bookings_booking_change', args=[obj.booking.id])
        return res

    def response_delete(self, request, obj_display, obj_id):
        res = super().response_delete(request, obj_display, obj_id)
        # Because the service is soft-deleted, we can still fetch it to find its parent booking
        from apps.bookings.models import BookingService
        service = BookingService.all_objects.filter(pk=obj_id).first()
        if service:
            from django.urls import reverse
            res['Location'] = reverse('admin:bookings_booking_change', args=[service.booking_id])
        return res
