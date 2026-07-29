from django.core.exceptions import ValidationError
from datetime import date

class TravelerService:
    @staticmethod
    def validate_traveler(dob=None, passport_issue_date=None, passport_expiry=None):
        """
        Validates business rules for a Traveler.
        """
        errors = {}
        
        if dob and dob > date.today():
            errors['dob'] = 'DOB cannot be in the future.'
            
        if passport_issue_date and passport_expiry and passport_issue_date > passport_expiry:
            errors['passport_issue_date'] = 'Issue date cannot be after expiry date.'
            
        if errors:
            raise ValidationError(errors)
            
    @staticmethod
    def save_traveler(traveler, user=None, change=False):
        TravelerService.validate_traveler(
            dob=traveler.dob,
            passport_issue_date=traveler.passport_issue_date,
            passport_expiry=traveler.passport_expiry
        )
        traveler.save()
        return traveler

    @staticmethod
    def delete_traveler(traveler, user=None):
        traveler.delete()
