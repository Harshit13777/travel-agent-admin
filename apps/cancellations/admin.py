from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import BookingCancellation, CancellationSettlement

class CancellationSettlementInline(TabularInline):
    model = CancellationSettlement
    extra = 0
    can_delete = False
    
    def get_readonly_fields(self, request, obj=None):
        return ['status', 'amount_received_date', 'approved_date', 'approved_by']

@admin.register(BookingCancellation)
class BookingCancellationAdmin(ModelAdmin):
    list_display = ['invoice', 'booking', 'type', 'status', 'service_refund', 'supplier_refund', 'total_refund', 'requested_at']
    search_fields = ['invoice__invoice_number', 'booking__booking_number']
    list_filter = ['status', 'type', 'requested_at']
    autocomplete_fields = ['booking', 'invoice']
    list_select_related = ['booking', 'invoice', 'invoice_line', 'invoice_line_traveler']
    inlines = [CancellationSettlementInline]
    
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
    list_display = ['settlement_number', 'booking_cancellation', 'supplier', 'settled_supplier_refund', 'status', 'approved_date']
    search_fields = ['settlement_number', 'booking_cancellation__invoice__invoice_number', 'supplier', 'supplier_reference', 'bank_reference']
    list_filter = ['status', 'currency', 'approved_date']
    autocomplete_fields = ['booking_cancellation']
    list_select_related = ['booking_cancellation']
    actions = ['action_approve_settlements']
    
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
        if obj and obj.status in ['APPROVED', 'REJECTED']:
            return [f.name for f in self.model._meta.fields if f.name != 'remarks']
        return ['status', 'approved_date', 'approved_by']
