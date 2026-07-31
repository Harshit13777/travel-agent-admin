# TAMS (Travel Agent Management System) Architecture & Rules

This document outlines the core architecture, data flows, and strict financial business rules implemented across the travel agent panel.

## 1. Architectural Philosophy

### The Service Layer Pattern

All critical business logic, validations, and database mutations are strictly isolated in `services.py` files within each app (e.g., `apps/invoices/services.py`, `apps/payments/services.py`).

- **Admin classes** (`admin.py`) are strictly responsible for UI presentation, routing, and passing requests to the service layer.
- **Models** (`models.py`) are strictly responsible for data structure and calculated properties (e.g., `@property def balance_due`).
- **No business logic** is ever executed directly inside an Admin `save_model` or `clean` method without delegating to the service layer.

### The "Boomerang" UI Pattern

To keep agents in their workflow, the system relies heavily on "boomerang" redirects.

- When an agent adds, edits, or deletes a child object (like a Service, Payment, or Cancellation) from a parent object's screen (like a Booking or Invoice), the system intercepts the standard Django redirect and instantly "boomerangs" the agent back to the parent object's detail view.

---

## 2. Core Data Flow

1. **Customer**: The root entity.
2. **Booking**: A trip for a customer. Contains overall status and journey dates.
3. **Booking Service**: A specific component of the trip (Flight, Hotel, Visa). Contains supplier costs and service charges.
4. **Booking Traveler**: The actual passenger attached to a specific service.
5. **Invoice**: A frozen financial snapshot of the Booking at a specific point in time.
6. **Invoice Line & Traveler**: The immutable snapshot of the `BookingService` and `BookingTraveler`.
7. **Financial Operations**: `Payments`, `Credit Allocations`, and `BookingCancellations` are processed directly against the **Invoice** (or its snapshot lines), never the live booking.

---

## 3. Financial Statuses & Strict Locks

The integrity of the system relies on the `InvoiceStatus`. This status is the ultimate source of truth and dictates what operations are allowed across the entire system via the centralized `can_modify_invoice()` service.

> [!CAUTION]
> The Payment Status (Paid, Unpaid, Partial) is a **dynamic calculation** based on `balance_due`. It is never saved to the database to prevent sync corruption with the actual Invoice Status.

### Status: `ISSUED` (Open)

- **State**: The invoice is active and expecting financial operations.
- **Allowed**: Adding/Editing/Deleting Payments, Allocating Credit Notes, Processing Passenger Cancellations.
- **Blocked**: Cannot generate a new Credit Note from an overpayment (invoice must be closed first).

### Status: `CLOSED` (Locked)

- **State**: The financial ledger for this invoice is permanently sealed.
- **Allowed**: Generating a single Credit Note (if there is an overpayment). Re-opening the invoice (if no generated credit notes have been allocated).
- **Blocked**: **Strictly no modifications.** Cannot add/edit/delete payments. Cannot apply credit notes. Cannot process cancellations.

### Status: `VOID` (Dead)

- **State**: The invoice and all its transactions are treated as if they never happened.
- **Allowed**: Generating a brand new invoice for the booking.
- **Blocked**: **Strictly no modifications.** Cannot be closed or re-opened. Cannot add payments or credits.
- **Cascade Rule**: When an invoice is `VOIDED`, the system automatically **deletes all passenger cancellation records** attached to it to prevent phantom refunds. The passenger returns to "Active" status on the booking screen.

---

## 4. Cross-App Business Rules

### Cancellations

- Cancellations are attached to the **Invoice Snapshot** (`InvoiceLineTraveler`), not the live booking passenger.
- If Invoice A is `VOIDED`, its cancellations are ignored/deleted. If Invoice B is generated, the passenger gets a brand new snapshot, allowing them to be cancelled properly on the active invoice.
- **Refund Limits**: The `supplier_refund` and `service_charge_refund` cannot exceed the original amounts recorded on the invoice snapshot.
- Only **one active cancellation** is allowed per passenger per invoice.

### Credit Notes

- **Generation**: Can only be generated automatically by the system from a `CLOSED` invoice that has a negative balance (overpayment).
- **Allocation**: Can only be applied to an `ISSUED` invoice that belongs to the **exact same Customer** as the originating credit note.
- **Dependency**: If an invoice generated a Credit Note, and that Credit Note was used to pay for a different invoice, the original invoice **cannot be re-opened or voided** until the allocation is removed.

### UI Context Filtering

To prevent user error and massive dropdown lists, the system intelligently filters Foreign Keys based on the URL context:

- **Passenger Selection**: When adding a passenger to a Booking Service, the dropdown exclusively shows travelers belonging to the Booking's Customer.
- **Credit Note Selection**: When applying a Credit Note to an Invoice, the dropdown exclusively shows active Credit Notes belonging to the Invoice's Customer.
- **Hidden Contexts**: If a user navigates to "Add Payment" directly from an Invoice screen, the `Invoice` dropdown is hidden to prevent accidental reassignment.

---

## 5. The Chronological Developer Workflow (Lifecycle Summary)

To summarize the entire financial flow for a developer building on top of this architecture:

1. **Draft Phase**: When a `Booking` is first created, there is no invoice. All operations (adding services, editing passenger prices, changing suppliers) are fully executable and unlocked.
2. **Invoice Generation**: When the agent generates an invoice, the system takes a snapshot of the financials. The `Booking` record is now **Locked** in the database. Financial fields on the live booking (like passenger prices) are locked from being edited.
3. **Open Invoice Phase**: The new invoice starts with the status `ISSUED` (Open). At this point, the invoice is ready for operations: you can add Payments, allocate existing Credit Notes, or process Passenger Cancellations.
4. **Closing the Invoice**: Once all transactions are completed, the agent clicks "Close Invoice". The status becomes `CLOSED`. The invoice is now permanently locked, and no further financial operations (payments, allocations, cancellations) can be performed on it.
5. **Voiding an Invoice**:
   - You can only `VOID` an invoice if it is completely untouched by external financials. This means: **no active payments**, **no applied credit notes**, and **no allocated credit notes that were generated by this invoice**.
   - When an invoice is `VOIDED`, all **cancellation refund records** attached to its snapshot lines are **permanently deleted** from the database to prevent phantom refunds. _(Note: This does NOT delete the actual passengers, only their cancellation records)._
   - The `Booking` is completely **unlocked** in the database. The agent can now freely edit the service/passenger prices again, and eventually generate a brand new invoice to restart the cycle.

---

## 6. Comprehensive Business Logic (Service Layer Reference)

All business rules below are strictly enforced in the respective `services.py` layers.

### Bookings (`apps/bookings/services.py`)

- **Modification**: A booking and its services/passengers can only be modified or deleted if `booking.locked_at` is `None`.
- **Locking**: Generating an invoice automatically sets `locked_at`, preventing any further changes to live financial fields.

### Invoices (`apps/invoices/services.py`)

- **Generation (`generate_invoice`)**: Reads live booking data and clones it into immutable `InvoiceLine` and `InvoiceLineTraveler` records. Calculates GST and final totals. Sets booking to locked.
- **Closing (`close_invoice`)**: Locks the invoice financials. Blocks if the invoice is `VOID`.
- **Re-opening (`reopen_invoice`)**:
  - Blocks if the invoice is `VOID`.
  - If a Credit Note was automatically generated by this invoice, the system checks it. If that Credit Note has been used (allocated), the reopen is **blocked**. If unused, the Credit Note is automatically **deleted**.
- **Voiding (`cancel_invoice`)**:
  - **Blocks** if there are active payments attached to the invoice.
  - **Blocks** if there are credit notes applied to this invoice.
  - **Blocks** if it generated a Credit Note that is actively allocated elsewhere.
  - **Actions**: Sets status to `VOID`. **Deletes all passenger cancellation refund records** attached to it _(does NOT delete the passengers themselves)_. **Unlocks** the original booking so a new invoice can be generated.

### Payments (`apps/payments/services.py`)

- **Validation (`validate_payment`)**:
  - **Blocks** if the target invoice is `VOID` or `CLOSED`.
  - **Blocks** if the payment amount exceeds the invoice's dynamic `balance_due`.

### Credit Notes (`apps/credit_notes/services.py`)

- **Generation (`generate_from_overpayment`)**: Can only be triggered on a `CLOSED` invoice that has a negative balance (e.g. they paid $500, but the total was $400).
- **Allocation (`allocate_credit`)**:
  - **Source Rule**: The Credit Note's originating invoice **must be CLOSED**.
  - **Target Rule**: The invoice receiving the credit **must be ISSUED** (Not VOID, Not CLOSED).
  - **Identity Rule**: The Customer of the Credit Note and the Customer of the target invoice **must be identical**.
  - **Math Rule**: The allocation amount cannot exceed the Credit Note's `remaining_amount` and cannot exceed the target invoice's `balance_due`.

### Cancellations (`apps/cancellations/services.py`)

- **Validation**:
  - Centralized check: `can_modify_invoice(invoice)`. **Blocks** any cancellation activity on `CLOSED` or `VOID` invoices.
  - **Blocks** if `supplier_refund` exceeds the passenger's original `supplier_cost`.
  - **Blocks** if `service_charge_refund` exceeds the passenger's original `service_charge`.
  - Only exactly **one** cancellation record is permitted per `InvoiceLineTraveler`.
- **Operations (`cancel_passengers`, `update_cancellation`, `delete_cancellation`)**: Fully wrapped in atomic transactions to ensure no partial refunds are ever recorded.
