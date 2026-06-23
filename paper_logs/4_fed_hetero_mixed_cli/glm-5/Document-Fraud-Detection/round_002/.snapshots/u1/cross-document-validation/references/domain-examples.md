# Domain Examples for Payment Validation

Concrete field mappings for adapting the validation pattern to different domains.

## Speaker Honorarium Validation

**Source Files:**
- `speaker_registry.xlsx` with columns: `speaker_id`, `speaker_name`, `organization_code`, `payment_account`
- `session_approvals.csv` with columns: `approval_code`, `approved_fee`, `speaker_id`
- `honorarium_requests.pdf` with pages containing: Speaker, Organization, Payment Account, Approval Code, Requested Fee

**Field Mappings:**
```python
FIELD_MAP = {
    "person_id": "speaker_id",
    "person_name": "speaker_name",
    "directory": "speaker_registry",
    "approval_id": "approval_code",
    "approval_amount": "approved_fee",
    "payment_account": "payment_account",
    "requested_amount": "requested_fee"
}
```

**Regex Patterns:**
```python
patterns = {
    "speaker_name": r'Speaker:\s*(.+?)(?:\n|$)',
    "organization": r'Organization:\s*(.+?)(?:\n|$)',
    "payment_account": r'Payment Account:\s*(\S+)',
    "approval_code": r'Approval Code:\s*(\S+)',
    "requested_fee": r'Requested Fee:\s*\$?([0-9,]+\.?\d*)',
}
```

**Validation Reasons:**
- "Unknown Speaker" (name not in registry)
- "Invalid Approval Code" (code not found)
- "Speaker Mismatch" (approval belongs to different speaker)
- "Account Mismatch" (payment account differs from registry)
- "Fee Mismatch" (requested amount differs from approved)

## Expense Claims Validation

**Source Files:**
- `employee_directory.xlsx` with columns: `employee_id`, `employee_name`, `bank_account`
- `trip_approvals.csv` with columns: `trip_id`, `approved_amount`, `employee_id`
- `expense_claims.pdf` with pages containing: Employee Name, Bank Account, Trip ID, Claim Total

**Field Mappings:**
```python
FIELD_MAP = {
    "person_id": "employee_id",
    "person_name": "employee_name",
    "directory": "employee_directory",
    "approval_id": "trip_id",
    "approval_amount": "approved_amount",
    "payment_account": "bank_account",
    "requested_amount": "claimed_amount"
}
```

**Validation Reasons:**
- "Unknown Employee" (name not in directory)
- "Invalid Trip ID" (trip not found)
- "Traveler Mismatch" (trip belongs to different employee)
- "Account Mismatch" (bank account differs from directory)
- "Amount Mismatch" (claimed amount differs from approved)

## Vendor Invoice Validation

**Typical Mappings:**
- Person → Vendor
- Directory → Vendor Master
- Approval ID → PO Number
- Approval DB → Purchase Orders
- Amount → Invoice Amount

**Common Issues:**
- Vendor names may have DBA ("Doing Business As") variations
- PO numbers may have prefixes/suffixes in the PDF (e.g., "PO# 12345" vs "12345" in database)

## Domain Mapping Table

| Generic Concept | Expense Claims | Speaker Honorariums | Vendor Invoices |
|----------------|----------------|---------------------|-----------------|
| Person | Employee | Speaker | Vendor |
| Person ID | `employee_id` | `speaker_id` | `vendor_id` |
| Directory | Employee Directory | Speaker Registry | Vendor Master |
| Approval ID | `trip_id` | `approval_code` | `po_number` |
| Approval DB | Trip Approvals | Session Approvals | Purchase Orders |
| Payment Account | `bank_account` | `payment_account` | `payment_details` |
| Amount | `claim_total` | `requested_fee` | `invoice_amount` |
