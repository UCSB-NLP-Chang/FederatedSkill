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

See `SKILL.md` main workflow for standard expense claim field mappings.

**Typical Mappings:**
- Person → Employee
- Directory → Employee Directory
- Approval ID → Trip ID
- Approval DB → Trip Approvals
- Amount → Claim Total

**Common Issues:**
- Employee names may have typos or misspellings in claims
- Trip IDs may be referenced by number only (e.g., "12345" vs "TRIP-12345")

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
- Vendor IDs may differ between systems (e.g., vendor master vs AP system)

## Adaptation Checklist

When adapting to a new domain:

1. Identify the person/entity being validated (employee, speaker, vendor, contractor)
2. Identify the directory/registry containing their records
3. Identify the approval reference (trip, session, PO, contract)
4. Map the ID field names (person_id → domain-specific ID)
5. Map the account/payment field (bank_account, payment_account, payment_details)
6. Map the amount field (claim_total, requested_fee, invoice_amount)
7. Adjust regex patterns to match PDF field labels in the new domain
8. Update validation reason messages to use domain-appropriate terminology