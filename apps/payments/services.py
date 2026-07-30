from django.core.exceptions import ValidationError
from apps.invoices.choices import InvoiceStatus

class PaymentService:
    @staticmethod
    def validate_payment(invoice):
        """
        Validates if a payment can be made for the given invoice.
        """
        if not invoice:
            return
            
        if invoice.status == InvoiceStatus.VOID:
            raise ValidationError("Cannot add or edit payments for a VOIDED invoice.")
            
        if invoice.status == InvoiceStatus.CLOSED:
            raise ValidationError("Cannot add or edit payments for a CLOSED invoice. Please re-open the invoice first.")

    @staticmethod
    def save_payment(payment, user, change):
        PaymentService.validate_payment(payment.invoice)
        payment.save()
        
        from apps.bookings.services import log_booking_history
        from apps.bookings.choices import BookingHistoryAction
        
        action = BookingHistoryAction.PAYMENT_UPDATED if change else BookingHistoryAction.PAYMENT_ADDED
        log_booking_history(
            booking=payment.invoice.booking,
            action=action,
            description=f"Payment of {payment.amount} via {payment.get_method_display()} was {'updated' if change else 'added'}.",
            metadata={
                "payment_id": payment.id,
                "amount": str(payment.amount),
                "method": payment.get_method_display(),
                "invoice_id": payment.invoice.id
            },
            user=user
        )
        
        # Sync the invoice status automatically (e.g. UNPAID -> PARTIAL)
        from apps.invoices.services import update_invoice_status
        update_invoice_status(payment.invoice)
        
        return payment

    @staticmethod
    def delete_payment(payment, user):
        PaymentService.validate_payment(payment.invoice)
        amount = payment.amount
        method = payment.get_method_display()
        booking = payment.invoice.booking
        payment.delete()
        
        from apps.bookings.services import log_booking_history
        from apps.bookings.choices import BookingHistoryAction
        
        log_booking_history(
            booking=booking,
            action=BookingHistoryAction.PAYMENT_DELETED,
            description=f"Payment of {amount} via {method} was deleted.",
            metadata={"amount": str(amount), "method": method},
            user=user
        )
        
        # Sync the invoice status automatically (e.g. PARTIAL -> UNPAID)
        from apps.invoices.services import update_invoice_status
        update_invoice_status(payment.invoice)
