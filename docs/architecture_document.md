# Internal Travel Agency ERP Architecture
**Project Scope:** 2–4 Employees | Manual Entry | No External APIs
**Core Stack:** Django 5.x, PostgreSQL, Django Admin (Unfold Theme)
**Timeline Goal:** 2-Day MVP (Can the office use this on Monday?)
**Core Principle:** Optimize for the **daily office workflow**. Keep It Simple, Stupid (KISS). 

---

## 1. Number Generation Rules
Auto-generated, unique, non-reusable alphanumeric identifiers for all core entities. Format: `[PREFIX]-[YEAR]-[4-DIGIT-SEQUENCE]`
* **Booking Number:** `BK-2026-0001`
* **Invoice Number:** `INV-2026-0001`
* **Credit Note:** `CN-2026-0001`
* **Voucher:** `VCH-2026-0001`

---

## 2. Business Workflow Rules
These rules govern how the ERP engine operates, guaranteeing consistency.

### **Booking Workflow**
* Can be edited freely before invoice generation.
* After invoice generation, operational details can still be changed, but financial totals are strictly locked according to user role.
* Super Admin can unlock a booking if required.
* Cancellation does **not** delete the booking; it changes status and creates financial records (Credit Notes) if applicable.

### **Payment Workflow**
* Multiple payments are allowed against a single invoice.
* Invoice status (Pending, Partially Paid, Paid) is calculated automatically from payments received.

### **Cancellation Workflow**
* A user can cancel one specific service or the entire booking.
* A user can cancel one traveler or multiple travelers (handled via `BookingTraveler` status).
* Credit Note generation is optional based on a business decision (e.g., if the supplier issues a refund).

### **Voucher Workflow**
* Can be redeemed across one or more future bookings.
* Cannot exceed the remaining balance.
* Expired vouchers cannot be used.

---

## 3. Folder Structure
Frozen list of 11 apps.

```text
travel_erp/
├── config/                 
├── apps/                   
│   ├── common/             # Base models, choices, constants
│   ├── accounts/           # User roles
│   ├── customers/          # Corporate clients & Suppliers
│   ├── travelers/          # Passengers (Takes the trip)
│   ├── bookings/           # The central order (Folder) + Service Types
│   ├── invoices/           
│   ├── payments/           
│   ├── credit_notes/       
│   ├── vouchers/           
│   ├── documents/          # Simple attachment models
│   └── reminders/          # Task follow-ups
├── media/                  
├── requirements.txt
└── manage.py
```

---

## 4. Core Model Blueprints

### **Customer vs Traveler vs Supplier**
* **Customer:** The billing entity that pays the invoice.
* **Traveler:** The physical person boarding the flight (Nationality, Identity Number).
* **Supplier:** The vendor providing the inventory (e.g., IRCTC, Makemytrip). Lives in the `customers` app for simplicity.

### **Booking (The Central Folder)**
```text
Booking
  ├── Booking Number (e.g. BK-2026-0012)
  ├── Customer (FK)
  ├── Assigned To (FK User - The owner of the booking)
  ├── Status (Draft, In Progress, Confirmed, Completed, Cancelled)
  └── Notes (TextField)
```

### **Booking Services & Travelers (The Through Model)**
A junction model (`BookingTraveler`) replaces standard M2M to store passenger-specific details (like Seat Number and Baggage).
```text
BookingService (Inline to Booking)
  ├── Service Type (FK)
  ├── Service Provider (e.g., Air India, Taj Hotel)
  ├── Journey Date
  ├── Supplier (FK)
  ├── Reference Number (Agnostic term for PNR, Confirmation No)
  └── Status (Draft, Pending, Confirmed, Waiting, Cancelled, Completed)

BookingTraveler (Junction Model linking BookingService to Traveler)
  ├── Booking Service (FK)
  ├── Traveler (FK)
  ├── Seat Number
  ├── Ticket Status
  ├── Fare
  └── Baggage
```

### **Booking History (Business Events)**
Records only core business events (not Django Admin field changes).
```text
BookingHistory
  ├── Booking (FK)
  ├── Date
  ├── Action (e.g., "Invoice Generated", "Passenger Cancelled")
  └── User (FK)
```

### **Financial Models**
* **Invoice:** `Booking (FK)`, `Invoice Number`, `Invoice Date`, `Due Date`, `Subtotal`, `GST`, `Total`, `Status`.
* **Payment:** `Invoice (FK)`, `Amount`, `Date`, `Method`, `Reference Number`, `Remarks`.
* **Credit Note:** `Booking (FK)`, `Credit Note Number`, `Amount`, `Remaining Amount`, `Reason`, `Issued Date`, `Voucher Created (Bool)`.
* **Voucher:** `Customer (FK)`, `Voucher Number`, `Original Amount`, `Remaining Balance`, `Issued Date`, `Used Date`, `Expiry`, `Status`.

### **Reminder & Documents**
* **Reminder:** `Title`, `Due Date`, `Customer`, `Booking`, `Reminder Type`, `Completed`.
* **Document:** `Customer (Optional)`, `Booking (Optional)`, `Booking Service (Optional)`, `Traveler (Optional)`, `File`, `Document Type`, `Uploaded By`, `Uploaded At`.
