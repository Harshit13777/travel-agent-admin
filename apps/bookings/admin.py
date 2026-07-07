from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import Booking, ServiceType, BookingService, BookingTraveler, BookingHistory

class BookingServiceInline(TabularInline):
    model = BookingService
    extra = 1
    autocomplete_fields = ['service_type', 'supplier']
    exclude = ['display_order']

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.is_locked:
            return [f.name for f in self.model._meta.fields] + ['passengers_summary']
        return ['passengers_summary', 'total_supplier_cost', 'total_service_charge', 'currency']

    def passengers_summary(self, obj):
        if not obj.pk:
            return "Save to add passengers"
        from django.utils.html import format_html
        from django.urls import reverse
        travelers = obj.booking_travelers.all()
        names = [str(t.traveler.full_name) for t in travelers]
        
        url = reverse('admin:bookings_bookingservice_change', args=[obj.id])
        link = format_html('<a href="{}" style="color: #3b82f6; font-weight: bold;">Edit Passengers</a>', url)
        
        if not names:
            return format_html('0 Passengers - {}', link)
        
        display_names = ", ".join(names[:2])
        if len(names) > 2:
            display_names += f" (+{len(names)-2})"
            
        return format_html('{} <br/> {}', display_names, link)
    passengers_summary.short_description = "Passengers"
        
    def has_add_permission(self, request, obj=None):
        if obj and obj.is_locked:
            return False
        return super().has_add_permission(request, obj)
        
    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_locked:
            return False
        return super().has_delete_permission(request, obj)

from django import forms

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

    def get_readonly_fields(self, request, obj=None):
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
            return format_html('<span style="color:red;font-weight:bold;">CANCELLED (Refund: {})</span>', cancellation.total_refund)
            
        booking = obj.booking_service.booking
        if booking.is_locked:
            invoice_snapshot = obj.invoice_snapshots.first()
            if invoice_snapshot:
                from django.utils.html import format_html
                from django.urls import reverse
                add_url = reverse('admin:cancellations_bookingcancellation_add') + f'?invoice_line_traveler={invoice_snapshot.id}'
                return format_html('<a href="{}" style="background-color: #ef4444; color: white; padding: 4px 8px; text-decoration: none; border-radius: 4px; font-weight: bold;">Cancel Passenger</a>', add_url)
                
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

from django.contrib.admin import SimpleListFilter

class InvoiceStatusFilter(SimpleListFilter):
    title = 'Invoice Status'
    parameter_name = 'invoice_status'

    def lookups(self, request, model_admin):
        return (
            ('invoiced', 'Invoiced'),
            ('not_invoiced', 'Not Invoiced'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'invoiced':
            return queryset.filter(locked_at__isnull=False)
        if self.value() == 'not_invoiced':
            return queryset.filter(locked_at__isnull=True)
        return queryset



@admin.register(Booking)
class BookingAdmin(ModelAdmin):
    list_display = ['booking_number', 'title', 'customer', 'passenger_list', 'status', 'priority']
    search_fields = ['booking_number', 'title', 'customer__name']
    list_filter = [InvoiceStatusFilter, 'status', 'priority', 'booking_source']
    autocomplete_fields = ['customer', 'assigned_to']
    list_select_related = ['customer', 'assigned_to']
    inlines = [BookingServiceInline]
    actions = [action_confirm_booking, action_generate_invoice]



    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return []
            
        readonly = ['booking_number', 'locked_at', 'invoice_link', 'passenger_list']
        if obj.is_locked:
            readonly.append('customer')
            
        return readonly

    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_locked:
            return False
        return super().has_delete_permission(request, obj)
        
    def delete_model(self, request, obj):
        from apps.bookings.services import delete_booking
        delete_booking(obj, user=request.user)

    def delete_queryset(self, request, queryset):
        from apps.bookings.services import delete_booking
        for obj in queryset:
            delete_booking(obj, user=request.user)

    def invoice_link(self, obj):
        from django.utils.html import format_html
        from django.urls import reverse
        if hasattr(obj, 'invoice'):
            url = reverse('admin:invoices_invoice_change', args=[obj.invoice.id])
            return format_html('<a href="{}" style="color: #3b82f6; font-weight: bold;">View Invoice {}</a>', url, obj.invoice.invoice_number)
        return "No Invoice Generated"
    invoice_link.short_description = "Related Invoice"

    def passenger_list(self, obj):
        from apps.bookings.models import BookingTraveler
        travelers = BookingTraveler.objects.filter(booking_service__booking=obj).values_list('traveler__full_name', flat=True).distinct()
        names = [str(t).strip() for t in travelers if t]
        if not names:
            return "No Passengers"
        if len(names) > 3:
            return ", ".join(names[:3]) + f" (+{len(names)-3} more)"
        return ", ".join(names)
    passenger_list.short_description = "Passengers"

    def get_exclude(self, request, obj=None):
        if obj is None:
            return ['booking_number', 'locked_at']
        return []

    def save_model(self, request, obj, form, change):
        if not change:
            from apps.bookings.services import create_booking
            create_booking(booking=obj, user=request.user)
        else:
            from apps.bookings.services import update_booking
            update_booking(booking=obj, user=request.user)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        from apps.bookings.services import update_booking_service, delete_booking_service
        for obj in formset.deleted_objects:
            delete_booking_service(obj, user=request.user)
        for instance in instances:
            if isinstance(instance, BookingService):
                update_booking_service(instance, user=request.user)
            else:
                instance.save()
        formset.save_m2m()

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
    exclude = ['display_order']

    def get_readonly_fields(self, request, obj=None):
        readonly = ['total_supplier_cost', 'total_service_charge', 'currency']
        if obj and obj.booking.is_locked:
            readonly.extend(['booking', 'service_type', 'supplier'])
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
        from apps.bookings.services import update_booking_traveler, delete_booking_traveler
        for obj in formset.deleted_objects:
            delete_booking_traveler(obj, user=request.user)
        for instance in instances:
            if isinstance(instance, BookingTraveler):
                update_booking_traveler(instance, user=request.user)
            else:
                instance.save()
        formset.save_m2m()

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


@admin.action(description="Cancel Passenger(s)")
def action_cancel_passenger(modeladmin, request, queryset):
    from django.shortcuts import render
    from django.http import HttpResponseRedirect
    from apps.bookings.forms import PassengerCancellationForm
    from apps.bookings.services import cancel_passenger_with_credit
    
    if queryset.count() > 1:
        from django.contrib import messages
        modeladmin.message_user(request, "You can only cancel one passenger at a time for MVP.", level=messages.ERROR)
        return HttpResponseRedirect(request.get_full_path())
        
    if 'apply' in request.POST:
        form = PassengerCancellationForm(request.POST)
        if form.is_valid():
            try:
                for traveler in queryset:
                    cancel_passenger_with_credit(traveler, form.cleaned_data, request.user)
                
                modeladmin.message_user(request, "Successfully cancelled passengers and processed refunds.")
                return HttpResponseRedirect(request.get_full_path())
            except Exception as e:
                from django.contrib import messages
                modeladmin.message_user(request, f"Error cancelling passenger: {str(e)}", level=messages.ERROR)
    else:
        form = PassengerCancellationForm(initial={'_selected_action': request.POST.getlist(admin.helpers.ACTION_CHECKBOX_NAME)})
        
    return render(
        request,
        "admin/bookings/cancel_passenger.html",
        context={
            "items": queryset,
            "form": form,
            "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,
            "action": "action_cancel_passenger"
        }
    )

@admin.register(BookingTraveler)
class BookingTravelerAdmin(ModelAdmin):
    list_display = ['traveler', 'booking_service', 'passenger_status']
    list_select_related = ['traveler', 'booking_service']
    search_fields = ['traveler__first_name', 'traveler__last_name', 'booking_service__reference_number']
    autocomplete_fields = ['traveler', 'booking_service']
    actions = [action_cancel_passenger]

