CUSTOMER_TYPES = [
    ('CORPORATE', 'Corporate'),
    ('INDIVIDUAL', 'Individual'),
    ('TRAVEL_AGENT', 'Travel Agent'),
]

GENDER_CHOICES = [
    ('M', 'Male'),
    ('F', 'Female'),
    ('OTHER', 'Other'),
]

IDENTITY_CHOICES = [
    ('PASSPORT', 'Passport'),
    ('AADHAAR', 'Aadhaar'),
    ('PAN', 'PAN'),
    ('DRIVING_LICENSE', 'Driving License'),
    ('OTHER', 'Other'),
]

BOOKING_STATUS_CHOICES = [
    ('DRAFT', 'Draft'),
    ('PENDING', 'Pending'),
    ('ON_HOLD', 'On Hold'),
    ('CONFIRMED', 'Confirmed'),
    ('PARTIALLY_COMPLETED', 'Partially Completed'),
    ('COMPLETED', 'Completed'),
    ('CANCELLED', 'Cancelled'),
]

BOOKING_SERVICE_STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('CONFIRMED', 'Confirmed'),
    ('CANCELLED', 'Cancelled'),
    ('COMPLETED', 'Completed'),
]

PASSENGER_STATUS_CHOICES = [
    ('CONFIRMED', 'Confirmed'),
    ('RAC', 'RAC'),
    ('WAITING', 'Waiting'),
    ('CANCELLED', 'Cancelled'),
    ('NO_SHOW', 'No Show'),
]

BOOKING_SOURCE_CHOICES = [
    ('WALK_IN', 'Walk In'),
    ('WHATSAPP', 'WhatsApp'),
    ('PHONE', 'Phone'),
    ('WEBSITE', 'Website'),
    ('CORPORATE', 'Corporate'),
    ('REFERENCE', 'Reference'),
]

PRIORITY_CHOICES = [
    ('LOW', 'Low'),
    ('MEDIUM', 'Medium'),
    ('HIGH', 'High'),
    ('URGENT', 'Urgent'),
]

