from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from apps.credit_notes.models import CreditNote, CreditAllocation
from apps.invoices.models import Invoice

class CreditNoteService:
    
    @classmethod
    @transaction.atomic
    def allocate_credit(cls, credit_note_id: int, invoice_id: int, amount: Decimal) -> CreditAllocation:
        """
        Allocates credit from a CreditNote to an Invoice.
        """
        if amount <= Decimal("0.00"):
            raise ValidationError("Allocation amount must be greater than zero.")
            
        credit_note = CreditNote.objects.select_for_update().get(id=credit_note_id)
        invoice = Invoice.objects.select_for_update().get(id=invoice_id)
        
        if credit_note.remaining_amount < amount:
            raise ValidationError(f"Cannot allocate {amount}. Only {credit_note.remaining_amount} remains on this credit note.")
            
        if invoice.balance_due < amount:
            raise ValidationError(f"Cannot allocate {amount}. The invoice balance due is only {invoice.balance_due}.")
            
        # Create allocation
        allocation = CreditAllocation.objects.create(
            credit_note=credit_note,
            invoice=invoice,
            amount=amount
        )
        
        # Update credit note
        credit_note.allocated_amount += amount
        if credit_note.allocated_amount >= credit_note.amount:
            credit_note.status = 'FULLY_APPLIED'
        else:
            credit_note.status = 'PARTIALLY_APPLIED'
        credit_note.save(update_fields=['allocated_amount', 'status'])
        
        # Update invoice payment status using central service if necessary,
        # but balance_due handles it via property. Just to trigger standard updates:
        from apps.invoices.services import update_invoice_status
        update_invoice_status(invoice)
        
        return allocation
