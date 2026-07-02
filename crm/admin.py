from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from import_export.admin import ExportMixin
from import_export import resources
from django.utils.html import format_html
from django.urls import reverse
from .models import Customer, Passenger

class PassengerInline(TabularInline):
    model = Passenger
    extra = 1

class CustomerResource(resources.ModelResource):
    class Meta:
        model = Customer
        fields = ('id', 'name', 'phone', 'email', 'address', 'company_name', 'GSTIN', 'PAN', 'customer_type', 'created_at')

@admin.register(Customer)
class CustomerAdmin(ExportMixin, ModelAdmin):
    resource_classes = [CustomerResource]
    list_display = ('name', 'phone', 'email', 'customer_type', 'created_at', 'edit_button')
    list_display_links = ('name',)
    search_fields = ('name', 'phone', 'email', 'GSTIN', 'company_name')
    list_filter = ('customer_type', 'created_at')
    inlines = [PassengerInline]

    def edit_button(self, obj):
        url = reverse("admin:crm_customer_change", args=[obj.id])
        return format_html('<a class="font-medium text-primary-600 hover:text-primary-500" href="{}">Edit</a>', url)
    edit_button.short_description = 'Action'

@admin.register(Passenger)
class PassengerAdmin(ModelAdmin):
    list_display = ('name', 'customer_link', 'dob', 'gender', 'is_senior', 'edit_button')
    list_display_links = ('name',)
    search_fields = ('name', 'customer__name', 'id_number')
    list_filter = ('gender', 'is_senior', 'id_type')
    autocomplete_fields = ('customer',)

    def customer_link(self, obj):
        if obj.customer:
            url = reverse("admin:crm_customer_change", args=[obj.customer.id])
            return format_html('<a class="font-medium text-primary-600 hover:text-primary-500" href="{}">{}</a>', url, obj.customer.name)
        return "-"
    customer_link.short_description = 'Customer'

    def edit_button(self, obj):
        url = reverse("admin:crm_passenger_change", args=[obj.id])
        return format_html('<a class="font-medium text-primary-600 hover:text-primary-500" href="{}">Edit</a>', url)
    edit_button.short_description = 'Action'
