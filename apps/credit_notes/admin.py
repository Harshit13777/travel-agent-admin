from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import CreditNote, CreditAllocation

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
    list_display = ['number', 'customer', 'invoice', 'amount', 'remaining_amount', 'source', 'status']
    search_fields = ['number', 'customer__name', 'invoice__invoice_number']
    list_filter = ['status', 'source', 'issued_at']
    autocomplete_fields = ['customer', 'invoice']
    list_select_related = ['customer', 'invoice']
    inlines = [CreditAllocationInline]
    
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields] + ['remaining_amount']
        
    def has_add_permission(self, request):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return False
