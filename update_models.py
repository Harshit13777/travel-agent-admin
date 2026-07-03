import os

# mapping of old choice lists to new Enum classes
replacements = {
    "GENDER_CHOICES": "Gender",
    "IDENTITY_CHOICES": "IdentityType",
    "CUSTOMER_TYPES": "CustomerType",
    "INVOICE_TYPE_CHOICES": "InvoiceType",
    "INVOICE_STATUS_CHOICES": "InvoiceStatus",
    "PAYMENT_METHOD_CHOICES": "PaymentMethod",
    "VOUCHER_STATUS_CHOICES": "VoucherStatus",
}

for app in ['customers', 'travelers', 'payments', 'vouchers', 'credit_notes']:
    model_path = f"apps/{app}/models.py"
    if not os.path.exists(model_path):
        continue
    
    with open(model_path, 'r') as f:
        content = f.read()

    # 1. Update imports
    for old, new in replacements.items():
        content = content.replace(old, new)
        content = content.replace(f"choices={new}", f"choices={new}.choices")
        content = content.replace(f"default='TAX'", f"default={new}.TAX")
        content = content.replace(f"default='M'", f"default={new}.MALE")
        content = content.replace(f"default='PASSPORT'", f"default={new}.PASSPORT")
        content = content.replace(f"default='CORPORATE'", f"default={new}.CORPORATE")
        content = content.replace(f"default='DRAFT'", f"default={new}.DRAFT")
        content = content.replace(f"default='CASH'", f"default={new}.CASH")
        content = content.replace(f"default='ACTIVE'", f"default={new}.ACTIVE")
        
    with open(model_path, 'w') as f:
        f.write(content)
