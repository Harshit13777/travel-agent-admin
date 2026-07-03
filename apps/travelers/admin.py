from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Traveler

@admin.register(Traveler)
class TravelerAdmin(ModelAdmin):
    list_display = ['full_name', 'customer', 'primary_identity_type', 'phone']
    search_fields = ['full_name', 'phone', 'primary_identity_number', 'passport_number']
    list_filter = ['primary_identity_type']
