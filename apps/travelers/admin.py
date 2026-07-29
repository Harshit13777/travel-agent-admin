from django.contrib import admin
from unfold.admin import ModelAdmin
from django import forms
from .models import Traveler
from .services import TravelerService

class TravelerAdminForm(forms.ModelForm):
    class Meta:
        model = Traveler
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        TravelerService.validate_traveler(
            dob=cleaned_data.get('dob'),
            passport_issue_date=cleaned_data.get('passport_issue_date'),
            passport_expiry=cleaned_data.get('passport_expiry')
        )
        return cleaned_data

@admin.register(Traveler)
class TravelerAdmin(ModelAdmin):
    form = TravelerAdminForm
    list_display = ['full_name', 'customer', 'primary_identity_type', 'phone']
    search_fields = ['full_name', 'phone', 'primary_identity_number', 'passport_number']
    list_filter = ['primary_identity_type']
    
    def save_model(self, request, obj, form, change):
        TravelerService.save_traveler(obj, user=request.user, change=change)
        
    def delete_model(self, request, obj):
        TravelerService.delete_traveler(obj, user=request.user)
        
    def delete_queryset(self, request, queryset):
        for obj in queryset:
            TravelerService.delete_traveler(obj, user=request.user)
