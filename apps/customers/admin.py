from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Customer, Supplier

@admin.register(Customer)
class CustomerAdmin(ModelAdmin):
    list_display = ['name', 'customer_type', 'phone', 'is_active']
    search_fields = ['name', 'phone', 'email', 'gst_number']
    list_filter = ['customer_type', 'is_active']

@admin.register(Supplier)
class SupplierAdmin(ModelAdmin):
    list_display = ['name', 'phone', 'is_active']
    search_fields = ['name', 'phone', 'gst_number']
    list_filter = ['is_active']
