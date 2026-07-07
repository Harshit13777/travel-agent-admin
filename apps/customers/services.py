from django.core.exceptions import ValidationError
from datetime import date
from decimal import Decimal

class CustomerService:
    @staticmethod
    def validate_customer(credit_limit=None, gst_number=None, pan=None):
        """
        Validates business rules for a Customer.
        """
        errors = {}
        
        if credit_limit is not None and credit_limit < Decimal("0.00"):
            errors['credit_limit'] = 'Credit limit cannot be negative.'
            
        if gst_number and len(gst_number) != 15:
            errors['gst_number'] = 'GST number must be 15 characters long.'
            
        if pan and len(pan) != 10:
            errors['pan'] = 'PAN must be exactly 10 characters long.'
            
        if errors:
            raise ValidationError(errors)
