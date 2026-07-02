from django.db import models
from crm.models import Customer, Passenger
from django.contrib.auth.models import User

class Booking(models.Model):
    STATUS_CHOICES = [
        ('Booked', 'Booked'),
        ('Confirmed', 'Confirmed'),
        ('Cancelled', 'Cancelled'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='bookings')
    passengers = models.ManyToManyField(Passenger, related_name='bookings')
    
    booking_date = models.DateField(auto_now_add=True)
    journey_date = models.DateField()
    
    train_no = models.CharField(max_length=20)
    train_name = models.CharField(max_length=255, blank=True)
    travel_class = models.CharField(max_length=10)
    from_station = models.CharField(max_length=100)
    to_station = models.CharField(max_length=100)
    
    pnr = models.CharField(max_length=20, blank=True, unique=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Booked')
    
    fare_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    conv_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.pnr if self.pnr else 'Booking'} - {self.customer.name}"
