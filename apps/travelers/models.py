from datetime import date
from django.db import models
from django.core.exceptions import ValidationError
from apps.common.models import AuditModel
from apps.customers.models import Customer
from apps.common.choices import Gender, IdentityType

class Traveler(AuditModel):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='travelers')
    full_name = models.CharField(max_length=200, db_index=True)
    dob = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=15, blank=True, db_index=True)
    email = models.EmailField(blank=True, db_index=True)
    nationality = models.CharField(max_length=50, default='Indian')
    
    gender = models.CharField(max_length=10, choices=Gender.choices, default=Gender.MALE)
    primary_identity_type = models.CharField(max_length=50, choices=IdentityType.choices, default=IdentityType.AADHAAR)
    primary_identity_number = models.CharField(max_length=50, blank=True, db_index=True)
    
    passport_number = models.CharField(max_length=50, blank=True, db_index=True)
    passport_issue_date = models.DateField(null=True, blank=True)
    passport_expiry = models.DateField(null=True, blank=True)
    
    meal_preference = models.CharField(max_length=50, blank=True)
    special_request = models.TextField(blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        verbose_name = "Traveler"
        verbose_name_plural = "Travelers"

    def __str__(self):
        return f"{self.full_name} ({self.customer.name})"

    def clean(self):
        if self.dob and self.dob > date.today():
            raise ValidationError({'dob': 'DOB cannot be in the future.'})
        if self.passport_issue_date and self.passport_expiry and self.passport_issue_date > self.passport_expiry:
             raise ValidationError({'passport_issue_date': 'Issue date cannot be after expiry date.'})
