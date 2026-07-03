from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import CreditNote, CreditNoteLine, CreditAllocation

class CreditNoteLineInline(TabularInline):
    model = CreditNoteLine
    extra = 0
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False
        
    def has_change_permission(self, request, obj=None):
        return False
        
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

class CreditAllocationInline(TabularInline):
    model = CreditAllocation
    extra = 0
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False
        
    def has_change_permission(self, request, obj=None):
        return False
        
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]


@admin.register(CreditNote)
class CreditNoteAdmin(ModelAdmin):
    list_display = ['credit_note_number', 'booking', 'invoice', 'total_credit', 'remaining_credit', 'status']
    search_fields = ['credit_note_number', 'booking__booking_number', 'invoice__invoice_number']
    list_filter = ['status', 'issued_date']
    autocomplete_fields = ['booking', 'invoice']
    list_select_related = ['booking', 'invoice']
    inlines = [CreditNoteLineInline, CreditAllocationInline]
    
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]
        
    def has_add_permission(self, request):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return False
