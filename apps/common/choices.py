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
    ('CONFIRMED', 'Confirmed'),
    ('CANCELLED', 'Cancelled'),
    ('COMPLETED', 'Completed'),
]

BOOKING_SERVICE_STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('CONFIRMED', 'Confirmed'),
    ('CANCELLED', 'Cancelled'),
    ('COMPLETED', 'Completed'),
]

PASSENGER_STATUS_CHOICES = [
    ('WAITING', 'Waiting'),
    ('CONFIRMED', 'Confirmed'),
    ('CANCELLED', 'Cancelled'),
    ('CHECKED_IN', 'Checked In'),
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

INVOICE_TYPE_CHOICES = [
    ('TAX', 'Tax Invoice'),
    ('PROFORMA', 'Proforma'),
]

INVOICE_STATUS_CHOICES = [
    ('DRAFT', 'Draft'),
    ('UNPAID', 'Unpaid'),
    ('PARTIAL', 'Partially Paid'),
    ('PAID', 'Paid'),
    ('CANCELLED', 'Cancelled'),
]

PAYMENT_METHOD_CHOICES = [
    ('CASH', 'Cash'),
    ('BANK_TRANSFER', 'Bank Transfer'),
    ('UPI', 'UPI'),
    ('CREDIT_CARD', 'Credit Card'),
    ('CHEQUE', 'Cheque'),
]

VOUCHER_STATUS_CHOICES = [
    ('ACTIVE', 'Active'),
    ('USED', 'Used'),
    ('EXPIRED', 'Expired'),
    ('CANCELLED', 'Cancelled'),
]


