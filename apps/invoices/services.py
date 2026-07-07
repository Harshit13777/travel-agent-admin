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

def generate_invoice(booking: Booking, user=None, applied_credit_notes=None) -> Invoice:
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
    - Apply CreditNotes via CreditAllocation.
    - Generate Invoice Number using generate_invoice_number().
    - Set Booking.locked_at.
    - Log BookingHistory using INVOICE_GENERATED.
    - Run inside transaction.atomic().
    """
    if booking.status != BookingStatus.CONFIRMED:
        raise ValidationError("Booking must be Confirmed to generate an invoice.")
        
    if not booking.services.exists():
        raise ValidationError("Booking must have at least one service to generate an invoice.")
        
    if hasattr(booking, 'invoice'):
        raise ValidationError("An invoice already exists for this booking.")
        
    # Check for any pending passengers
    if BookingTraveler.objects.filter(booking_service__booking=booking, passenger_status=PassengerStatus.PENDING).exists():
        raise ValidationError("Cannot generate invoice while there are passengers with PENDING status.")
    
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
            travelers = service.booking_travelers.exclude(passenger_status='CANCELLED')
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
        
        # Credit notes logic...
        credit_applied = Decimal("0.00")
        if applied_credit_notes:
            from apps.credit_notes.services import CreditNoteService
            for cn in applied_credit_notes:
                remaining = cn.remaining_amount
                if remaining > 0:
                    amount_to_apply = min(remaining, grand_total - credit_applied)
                    if amount_to_apply > 0:
                        credit_applied += amount_to_apply
                        CreditNoteService.allocate_credit(cn.id, invoice.id, amount_to_apply)
                        
        final_payable = max(Decimal("0.00"), grand_total - credit_applied)
        invoice.final_payable = final_payable
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
    if invoice.status == InvoiceStatus.VOID:
        return invoice
        
    with transaction.atomic():
        invoice.status = InvoiceStatus.VOID
        invoice.save(update_fields=['status'])
        log_booking_history(
            booking=invoice.booking,
            action=BookingHistoryAction.INVOICE_CANCELLED,
            description=f"Invoice {invoice.invoice_number} was voided.",
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
