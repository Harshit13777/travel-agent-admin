from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.bookings.models import Booking, BookingTimeline
from apps.bookings.admin.inlines import BookingServiceInline
from apps.bookings.admin.filters import InvoiceStatusFilter

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
    list_display = ['booking_number', 'title', 'customer', 'passenger_list', 'status', 'priority']
    search_fields = ['booking_number', 'title', 'customer__name']
    list_filter = [InvoiceStatusFilter, 'status', 'priority', 'booking_source']
    autocomplete_fields = ['customer', 'assigned_to']
    list_select_related = ['customer', 'assigned_to']
    inlines = [BookingServiceInline]
    actions = [action_confirm_booking, action_generate_invoice]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related(
            'services',
            'services__booking_travelers',
            'services__booking_travelers__traveler'
        )

    fieldsets = (
        ('Actions & Financials', {
            'fields': ('invoice_link', 'generate_invoice_button', 'view_history_button'),
            'classes': ('tab',)
        }),
        ('Booking Details', {
            'fields': ('booking_number', 'title', 'customer', 'status', 'passenger_list', 'priority', 'booking_source', 'assigned_to', 'notes', 'locked_at'),
            'classes': ('tab',)
        })
    )

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return (
                ('Booking Details', {
                    'fields': ('title', 'customer', 'status', 'priority', 'booking_source', 'assigned_to', 'notes'),
                    'classes': ('tab',)
                }),
            )
        return super().get_fieldsets(request, obj)

    def get_readonly_fields(self, request, obj=None):
        readonly = ['invoice_link', 'passenger_list', 'generate_invoice_button', 'view_history_button']
        if obj is None:
            return []
            
        readonly.extend(['booking_number', 'locked_at'])
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
        if not obj or not obj.pk:
            return "Save booking first"
        from django.utils.html import format_html
        from django.urls import reverse
        if hasattr(obj, 'invoice'):
            inv = obj.invoice
            url = reverse('admin:invoices_invoice_change', args=[inv.id])
            return format_html(
                '<a href="{}" style="color: #3b82f6; font-weight: bold;">View Invoice {}</a><br><span style="color: #6b7280; font-size: 0.9em;">(Balance Due: {})</span>', 
                url, 
                inv.invoice_number,
                inv.balance_due
            )
        return "No Invoice Generated"
    invoice_link.short_description = "Related Invoice"
    
    def view_history_button(self, obj):
        if not obj or not obj.pk:
            return ""
        from django.utils.html import format_html
        from django.urls import reverse
        url = reverse('admin:bookings_bookingtimeline_change', args=[obj.id])
        return format_html(
            '<a href="{}" style="display: inline-block; background-color: #3b82f6; color: white; padding: 10px 16px; border-radius: 6px; text-decoration: none; font-family: sans-serif; font-size: 14px; font-weight: bold;">🕰️ View Full History</a>', 
            url
        )
    view_history_button.short_description = "Audit Trail"
    
    def generate_invoice_button(self, obj):
        if not obj or not obj.pk:
            return "Save booking first before generating an invoice."
            
        from django.utils.html import format_html
        from django.urls import reverse
        
        if hasattr(obj, 'invoice') or obj.is_locked:
            return "✅ Invoice has been generated."
            
        url = reverse('admin:bookings_booking_generate_invoice_btn', args=[obj.id])
        onclick = "return confirm('Are you sure you want to generate the invoice for this booking? This will lock the booking financials.');"
        return format_html(
            '<a href="{}" onclick="{}" style="display: inline-block; background-color: #8b5cf6; color: white; padding: 10px 16px; border-radius: 6px; text-decoration: none; font-family: sans-serif; font-size: 14px; font-weight: bold;">📝 Generate Invoice Now</a>', 
            url, onclick
        )
    generate_invoice_button.short_description = "Generate Invoice"
    
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/generate-invoice-btn/', self.admin_site.admin_view(self.generate_invoice_button_view), name='bookings_booking_generate_invoice_btn'),
        ]
        return custom_urls + urls
        
    def generate_invoice_button_view(self, request, object_id):
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        from apps.invoices.services import generate_invoice
        
        booking = get_object_or_404(Booking, pk=object_id)
        if booking.is_locked or hasattr(booking, 'invoice'):
            messages.info(request, "Invoice is already generated.")
            return redirect('admin:bookings_booking_change', object_id)
            
        try:
            invoice = generate_invoice(booking, user=request.user)
            messages.success(request, f"Successfully generated Invoice {invoice.invoice_number}!")
            return redirect('admin:invoices_invoice_change', invoice.id)
        except Exception as e:
            messages.error(request, f"Failed to generate invoice: {str(e)}")
            return redirect('admin:bookings_booking_change', object_id)

    def passenger_list(self, obj):
        if not obj or not obj.pk:
            return "No Passengers"
            
        names = []
        for service in obj.services.all():
            for bt in service.booking_travelers.all():
                name = str(bt.traveler.full_name).strip()
                if name and name not in names:
                    names.append(name)
                    
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
        from apps.bookings.models import BookingService
        from apps.bookings.services import update_booking_service, delete_booking_service
        for obj in formset.deleted_objects:
            delete_booking_service(obj, user=request.user)
        for instance in instances:
            if isinstance(instance, BookingService):
                update_booking_service(instance, user=request.user)
            else:
                instance.save()
        formset.save_m2m()

@admin.register(BookingTimeline)
class BookingTimelineAdmin(ModelAdmin):
    readonly_fields = ['full_timeline']
    fieldsets = (
        (None, {
            'fields': ('full_timeline',),
            'classes': ('wide',)
        }),
    )

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

    def full_timeline(self, obj):
        from django.utils.safestring import mark_safe
        from django.urls import reverse
        
        events = []
        
        # 1. Booking Created
        events.append({
            'time': obj.created_at,
            'category': 'INITIAL',
            'color': '#6b7280', # Gray
            'icon': '📝',
            'title': 'Booking Created',
            'desc': f'Booking {obj.booking_number} initiated for {obj.customer.name}',
            'amount': None,
            'link': reverse('admin:bookings_booking_change', args=[obj.id])
        })
        
        # 2. Services Added
        for service in obj.services.all():
            events.append({
                'time': service.created_at,
                'category': 'SERVICE',
                'color': '#3b82f6', # Blue
                'icon': '✈️',
                'title': f'Service Added: {service.service_type.name}',
                'desc': f'Provider: {service.service_provider}',
                'amount': f'+ {service.currency} {service.total_service_charge}',
                'link': reverse('admin:bookings_booking_change', args=[obj.id])
            })
            
            # Passengers added (assuming roughly same time as service)
            for traveler in service.booking_travelers.all():
                events.append({
                    'time': traveler.created_at,
                    'category': 'PASSENGER',
                    'color': '#0ea5e9', # Light Blue
                    'icon': '👤',
                    'title': f'Passenger Added: {traveler.traveler.full_name}',
                    'desc': f'Status: {traveler.passenger_status}',
                    'amount': None,
                    'link': None
                })
        
        # 3. Invoice Generated
        if hasattr(obj, 'invoice'):
            inv = obj.invoice
            events.append({
                'time': inv.created_at,
                'category': 'INVOICE',
                'color': '#f59e0b', # Orange
                'icon': '🧾',
                'title': f'Invoice Generated: {inv.invoice_number}',
                'desc': f'Status: {inv.get_status_display()}',
                'amount': f'{inv.currency} {inv.final_payable}',
                'link': reverse('admin:invoices_invoice_change', args=[inv.id])
            })
            
            # 4. Payments
            for p in inv.payments.all():
                events.append({
                    'time': p.created_at,
                    'category': 'PAYMENT',
                    'color': '#10b981', # Green
                    'icon': '💸',
                    'title': f'Payment Received ({p.get_method_display()})',
                    'desc': f'Ref: {p.reference_number}',
                    'amount': f'- {inv.currency} {p.amount}',
                    'link': reverse('admin:payments_payment_change', args=[p.id])
                })
                
            # 5. Credit Note Allocations
            for a in inv.credit_allocations.all():
                events.append({
                    'time': a.created_at,
                    'category': 'CREDIT',
                    'color': '#8b5cf6', # Purple
                    'icon': '💰',
                    'title': f'Credit Note Applied: {a.credit_note.number}',
                    'desc': f'Source: {a.credit_note.get_source_display()}',
                    'amount': f'- {inv.currency} {a.amount}',
                    'link': reverse('admin:credit_notes_creditallocation_change', args=[a.id]) if hasattr(a, 'id') else None
                })
                
            # 6. Credit Notes Generated
            if hasattr(inv, 'issued_credit_note') and inv.issued_credit_note:
                cn = inv.issued_credit_note
                events.append({
                    'time': cn.created_at,
                    'category': 'CREDIT_GENERATED',
                    'color': '#8b5cf6', # Purple
                    'icon': '✨',
                    'title': f'Credit Note Issued: {cn.number}',
                    'desc': f'Status: {cn.status}',
                    'amount': f'+ {inv.currency} {cn.amount}',
                    'link': reverse('admin:credit_notes_creditnote_change', args=[cn.id])
                })
                
            # 7. Cancellations
            for line in inv.lines.all():
                for traveler in line.travelers.all():
                    if hasattr(traveler, 'cancellation'):
                        c = traveler.cancellation
                        events.append({
                            'time': c.created_at,
                            'category': 'CANCELLATION',
                            'color': '#ef4444', # Red
                            'icon': '❌',
                            'title': f'Cancellation: {traveler.traveler_name}',
                            'desc': f'Refund: {c.total_refund}',
                            'amount': f'- {inv.currency} {c.total_refund}',
                            'link': reverse('admin:cancellations_bookingcancellation_change', args=[c.id])
                        })
                        
        # Collect signatures of live objects to prevent duplicating "Added" audit logs
        live_signatures = [
            f"Booking created for {obj.customer.name}."
        ]
        
        for service in obj.services.all():
            live_signatures.append(f"Service {service.service_type.name} added to booking.")
            for traveler in service.booking_travelers.all():
                live_signatures.append(f"Passenger {traveler.traveler.full_name} added to service.")
                
        if hasattr(obj, 'invoice'):
            inv = obj.invoice
            live_signatures.append(f"Invoice {inv.invoice_number} generated")
            for p in inv.payments.all():
                live_signatures.append(f"Payment of {p.amount} via {p.get_method_display()} was added")
            for a in inv.credit_allocations.all():
                live_signatures.append(f"Credit of {a.amount} from {a.credit_note.number} was allocated")
            if hasattr(inv, 'issued_credit_note') and inv.issued_credit_note:
                cn = inv.issued_credit_note
                live_signatures.append(f"Credit Note {cn.number} of {cn.amount} generated")
            for line in inv.lines.all():
                for traveler in line.travelers.all():
                    if hasattr(traveler, 'cancellation'):
                        live_signatures.append(f"Passenger {traveler.traveler_name} cancelled")

        # 8. Audit Log Events (Deletions, Updates, Status Changes, and Historical Adds)
        for history in obj.history.all():
            from apps.bookings.choices import BookingHistoryAction
            
            creation_actions = [
                BookingHistoryAction.BOOKING_CREATED,
                BookingHistoryAction.SERVICE_CREATED,
                BookingHistoryAction.PASSENGER_ADDED,
                BookingHistoryAction.INVOICE_GENERATED,
                BookingHistoryAction.PAYMENT_ADDED,
                BookingHistoryAction.CREDIT_NOTE_GENERATED,
            ]
            
            # Skip creation/addition audit logs if the live object is already rendering in the timeline
            is_duplicate = False
            if history.action in creation_actions:
                for sig in live_signatures:
                    if sig in history.description:
                        is_duplicate = True
                        break
            if is_duplicate:
                continue
                
            # Determine icon based on action
            icon = '📝'
            deletion_actions = [
                BookingHistoryAction.BOOKING_DELETED, BookingHistoryAction.SERVICE_DELETED, 
                BookingHistoryAction.PASSENGER_DELETED, BookingHistoryAction.BOOKING_CANCELLED, 
                BookingHistoryAction.SERVICE_CANCELLED, BookingHistoryAction.PASSENGER_CANCELLED, 
                BookingHistoryAction.INVOICE_CANCELLED, BookingHistoryAction.CREDIT_NOTE_VOIDED, 
                BookingHistoryAction.PAYMENT_DELETED
            ]
            update_actions = [
                BookingHistoryAction.BOOKING_UPDATED, BookingHistoryAction.SERVICE_UPDATED, 
                BookingHistoryAction.PASSENGER_UPDATED, BookingHistoryAction.PAYMENT_UPDATED,
                BookingHistoryAction.BOOKING_CONFIRMED
            ]
            
            if history.action in deletion_actions:
                icon = '🗑️'
            elif history.action in update_actions:
                icon = '✏️'
            elif history.action == BookingHistoryAction.INVOICE_CLOSED:
                icon = '🔒'
            elif history.action == BookingHistoryAction.INVOICE_OPENED:
                icon = '🔓'
            elif history.action in creation_actions:
                icon = '⚡'
                
            events.append({
                'time': history.created_at,
                'category': 'AUDIT',
                'color': '#475569', # Slate
                'icon': icon,
                'title': f'Audit: {history.action.replace("_", " ").title()}',
                'desc': f'{history.description} (by {history.user.username if history.user else "System"})',
                'amount': None,
                'link': None
            })

        # Sort by time (oldest first)
        events.sort(key=lambda x: x['time'])
        
        # Build HTML
        html = '<div style="font-family: sans-serif; max-width: 800px; margin: 0 auto; background: #f9fafb; padding: 20px; border-radius: 8px;">'
        html += f'<h2 style="margin-top: 0; color: #111827; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px;">Timeline for Booking {obj.booking_number}</h2>'
        
        # Add a visual line container
        html += '<div style="position: relative; padding-top: 20px;">'
        
        for e in events:
            time_str = e['time'].strftime('%b %d, %Y - %I:%M %p')
            
            html += f'<div style="display: flex; margin-bottom: 20px; align-items: flex-start; position: relative;">'
            
            # Left: Icon & Line
            html += f'<div style="display: flex; flex-direction: column; align-items: center; margin-right: 15px;">'
            html += f'<div style="width: 36px; height: 36px; border-radius: 50%; background-color: {e["color"]}; display: flex; align-items: center; justify-content: center; color: white; font-size: 16px; z-index: 2; box-shadow: 0 0 0 4px #f9fafb;">{e["icon"]}</div>'
            html += f'<div style="width: 2px; height: calc(100% + 20px); background-color: #e5e7eb; position: absolute; top: 36px; left: 17px; z-index: 1;"></div>'
            html += f'</div>'
            
            # Right: Content
            html += f'<div style="flex-grow: 1; background: white; padding: 12px 16px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-left: 4px solid {e["color"]}; z-index: 2;">'
            
            # Header
            html += f'<div style="display: flex; justify-content: space-between; margin-bottom: 4px;">'
            title_html = f'<a href="{e["link"]}" style="color: #111827; font-weight: bold; text-decoration: none;">{e["title"]}</a>' if e["link"] else f'<span style="color: #111827; font-weight: bold;">{e["title"]}</span>'
            html += f'<div>{title_html}</div>'
            html += f'<div style="font-size: 12px; color: #6b7280;">{time_str}</div>'
            html += f'</div>'
            
            # Description & Amount
            html += f'<div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px;">'
            html += f'<div style="font-size: 13px; color: #4b5563;">{e["desc"]}</div>'
            if e["amount"]:
                amt_color = '#ef4444' if e["amount"].startswith('-') and 'CANCELLATION' in e["category"] else ('#10b981' if e["amount"].startswith('-') else '#111827')
                html += f'<div style="font-size: 14px; font-weight: bold; color: {amt_color};">{e["amount"]}</div>'
            html += f'</div>'
            
            html += f'</div></div>'
            
        html += '</div></div>'
        return mark_safe(html)
        
    full_timeline.short_description = "Complete Booking History"
