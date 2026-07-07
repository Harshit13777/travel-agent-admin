from django.contrib import admin
from django import forms
from django.forms import ModelForm
from unfold.admin import ModelAdmin, TabularInline
from .models import BookingCancellation

class BookingCancellationForm(ModelForm):
    passenger_info = forms.CharField(
        disabled=True, required=False, label="Selected Passenger", initial="Select a passenger"
    )
    original_service_charge = forms.CharField(
        disabled=True, required=False, label="Original Service Charge", initial="-"
    )
    original_supplier_cost = forms.CharField(
        disabled=True, required=False, label="Original Supplier Cost", initial="-"
    )
    original_cgst = forms.CharField(
        disabled=True, required=False, label="Original CGST", initial="-"
    )
    original_sgst = forms.CharField(
        disabled=True, required=False, label="Original SGST", initial="-"
    )
    original_igst = forms.CharField(
        disabled=True, required=False, label="Original IGST", initial="-"
    )

    class Meta:
        model = BookingCancellation
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ilt = None
        if self.instance and self.instance.pk:
            ilt = self.instance.invoice_line_traveler
        elif 'initial' in kwargs and 'invoice_line_traveler' in kwargs['initial']:
            from apps.invoices.models import InvoiceLineTraveler
            ilt_id = kwargs['initial']['invoice_line_traveler']
            try:
                ilt = InvoiceLineTraveler.objects.get(pk=ilt_id)
            except InvoiceLineTraveler.DoesNotExist:
                ilt = None
                
        if ilt:
            self.fields['passenger_info'].initial = f"{ilt.traveler_name} (Ticket: {ilt.ticket_number or 'N/A'}) - Invoice {ilt.invoice_line.invoice.invoice_number}"
            self.fields['original_service_charge'].initial = ilt.service_charge
            self.fields['original_supplier_cost'].initial = ilt.supplier_cost
            self.fields['original_cgst'].initial = ilt.cgst
            self.fields['original_sgst'].initial = ilt.sgst
        if 'invoice_line_traveler' in self.fields:
            self.fields['invoice_line_traveler'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        
        # During 'add', it's in cleaned_data. During 'edit', it's in self.instance because it's readonly
        ilt = cleaned_data.get('invoice_line_traveler')
        if not ilt and self.instance and self.instance.pk:
            ilt = self.instance.invoice_line_traveler
            
        if not ilt:
            return cleaned_data
            
        from django.core.exceptions import ValidationError
        from apps.invoices.choices import InvoiceStatus
        if ilt.invoice_line.invoice.status == InvoiceStatus.CLOSED:
            raise ValidationError("Cannot add or edit cancellations for a CLOSED invoice.")
            
        if not self.instance.pk and hasattr(ilt, 'cancellation') and ilt.cancellation.pk is not None:
            raise ValidationError(f"Traveler {ilt.traveler_name} already has a cancellation record.")
            
        from apps.cancellations.services import CancellationValidationService
        
        refund_data = {
            ilt.id: {
                'supplier_refund': cleaned_data.get('supplier_refund'),
                'service_refund': cleaned_data.get('service_refund'),
                'cgst_refund': cleaned_data.get('cgst_refund'),
                'sgst_refund': cleaned_data.get('sgst_refund'),
                'igst_refund': cleaned_data.get('igst_refund'),
            }
        }
        
        try:
            CancellationValidationService.validate_components([ilt], refund_data)
        except ValidationError as e:
            raise forms.ValidationError(e.message)
            
        return cleaned_data





class BookingCancellationInlineForBooking(TabularInline):
    model = BookingCancellation
    form = BookingCancellationForm
    extra = 0
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False
        
    def has_change_permission(self, request, obj=None):
        return False
        
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

@admin.register(BookingCancellation)
class BookingCancellationAdmin(ModelAdmin):
    form = BookingCancellationForm
    list_display = ['invoice_line_traveler', 'service_refund', 'supplier_refund', 'total_refund', 'created_at']
    search_fields = ['invoice_line_traveler__id']
    list_filter = ['source', 'created_at']
    raw_id_fields = ['invoice_line_traveler']
    list_select_related = ['invoice_line_traveler']
    
    fieldsets = (
        (None, {
            'fields': ('passenger_info', 'invoice_line_traveler')
        }),
        ('Original Invoice Amounts', {
            'fields': (
                ('original_service_charge', 'original_supplier_cost'),
                ('original_cgst', 'original_sgst', 'original_igst')
            ),
            'description': 'These are the maximum amounts you can refund based on the invoice snapshot.'
        }),
        ('Refund Amounts', {
            'fields': (
                ('service_refund', 'supplier_refund'),
                ('cgst_refund', 'sgst_refund', 'igst_refund')
            )
        }),
        ('Details', {
            'fields': ('reason', 'remarks', 'source')
        })
    )
    
    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        if 'invoice_line_traveler' in request.GET:
            initial['invoice_line_traveler'] = request.GET['invoice_line_traveler']
        return initial
        
    def save_model(self, request, obj, form, change):
        from apps.cancellations.services import CancellationService
        from django.core.exceptions import ValidationError
        from django.contrib import messages
        
        refund_data = {
            obj.invoice_line_traveler_id: {
                'supplier_refund': obj.supplier_refund,
                'service_refund': obj.service_refund,
                'cgst_refund': obj.cgst_refund,
                'sgst_refund': obj.sgst_refund,
                'igst_refund': obj.igst_refund,
            }
        }
        
        try:
            if not change:
                cancellations = CancellationService.cancel_passengers(
                    travelers=[obj.invoice_line_traveler],
                    refund_data=refund_data,
                    user=request.user,
                    source=obj.source,
                    reason=obj.reason,
                    remarks=obj.remarks
                )
                if cancellations:
                    obj.pk = cancellations[0].pk
                    obj.id = cancellations[0].id
            else:
                CancellationService.update_cancellation(
                    cancellation=obj,
                    refund_data=refund_data,
                    user=request.user,
                    source=obj.source,
                    reason=obj.reason,
                    remarks=obj.remarks
                )
        except ValidationError as e:
            # We add it as an error to the request context. 
            # Note: since save_model doesn't halt the redirect unless it raises, we MUST raise an exception 
            # or the admin will redirect to the list view acting as if it saved.
            # Most validation should now happen in form.clean() to avoid this block entirely.
            raise e
    
    def get_readonly_fields(self, request, obj=None):
        base_readonly = []
        if obj:
            base_readonly.append('invoice_line_traveler')
        return base_readonly

    def has_add_permission(self, request):
        return True # Handled in form clean or save_model
        
    def response_add(self, request, obj, post_url_continue=None):
        if '_addanother' not in request.POST and '_continue' not in request.POST:
            from django.urls import reverse
            from django.http import HttpResponseRedirect
            try:
                booking_id = obj.invoice_line_traveler.invoice_line.invoice.booking_id
                return HttpResponseRedirect(reverse('admin:bookings_booking_change', args=[booking_id]))
            except Exception:
                pass
        return super().response_add(request, obj, post_url_continue)
        
    def response_change(self, request, obj):
        if '_addanother' not in request.POST and '_continue' not in request.POST and '_saveasnew' not in request.POST:
            from django.urls import reverse
            from django.http import HttpResponseRedirect
            try:
                booking_id = obj.invoice_line_traveler.invoice_line.invoice.booking_id
                return HttpResponseRedirect(reverse('admin:bookings_booking_change', args=[booking_id]))
            except Exception:
                pass
        return super().response_change(request, obj)
        
    def response_delete(self, request, obj_display, obj_id):
        next_url = request.GET.get('next')
        if next_url:
            from django.http import HttpResponseRedirect
            return HttpResponseRedirect(next_url)
        return super().response_delete(request, obj_display, obj_id)
        
    def has_change_permission(self, request, obj=None):
        if obj:
            from apps.invoices.choices import InvoiceStatus
            if obj.invoice_line_traveler.invoice_line.invoice.status == InvoiceStatus.CLOSED:
                return False
        return True
        
    def has_delete_permission(self, request, obj=None):
        if obj:
            from apps.invoices.choices import InvoiceStatus
            if obj.invoice_line_traveler.invoice_line.invoice.status == InvoiceStatus.CLOSED:
                return False
        return True
