from django.core.exceptions import ValidationError
from apps.invoices.choices import InvoiceStatus

class PaymentService:
    @staticmethod
    def validate_payment(invoice):
        """
        Validates if a payment can be made for the given invoice.
        """
        if invoice and invoice.status == InvoiceStatus.CLOSED:
            raise ValidationError("Cannot add or edit payments for a CLOSED invoice.")

    @staticmethod
    def save_payment(payment, user, change):
        PaymentService.validate_payment(payment.invoice)
        payment.save()
        
        from apps.bookings.services import log_booking_history
        action = "PAYMENT_UPDATED" if change else "PAYMENT_ADDED"
        log_booking_history(
            booking=payment.invoice.booking,
            action=action,
            description=f"Payment of {payment.amount} via {payment.get_method_display()} was {'updated' if change else 'added'}.",
            user=user
        )
        return payment

    @staticmethod
    def delete_payment(payment, user):
        PaymentService.validate_payment(payment.invoice)
        amount = payment.amount
        method = payment.get_method_display()
        booking = payment.invoice.booking
        payment.delete()
        
        from apps.bookings.services import log_booking_history
        log_booking_history(
            booking=booking,
            action="PAYMENT_DELETED",
            description=f"Payment of {amount} via {method} was deleted.",
            user=user
        )
