from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Voucher

@admin.register(Voucher)
class VoucherAdmin(ModelAdmin):
    list_display = ['voucher_number', 'customer', 'original_amount', 'remaining_balance', 'status']
    search_fields = ['voucher_number', 'customer__name']
    list_filter = ['status']
