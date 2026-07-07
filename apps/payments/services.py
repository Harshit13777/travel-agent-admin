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
