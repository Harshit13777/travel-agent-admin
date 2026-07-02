from django.db import models
from django.contrib.auth.models import User

class Customer(models.Model):
    CUSTOMER_TYPES = [
        ('Individual', 'Individual'),
        ('Corporate', 'Corporate'),
    ]

    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15, unique=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    company_name = models.CharField(max_length=255, blank=True)
    GSTIN = models.CharField(max_length=15, blank=True)
    PAN = models.CharField(max_length=10, blank=True)
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPES, default='Individual')
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_customers')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.phone})"


class Passenger(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    ID_TYPES = [
        ('Aadhaar', 'Aadhaar'),
        ('Passport', 'Passport'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='passengers')
    name = models.CharField(max_length=255)
    dob = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    is_senior = models.BooleanField(default=False)
    id_type = models.CharField(max_length=20, choices=ID_TYPES, blank=True)
    id_number = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.name
