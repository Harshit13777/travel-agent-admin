from django.utils import timezone
from django.db import transaction
from apps.common.models import NumberSequence

def _generate_number(sequence_name: str, prefix: str) -> str:
    """
    Generate a transaction-safe number.
    Uses select_for_update to prevent race conditions.
    """
    with transaction.atomic():
        seq, created = NumberSequence.objects.select_for_update().get_or_create(
            prefix=sequence_name,
            defaults={'last_value': '', 'current_year': timezone.now().year, 'current_sequence': 0}
        )
        
        current_year = timezone.now().year
        
        if seq.current_year != current_year:
            seq.current_year = current_year
            seq.current_sequence = 0
            
        seq.current_sequence += 1
        seq.save(update_fields=['current_year', 'current_sequence'])
        
        return f"{prefix}-{current_year}-{seq.current_sequence:04d}"

def generate_booking_number() -> str:
    return _generate_number("BOOKING", "BKG")

def generate_invoice_number() -> str:
    return _generate_number("INVOICE", "INV")

def generate_credit_note_number() -> str:
    return _generate_number("CREDIT_NOTE", "CN")

def generate_payment_number() -> str:
    return _generate_number("PAYMENT", "PAY")


