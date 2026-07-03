from django.utils import timezone
from django.db import transaction
from apps.common.models import NumberSequence

def _generate_number(*, prefix: str) -> str:
    """
    Generate a transaction-safe number.
    Uses select_for_update to prevent race conditions.
    """
    with transaction.atomic():
        seq, created = NumberSequence.objects.select_for_update().get_or_create(
            prefix=prefix,
            defaults={'last_value': ''}
        )
        
        current_time_str = timezone.now().strftime('%Y%m%d%H%M%S')
        
        if seq.last_value >= current_time_str:
            # If generated in the same second, increment the second artificially
            from datetime import datetime, timedelta
            last_dt = datetime.strptime(seq.last_value, '%Y%m%d%H%M%S')
            next_dt = last_dt + timedelta(seconds=1)
            current_time_str = next_dt.strftime('%Y%m%d%H%M%S')
            
        seq.last_value = current_time_str
        seq.save(update_fields=['last_value'])
        
        return f"{prefix}-{current_time_str}"

def generate_booking_number() -> str:
    return _generate_number(prefix="BKG")

def generate_invoice_number() -> str:
    return _generate_number(prefix="INV")

def generate_credit_note_number() -> str:
    return _generate_number(prefix="CN")

def generate_voucher_number() -> str:
    return _generate_number(prefix="VCH")
