from django.contrib import admin
from django.forms import ModelForm
from unfold.admin import ModelAdmin, TabularInline
from .models import BookingCancellation, CancellationSettlement
from apps.cancellations.services import CancellationValidationService

class CancellationSettlementForm(ModelForm):
    class Meta:
        model = CancellationSettlement
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        # Create an unsaved instance to validate
        instance = self.save(commit=False)
        CancellationValidationService.validate_settlement_creation(instance)
        return cleaned_data

class BookingCancellationForm(ModelForm):
    class Meta:
        model = BookingCancellation
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        instance = self.save(commit=False)
        CancellationValidationService.validate_cancellation_totals(instance)
        return cleaned_data

class CancellationSettlementInline(TabularInline):
    model = CancellationSettlement
    form = CancellationSettlementForm
    extra = 0
    can_delete = False
    
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status == 'FINALIZED':
            return [f.name for f in self.model._meta.fields]
        return ['status', 'amount_received_date', 'approved_date', 'approved_by']

    def has_change_permission(self, request, obj=None):
        if obj and obj.status == 'FINALIZED':
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.status == 'FINALIZED':
            return False
        return super().has_delete_permission(request, obj)

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
    list_display = ['invoice', 'booking', 'type', 'status', 'service_refund', 'supplier_refund', 'total_refund', 'requested_at']
    search_fields = ['invoice__invoice_number', 'booking__booking_number']
    list_filter = ['status', 'type', 'requested_at']
    autocomplete_fields = ['invoice']
    list_select_related = ['booking', 'invoice', 'invoice_line', 'invoice_line_traveler']
    inlines = [CancellationSettlementInline]
    exclude = ['booking']
    
    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        
        # If this autocomplete request comes from the Settlement form, hide FINALIZED
        if request.GET.get('model_name') == 'cancellationsettlement':
            queryset = queryset.exclude(status='FINALIZED')
            
        return queryset, use_distinct
    
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status == 'FINALIZED':
            return [f.name for f in self.model._meta.fields if f.name != 'remarks']
        return ['status', 'supplier_refund', 'total_refund', 'finalized_invoice_value', 'requested_by', 'requested_at', 'finalized_by', 'finalized_at']

    actions = ['action_finalize_cancellations']
    
    @admin.action(description="Finalize selected Cancellations")
    def action_finalize_cancellations(self, request, queryset):
        from apps.cancellations.services import CancellationFinalizationService
        from django.core.exceptions import ValidationError
        
        success_count = 0
        for cancellation in queryset:
            try:
                CancellationFinalizationService.finalize_cancellation(
                    cancellation_id=cancellation.id,
                    finalized_by_user=request.user
                )
                success_count += 1
            except ValidationError as e:
                self.message_user(request, f"Error finalizing cancellation {cancellation.id}: {e}", level='ERROR')
                
        if success_count > 0:
            self.message_user(request, f"Successfully finalized {success_count} cancellations.")

@admin.register(CancellationSettlement)
class CancellationSettlementAdmin(ModelAdmin):
    form = CancellationSettlementForm
    list_display = ['settlement_number', 'booking_cancellation', 'supplier', 'settled_supplier_refund', 'status', 'approved_date']
    search_fields = ['settlement_number', 'booking_cancellation__invoice__invoice_number', 'supplier', 'supplier_reference', 'bank_reference']
    list_filter = ['status', 'currency', 'approved_date']
    autocomplete_fields = ['booking_cancellation']
    list_select_related = ['booking_cancellation']
    actions = ['action_approve_settlements']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "booking_cancellation":
            kwargs["queryset"] = BookingCancellation.objects.exclude(status='FINALIZED')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    @admin.action(description="Approve selected Settlements")
    def action_approve_settlements(self, request, queryset):
        from django.utils import timezone
        
        success_count = 0
        for settlement in queryset:
            if settlement.status != 'APPROVED':
                settlement.status = 'APPROVED'
                settlement.approved_date = timezone.now()
                settlement.approved_by = request.user
                settlement.save(update_fields=['status', 'approved_date', 'approved_by'])
                success_count += 1
                
        if success_count > 0:
            self.message_user(request, f"Successfully approved {success_count} settlements.")
    
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.booking_cancellation and obj.booking_cancellation.status == 'FINALIZED':
            return [f.name for f in self.model._meta.fields]
        if obj and obj.status in ['APPROVED', 'REJECTED']:
            return [f.name for f in self.model._meta.fields if f.name != 'remarks']
        return ['status', 'approved_date', 'approved_by']

    def has_change_permission(self, request, obj=None):
        if obj and obj.booking_cancellation and obj.booking_cancellation.status == 'FINALIZED':
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.booking_cancellation and obj.booking_cancellation.status == 'FINALIZED':
            return False
        return super().has_delete_permission(request, obj)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.exclude(booking_cancellation__status='FINALIZED')
