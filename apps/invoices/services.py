from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.utils import timezone
from apps.invoices.models import Invoice, InvoiceLine
from apps.invoices.choices import InvoiceStatus
from apps.bookings.models import Booking
from apps.bookings.choices import BookingStatus, BookingServiceStatus, BookingHistoryAction
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
    
    with transaction.atomic():
        # 1. Load active services
        services = booking.services.exclude(status=BookingServiceStatus.CANCELLED)
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
        
        line_data_list = []
        
        for service in services:
            line_supplier = service.supplier_cost.quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
            line_service_charge = service.service_charge.quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
            line_discount = service.discount.quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
            
            line_taxable = Decimal("0.00")
            line_cgst = Decimal("0.00")
            line_sgst = Decimal("0.00")
            line_igst = Decimal("0.00")
            
            is_taxable = getattr(service, 'is_taxable', True)
            
            if is_taxable:
                line_taxable = (line_service_charge - line_discount).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
                if line_taxable < Decimal('0.00'):
                    line_taxable = Decimal("0.00")
                    
                if settings.gst_enabled:
                    if settings.gst_type == 'CGST_SGST':
                        line_cgst = (line_taxable * (settings.cgst_rate / Decimal("100.00"))).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
                        line_sgst = (line_taxable * (settings.sgst_rate / Decimal("100.00"))).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
                    elif settings.gst_type == 'IGST':
                        line_igst = (line_taxable * (settings.igst_rate / Decimal("100.00"))).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
                        
            line_total = (line_supplier + line_service_charge - line_discount + line_cgst + line_sgst + line_igst).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
            
            supplier_total += line_supplier
            service_charge_total += (line_service_charge - line_discount)
            taxable_amount += line_taxable
            cgst_amount += line_cgst
            sgst_amount += line_sgst
            igst_amount += line_igst
            
            line_data_list.append({
                'service': service,
                'supplier_cost': line_supplier,
                'service_charge': line_service_charge,
                'discount': line_discount,
                'is_taxable': is_taxable,
                'taxable_amount': line_taxable,
                'cgst_amount': line_cgst,
                'sgst_amount': line_sgst,
                'igst_amount': line_igst,
                'total': line_total
            })
            
        # 4. Validate Math
        subtotal_before_tax = supplier_total + service_charge_total
        grand_total = (subtotal_before_tax + cgst_amount + sgst_amount + igst_amount).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
        
        credit_applied = Decimal("0.00")
        invoice_number = generate_invoice_number()
        
        # 5. Create Invoice Snapshot
        invoice = Invoice.objects.create(
            booking=booking,
            invoice_number=invoice_number,
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date(),
            
            # Company Identity Snapshot
            company_name=settings.company_name,
            gstin=settings.gstin,
            pan=settings.pan,
            address=settings.address,
            phone=settings.phone,
            email=settings.email,
            
            # Settings Snapshot
            currency=settings.currency,
            gst_enabled=settings.gst_enabled,
            gst_type=settings.gst_type,
            cgst_rate=settings.cgst_rate,
            sgst_rate=settings.sgst_rate,
            igst_rate=settings.igst_rate,
            tax_label_1=settings.tax_label_1,
            tax_label_2=settings.tax_label_2,
            tax_label_3=settings.tax_label_3,
            
            # Financial Snapshot
            supplier_total=supplier_total,
            service_charge_total=service_charge_total,
            subtotal_before_tax=subtotal_before_tax,
            taxable_amount=taxable_amount,
            cgst_amount=cgst_amount,
            sgst_amount=sgst_amount,
            igst_amount=igst_amount,
            
            grand_total=grand_total,
            original_total=grand_total,
            final_payable=grand_total,
            status=InvoiceStatus.ISSUED
        )
        
        # 6. Create Invoice Line Snapshots
        for data in line_data_list:
            service = data['service']
            inv_line = InvoiceLine.objects.create(
                invoice=invoice,
                booking_service=service,
                service_type=service.service_type.name,
                service_provider=service.service_provider,
                supplier_cost=data['supplier_cost'],
                service_charge=data['service_charge'],
                discount=data['discount'],
                is_taxable=data['is_taxable'],
                taxable_amount=data['taxable_amount'],
                cgst_amount=data['cgst_amount'],
                sgst_amount=data['sgst_amount'],
                igst_amount=data['igst_amount'],
                total=data['total']
            )
            
            # Create InvoiceLineTraveler snapshots
            travelers = service.booking_travelers.exclude(passenger_status='CANCELLED')
            t_count = travelers.count()
            if t_count > 0:
                for idx, t in enumerate(travelers):
                    from apps.invoices.models import InvoiceLineTraveler
                    InvoiceLineTraveler.objects.create(
                        invoice_line=inv_line,
                        booking_traveler=t,
                        traveler_sequence=idx + 1,
                        traveler_name=t.traveler.full_name,
                        ticket_number=t.ticket_number,
                        supplier_cost=data['supplier_cost'] / t_count,
                        service_charge=data['service_charge'] / t_count,
                        discount=data['discount'] / t_count,
                        taxable_amount=data['taxable_amount'] / t_count,
                        cgst=data['cgst_amount'] / t_count,
                        sgst=data['sgst_amount'] / t_count,
                        igst=data['igst_amount'] / t_count,
                        total=data['total'] / t_count
                    )
        
        # Apply Credit Notes via CreditAllocation
        if applied_credit_notes:
            from apps.credit_notes.services import CreditNoteService
            
            for cn in applied_credit_notes:
                if cn.customer != booking.customer:
                    raise ValidationError(f"Credit Note {cn.number} belongs to a different customer.")
                
                remaining = cn.remaining_amount
                if remaining <= 0:
                    continue
                    
                amount_to_apply = remaining
                
                if amount_to_apply > (original_total - credit_applied):
                    amount_to_apply = original_total - credit_applied
                
                if amount_to_apply <= 0:
                    continue
                    
                credit_applied += amount_to_apply
                
                CreditNoteService.allocate_credit(
                    credit_note_id=cn.id,
                    invoice_id=invoice.id,
                    amount=amount_to_apply
                )
                
        # 7. Lock Booking and Update Invoice
        final_payable = grand_total - credit_applied
        if final_payable < Decimal("0.00"):
            final_payable = Decimal("0.00")
            
        booking.locked_at = timezone.now()
        booking.save(update_fields=['locked_at'])
        
        invoice.final_payable = final_payable
        invoice.save(update_fields=['final_payable'])
        
        # 8. Audit Trail
        log_booking_history(
            booking=booking,
            action=BookingHistoryAction.INVOICE_GENERATED,
            description=f"Invoice {invoice_number} generated for {grand_total}. Final payable: {final_payable}",
            metadata={
                "invoice_id": invoice.id,
                "supplier_total": str(supplier_total),
                "service_charge_total": str(service_charge_total),
                "grand_total": str(grand_total),
                "gst_type": str(settings.gst_type)
            },
            user=user
        )
        return invoice

def cancel_invoice(invoice: Invoice, user=None) -> Invoice:
    """
    Cancel an invoice.
    """
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
    """
    Update invoice status based on payment_status property.
    This should be called whenever a payment is added or removed.
    """
    with transaction.atomic():
        new_status = invoice.payment_status
        if invoice.status != new_status:
            invoice.status = new_status
            invoice.save(update_fields=['status'])
        return invoice
