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

## Clinic Shift Claim Validation

**Source Files:**
- `clinician_directory.xlsx`: `clinician_id`, `clinician_name`, `unit_code`, `payout_account`
- `shift_crosswalk.csv`: `shift_ref`, `shift_code_internal`
- `shift_authorizations.csv`: `shift_code_internal`, `approved_pay`, `clinician_id`
- `claims.pdf`: Clinician, Unit, Payout Account, Shift Ref, Requested Pay

**Workflow Adaptation:**
1. Resolve `Shift Ref` → `shift_code_internal` via crosswalk. If missing → "Invalid Shift Code".
2. Lookup `shift_code_internal` in authorizations.
3. Match `clinician_name` (fuzzy) → `clinician_id`.
4. Validate: `auth.clinician_id == matched.clinician_id`, `claim.account == dir.account`, `claim.pay == auth.approved_pay`.

**Regex Patterns:**
```python
patterns = {
    "clinician_name": r'Clinician:\s*(.+?)(?:\n|$)',
    "unit": r'Unit:\s*(.+?)(?:\n|$)',
    "payout_account": r'Payout Account:\s*(\S+)',
    "shift_ref": r'Shift Ref:\s*(\S+)',
    "requested_pay": r'Requested Pay:\s*\$?([0-9,]+\.?\d*)',
}
```

## Field Service Work Order Audit

**Source Files:**
- `contractor_directory.xlsx` with sheets: `contractors` (`contractor_id`, `legal_name`, `site_zone`, `payment_account`) and `aliases` (`contractor_id`, `alias_name`)
- `work_orders.csv`: `work_order_id`, `contractor_id`, `approved_amount`, `site_zone`, `status`
- `work_order_revisions.csv`: `work_order_id`, `revision`, `revised_amount`, `site_zone`, `approval_state`
- `billing_packets.pdf`: Contractor, Service Zone, Payment Account, Work Order, Billed Total

**Workflow Adaptation:**
1. Load `contractors` and `aliases` sheets. Build `name_lower → contractor_id` map from both.
2. Load `work_orders.csv`. Filter `status == 'active'`.
3. Load `work_order_revisions.csv`. Filter `approval_state == 'approved'`. For each `work_order_id`, keep the row with the highest `revision` number.
4. Parse PDF. Match contractor name via aliases first, then fuzzy match (90%).
5. Validate:
   - Unknown Contractor (no match)
   - Invalid Work Order (status ≠ active or missing)
   - Contractor Mismatch (WO's `contractor_id` ≠ matched `contractor_id`)
   - Account Mismatch (claim account ≠ directory account)
   - Amount Mismatch (|billed - resolved_amount| > 0.01)

**Regex Patterns:**
```python
patterns = {
    "contractor_name": r'Contractor:\s*(.+?)(?:\n|$)',
    "service_zone": r'Service Zone:\s*(.+?)(?:\n|$)',
    "payment_account": r'Payment Account:\s*(\S+)',
    "work_order_id": r'Work Order:\s*(\S+)',
    "billed_total": r'Billed Total:\s*\$?([0-9,]+\.?\d*)',
}
```