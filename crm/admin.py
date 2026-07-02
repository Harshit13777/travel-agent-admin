from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.import_export.admin import ExportModelAdmin
from import_export import resources
from .models import Customer, Passenger

class PassengerInline(TabularInline):
    model = Passenger
    extra = 1

class CustomerResource(resources.ModelResource):
    class Meta:
        model = Customer
        fields = ('id', 'name', 'phone', 'email', 'address', 'company_name', 'GSTIN', 'PAN', 'customer_type', 'created_at')

@admin.register(Customer)
class CustomerAdmin(ExportModelAdmin):
    resource_classes = [CustomerResource]
    list_display = ('name', 'phone', 'email', 'customer_type', 'created_at')
    search_fields = ('name', 'phone', 'email', 'GSTIN', 'company_name')
    list_filter = ('customer_type', 'created_at')
    inlines = [PassengerInline]

@admin.register(Passenger)
class PassengerAdmin(ModelAdmin):
    list_display = ('name', 'customer', 'dob', 'gender', 'is_senior')
    search_fields = ('name', 'customer__name', 'id_number')
    list_filter = ('gender', 'is_senior', 'id_type')
    autocomplete_fields = ('customer',)
