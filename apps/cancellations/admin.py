from django.contrib import admin
from django.forms import ModelForm
from unfold.admin import ModelAdmin, TabularInline
from .models import BookingCancellation

class BookingCancellationForm(ModelForm):
    class Meta:
        model = BookingCancellation
        fields = '__all__'

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
    list_display = ['invoice_line_traveler', 'status', 'service_refund', 'supplier_refund', 'total_refund', 'created_at']
    search_fields = ['invoice_line_traveler__id']
    list_filter = ['status', 'source', 'created_at']
    raw_id_fields = ['invoice_line_traveler']
    list_select_related = ['invoice_line_traveler']
    
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status == 'VOID':
            return [f.name for f in self.model._meta.fields if f.name != 'remarks']
        if obj:
            return ['invoice_line_traveler', 'supplier_refund', 'service_refund', 'cgst_refund', 'sgst_refund', 'igst_refund', 'created_by']
        return []
    
    def has_delete_permission(self, request, obj=None):
        return False # Never delete, only VOID
