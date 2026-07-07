from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from apps.credit_notes.models import CreditNote, CreditAllocation
from apps.invoices.models import Invoice
from apps.credit_notes.choices import CreditNoteStatus, CreditNoteSource
from apps.invoices.choices import InvoiceStatus

class CreditNoteService:
    
    @classmethod
    def validate_allocation(cls, credit_note, invoice, amount):
        if not credit_note or not invoice or not amount:
            return
            
        if credit_note.customer and invoice.booking.customer and credit_note.customer != invoice.booking.customer:
            raise ValidationError("The Credit Note and Invoice must belong to the same customer.")
            
        if amount <= 0:
            raise ValidationError("Allocation amount must be greater than zero.")
            
        if credit_note.remaining_amount < amount:
            raise ValidationError(f"Cannot allocate {amount}. Only {credit_note.remaining_amount} remains on this credit note.")
            
        if invoice.balance_due < amount:
            raise ValidationError(f"Cannot allocate {amount}. The invoice balance due is only {invoice.balance_due}.")
            
    @classmethod
    @transaction.atomic
    def allocate_credit(cls, credit_note_id: int, invoice_id: int, amount: Decimal) -> CreditAllocation:
        """
        Allocates credit from a CreditNote to an Invoice.
        """
        credit_note = CreditNote.objects.select_for_update().get(id=credit_note_id)
        invoice = Invoice.objects.select_for_update().get(id=invoice_id)
        
        # Run centralized validation
        cls.validate_allocation(credit_note, invoice, amount)
            
        # Create allocation
        allocation = CreditAllocation.objects.create(
            credit_note=credit_note,
            invoice=invoice,
            amount=amount
        )
        
        # Update credit note
        credit_note.allocated_amount += amount
        if credit_note.allocated_amount >= credit_note.amount:
            credit_note.status = CreditNoteStatus.FULLY_APPLIED
        else:
            credit_note.status = CreditNoteStatus.PARTIALLY_APPLIED
        credit_note.save(update_fields=['allocated_amount', 'status'])
        
        # Update invoice payment status using central service if necessary,
        # but balance_due handles it via property. Just to trigger standard updates:
        from apps.invoices.services import update_invoice_status
        update_invoice_status(invoice)
        
        return allocation

    @classmethod
    @transaction.atomic
    def deallocate_credit(cls, allocation_id: int):
        """
        Removes an allocation and refunds the amount back to the CreditNote.
        Fails if the linked Invoice is CLOSED.
        """
        allocation = CreditAllocation.objects.select_for_update().get(id=allocation_id)
        credit_note = CreditNote.objects.select_for_update().get(id=allocation.credit_note_id)
        invoice = Invoice.objects.select_for_update().get(id=allocation.invoice_id)
        
        if invoice.status == InvoiceStatus.CLOSED:
            raise ValidationError("Cannot deallocate credit from a CLOSED invoice.")
            
        amount = allocation.amount
        allocation.delete()
        
        # Update credit note
        credit_note.allocated_amount -= amount
        if credit_note.allocated_amount <= Decimal("0.00"):
            credit_note.status = CreditNoteStatus.ACTIVE
        else:
            credit_note.status = CreditNoteStatus.PARTIALLY_APPLIED
        credit_note.save(update_fields=['allocated_amount', 'status'])
        
        # Trigger invoice update
        from apps.invoices.services import update_invoice_status
        update_invoice_status(invoice)

    @classmethod
    @transaction.atomic
    def update_allocation(cls, allocation_id: int, new_amount: Decimal):
        """
        Updates an existing allocation.
        It refunds the old amount, and then allocates the new amount.
        """
        allocation = CreditAllocation.objects.select_for_update().get(id=allocation_id)
        credit_note = CreditNote.objects.select_for_update().get(id=allocation.credit_note_id)
        invoice = Invoice.objects.select_for_update().get(id=allocation.invoice_id)
        
        if invoice.status == InvoiceStatus.CLOSED:
            raise ValidationError("Cannot edit credit allocation on a CLOSED invoice.")
            
        old_amount = allocation.amount
        
        if new_amount <= Decimal("0.00"):
            raise ValidationError("Allocation amount must be greater than zero.")
            
        if new_amount > (credit_note.amount - credit_note.allocated_amount + old_amount):
            raise ValidationError("Credit Note does not have enough remaining balance.")
            
        # Refund old amount
        credit_note.allocated_amount -= old_amount
        
        # Apply new amount
        credit_note.allocated_amount += new_amount
        allocation.amount = new_amount
        allocation.save(update_fields=['amount'])
        
        if credit_note.allocated_amount >= credit_note.amount:
            credit_note.status = CreditNoteStatus.FULLY_APPLIED
        elif credit_note.allocated_amount <= Decimal("0.00"):
            credit_note.status = CreditNoteStatus.ACTIVE
        else:
            credit_note.status = CreditNoteStatus.PARTIALLY_APPLIED
        credit_note.save(update_fields=['allocated_amount', 'status'])
        
        from apps.invoices.services import update_invoice_status
        update_invoice_status(invoice)
        return allocation


    @classmethod
    @transaction.atomic
    def generate_from_overpayment(cls, invoice, user):
        """
        Generates a Credit Note from a negative balance on a CLOSED invoice.
        """
        if invoice.status != InvoiceStatus.CLOSED:
            raise ValidationError("Invoice must be CLOSED before generating a Credit Note.")
            
        if invoice.balance_due >= 0:
            raise ValidationError("Invoice does not have a negative balance (overpayment).")
            
        if invoice.credit_allocations.exists():
            raise ValidationError("Cannot generate a new credit note because you have active Credit Note Allocations applied to this invoice. Please reduce or remove the applied allocations instead to balance the invoice.")
            
        amount = abs(invoice.balance_due)
        
        # Determine Source
        source = CreditNoteSource.OVERPAYMENT
        
        cn = CreditNote.objects.create(
            customer=invoice.booking.customer,
            invoice=invoice,
            source=source,
            amount=amount,
            issued_by=user,
            reason=f"Generated from overpayment on {invoice.invoice_number}",
            status=CreditNoteStatus.ACTIVE
        )
        
        # Generate number if not generated yet (assuming signals handle this or we can generate it)
        if not cn.number:
            cn.number = f"CN-{cn.id:04d}"
            cn.save(update_fields=['number'])
            
        return cn
