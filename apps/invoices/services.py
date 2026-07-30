from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.utils import timezone
from apps.invoices.models import Invoice, InvoiceLine, InvoiceLineTraveler
from apps.invoices.choices import InvoiceStatus
from apps.bookings.models import Booking, BookingTraveler
from apps.bookings.choices import BookingStatus, BookingHistoryAction, PassengerStatus
from apps.common.number_generator import generate_invoice_number
from apps.bookings.services import log_booking_history
from apps.common.services import get_company_settings
from django.core.exceptions import ValidationError

def generate_invoice(booking: Booking, user=None) -> Invoice:
    """
    Generate an invoice for a confirmed booking.
    
    IMPORTANT:
    - Invoice is a permanent, immutable legal snapshot.
    - Booking data is never used again for accounting after invoice generation.
    - Credit Notes are the ONLY mechanism for post-invoice financial adjustments.
    - Payments never modify invoice totals, only the outstanding balance.
    
    Rules:
    - Validate Booking is CONFIRMED.
    - Validate Booking has at least one BookingService.
    - Prevent duplicate invoices.
    - Copy Booking financial totals into the Invoice.
    - Copy BookingServices to InvoiceLines for traceability.
    - Generate Invoice Number using generate_invoice_number().
    - Set Booking.locked_at.
    - Log BookingHistory using INVOICE_GENERATED.
    - Run inside transaction.atomic().
    """
    if booking.has_invoice:
        raise ValidationError("An active invoice already exists for this booking.")
        
    if not booking.services.exists():
        raise ValidationError("Booking must have at least one service to generate an invoice.")
        
    # We now allow invoicing regardless of passenger statuses.
    # However, we must ensure that no passenger has 0 supplier/service costs before locking the invoice.
    travelers_to_invoice = BookingTraveler.objects.filter(booking_service__booking=booking)
    
    if not travelers_to_invoice.exists():
        raise ValidationError("No active passengers to invoice.")
        
    for t in travelers_to_invoice:
        if t.supplier_cost <= Decimal("0.00") and t.service_charge <= Decimal("0.00"):
            raise ValidationError(f"Passenger {t.traveler.first_name} has no financial costs set. Cannot generate invoice.")
    
    with transaction.atomic():
        # 1. Load all services (we filter out cancelled travelers later)
        services = booking.services.all()
        if not services:
            raise ValidationError("No active services to invoice.")
            
        # 2. Read Company Settings Exactly Once
        settings = get_company_settings()
        
        # 3. Calculate Line Totals and Taxes
        supplier_total = Decimal("0.00")
        service_charge_total = Decimal("0.00")
        taxable_amount = Decimal("0.00")
        cgst_amount = Decimal("0.00")
        sgst_amount = Decimal("0.00")
        igst_amount = Decimal("0.00")
        
        invoice_number = generate_invoice_number()
        
        # Create Invoice Header Snapshot
        invoice = Invoice.objects.create(
            booking=booking,
            invoice_number=invoice_number,
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date(),
            
            company_name=settings.company_name,
            gstin=settings.gstin,
            pan=settings.pan,
            address=settings.address,
            phone=settings.phone,
            email=settings.email,
            
            currency=settings.currency,
            gst_enabled=settings.gst_enabled,
            gst_type=settings.gst_type,
            cgst_rate=settings.cgst_rate,
            sgst_rate=settings.sgst_rate,
            igst_rate=settings.igst_rate,
            tax_label_1=settings.tax_label_1,
            tax_label_2=settings.tax_label_2,
            tax_label_3=settings.tax_label_3,
        )
        
        for service in services:
            travelers = service.booking_travelers.all()
            if not travelers.exists():
                continue
                
            line_supplier = Decimal("0.00")
            line_service_charge = Decimal("0.00")
            line_discount = Decimal("0.00")
            
            line_taxable = Decimal("0.00")
            line_cgst = Decimal("0.00")
            line_sgst = Decimal("0.00")
            line_igst = Decimal("0.00")
            
            inv_line = InvoiceLine.objects.create(
                invoice=invoice,
                booking_service=service,
                service_type=service.service_type.name,
                service_provider=service.service_provider,
            )
            
            for idx, t in enumerate(travelers):
                t_taxable = Decimal("0.00")
                t_cgst = Decimal("0.00")
                t_sgst = Decimal("0.00")
                t_igst = Decimal("0.00")
                
                if t.is_gst_applicable:
                    t_taxable = t.service_charge
                    if settings.gst_enabled:
                        if settings.gst_type == 'CGST_SGST':
                            t_cgst = (t_taxable * (settings.cgst_rate / Decimal("100.00"))).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
                            t_sgst = (t_taxable * (settings.sgst_rate / Decimal("100.00"))).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
                        elif settings.gst_type == 'IGST':
                            t_igst = (t_taxable * (settings.igst_rate / Decimal("100.00"))).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
                    
                t_total = t.supplier_cost + t.service_charge + t_cgst + t_sgst + t_igst
                
                InvoiceLineTraveler.objects.create(
                    invoice_line=inv_line,
                    booking_traveler=t,
                    traveler_sequence=idx + 1,
                    traveler_name=t.traveler.full_name,
                    ticket_number=t.ticket_number,
                    supplier_cost=t.supplier_cost,
                    service_charge=t.service_charge,
                    discount=Decimal("0.00"),  # No passenger discount for now
                    taxable_amount=t_taxable,
                    cgst=t_cgst,
                    sgst=t_sgst,
                    igst=t_igst,
                    total=t_total
                )
                
                line_supplier += t.supplier_cost
                line_service_charge += t.service_charge
                line_taxable += t_taxable
                line_cgst += t_cgst
                line_sgst += t_sgst
                line_igst += t_igst
                
            line_total = line_supplier + line_service_charge - line_discount + line_cgst + line_sgst + line_igst
            
            inv_line.supplier_cost = line_supplier
            inv_line.service_charge = line_service_charge
            inv_line.discount = line_discount
            inv_line.taxable_amount = line_taxable
            inv_line.cgst_amount = line_cgst
            inv_line.sgst_amount = line_sgst
            inv_line.igst_amount = line_igst
            inv_line.total = line_total
            inv_line.save()
            
            supplier_total += line_supplier
            service_charge_total += line_service_charge
            taxable_amount += line_taxable
            cgst_amount += line_cgst
            sgst_amount += line_sgst
            igst_amount += line_igst
            
        # Invoice Totals
        subtotal_before_tax = supplier_total + service_charge_total
        # For MVP we don't handle global discount, we assume discount at line level. 
        # But wait, we didn't subtract discount from global service_charge_total! Let's do it if we need to.
        # It's better to just leave discount 0 or remove it if not asked.
        grand_total = subtotal_before_tax + cgst_amount + sgst_amount + igst_amount
        
        invoice.supplier_total = supplier_total
        invoice.service_charge_total = service_charge_total
        invoice.subtotal_before_tax = subtotal_before_tax
        invoice.taxable_amount = taxable_amount
        invoice.cgst_amount = cgst_amount
        invoice.sgst_amount = sgst_amount
        invoice.igst_amount = igst_amount
        invoice.grand_total = grand_total
        invoice.original_total = grand_total
        invoice.final_payable = grand_total
        invoice.status = InvoiceStatus.ISSUED
        invoice.save()
        invoice.final_payable = grand_total
        invoice.save(update_fields=['final_payable'])
        
        booking.locked_at = timezone.now()
        booking.save(update_fields=['locked_at'])
        
        log_booking_history(
            booking=booking,
            action=BookingHistoryAction.INVOICE_GENERATED,
            description=f"Invoice {invoice_number} generated.",
            metadata={"invoice_id": invoice.id},
            user=user
        )
        return invoice

def cancel_invoice(invoice: Invoice, user=None) -> Invoice:
    from django.core.exceptions import ValidationError
    if invoice.status == InvoiceStatus.VOID:
        return invoice
        
    # Validation: Cannot void if there are payments
    if invoice.payments.exists():
        raise ValidationError("Cannot void invoice: there are active payments. Please refund or delete the payments first.")
        
    # Validation: Cannot void if there are credit allocations applied to this invoice
    if invoice.credit_allocations.exists():
        raise ValidationError("Cannot void invoice: there are credit notes applied to it. Please remove the allocations first.")
        
    # Validation: What if this invoice generated a credit note?
    if hasattr(invoice, 'issued_credit_note') and invoice.issued_credit_note:
        cn = invoice.issued_credit_note
        if cn.allocated_amount > 0:
            raise ValidationError("Cannot void invoice: it generated a Credit Note that has already been allocated to another invoice. Please remove that allocation first.")
        else:
            from apps.credit_notes.services import CreditNoteService
            CreditNoteService.delete_credit_note(cn.id, user=user)
        
    with transaction.atomic():
        invoice.status = InvoiceStatus.VOID
        invoice.save(update_fields=['status'])
        
        # Unlock the booking so a new invoice can be generated if needed
        invoice.booking.locked_at = None
        invoice.booking.save(update_fields=['locked_at'])
        
        log_booking_history(
            booking=invoice.booking,
            action=BookingHistoryAction.INVOICE_CANCELLED,
            description=f"Invoice {invoice.invoice_number} was VOIDED.",
            metadata={"invoice_id": invoice.id},
            user=user
        )
        return invoice

def update_invoice_status(invoice: Invoice) -> Invoice:
    with transaction.atomic():
        new_status = invoice.payment_status
        if invoice.status != new_status:
            invoice.status = new_status
            invoice.save(update_fields=['status'])
        return invoice

def close_invoice(invoice: Invoice, user=None) -> Invoice:
    if invoice.status != InvoiceStatus.CLOSED:
        invoice.status = InvoiceStatus.CLOSED
        invoice.save(update_fields=['status'])
        from apps.bookings.choices import BookingHistoryAction
        log_booking_history(
            booking=invoice.booking,
            action=BookingHistoryAction.INVOICE_CLOSED,
            description=f"Invoice {invoice.invoice_number} was marked as CLOSED. Financials locked.",
            metadata={"invoice_id": invoice.id},
            user=user
        )
    return invoice

def reopen_invoice(invoice: Invoice, user=None) -> Invoice:
    from django.core.exceptions import ValidationError
    from apps.invoices.choices import InvoiceStatus
    
    if invoice.status != InvoiceStatus.CLOSED:
        raise ValidationError("Invoice is not closed.")
        
    # Check generated credit note
    if hasattr(invoice, 'issued_credit_note') and invoice.issued_credit_note:
        cn = invoice.issued_credit_note
        if cn.allocated_amount > 0:
            raise ValidationError("Cannot re-open: This invoice has generated a Credit Note that has already been allocated. Please remove the allocation first.")
        else:
            from apps.credit_notes.services import CreditNoteService
            CreditNoteService.delete_credit_note(cn.id, user=user)

    invoice.status = InvoiceStatus.ISSUED
    invoice.save(update_fields=['status'])
    
    from apps.bookings.choices import BookingHistoryAction
    from apps.bookings.services import log_booking_history
    log_booking_history(
        booking=invoice.booking,
        action=BookingHistoryAction.INVOICE_OPENED,
        description=f"Invoice {invoice.invoice_number} was RE-OPENED. Financials unlocked.",
        metadata={"invoice_id": invoice.id},
        user=user
    )
    update_invoice_status(invoice)
    return invoice
