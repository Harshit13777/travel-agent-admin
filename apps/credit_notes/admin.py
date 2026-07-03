from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import CreditNote

@admin.register(CreditNote)
class CreditNoteAdmin(ModelAdmin):
    list_display = ['credit_note_number', 'booking', 'amount', 'remaining_amount', 'issued_date']
    search_fields = ['credit_note_number', 'booking__booking_number']
