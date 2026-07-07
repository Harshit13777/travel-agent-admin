from django.contrib import admin
from unfold.admin import ModelAdmin
from django import forms
from .models import Customer, Supplier
from .services import CustomerService

class CustomerAdminForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        CustomerService.validate_customer(
            credit_limit=cleaned_data.get('credit_limit'),
            gst_number=cleaned_data.get('gst_number'),
            pan=cleaned_data.get('pan')
        )
        return cleaned_data

@admin.register(Customer)
class CustomerAdmin(ModelAdmin):
    form = CustomerAdminForm
    list_display = ['name', 'customer_type', 'phone', 'is_active']
    search_fields = ['name', 'phone', 'email', 'gst_number']
    list_filter = ['customer_type', 'is_active']

@admin.register(Supplier)
class SupplierAdmin(ModelAdmin):
    list_display = ['name', 'phone', 'is_active']
    search_fields = ['name', 'phone', 'gst_number']
    list_filter = ['is_active']
