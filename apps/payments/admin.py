from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = ['amount', 'invoice', 'date', 'method', 'received_by']
    search_fields = ['reference_number', 'invoice__invoice_number']
    list_filter = ['method']
    
    def has_change_permission(self, request, obj=None):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return False
        
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return [f.name for f in self.model._meta.fields]
        return []
