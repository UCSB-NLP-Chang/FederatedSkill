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

## Clinic Shift Claims Validation

**Source Files:**
- `clinician_directory.xlsx` with columns: `clinician_id`, `clinician_name`, `unit_code`, `payout_account`
- `shift_crosswalk.csv` with columns: `shift_ref` (external), `shift_code_internal` (internal)
- `shift_authorizations.csv` with columns: `shift_code_internal`, `approved_pay`, `clinician_id`
- `shift_claims.pdf` with pages containing: Clinician Name, Payout Account, Shift Ref, Requested Pay

**Field Mappings:**
```python
FIELD_MAP = {
    "person_id": "clinician_id",
    "person_name": "clinician_name",
    "directory": "clinician_directory",
    "external_ref": "shift_ref",
    "approval_id": "shift_code_internal",
    "approval_amount": "approved_pay",
    "payment_account": "payout_account",
    "requested_amount": "requested_pay"
}
```

**Crosswalk Resolution:**
```python
# Build crosswalk: external code -> internal code
crosswalk = {}
for _, row in shift_crosswalk_df.iterrows():
    crosswalk[row['shift_ref']] = row['shift_code_internal']

# Resolve external reference to internal code
shift_ref = claim.get('shift_ref')  # e.g., "SHIFT-A1"
if shift_ref not in crosswalk:
    return False, "Invalid Shift Code", None
internal_code = crosswalk[shift_ref]  # e.g., "INT-5101"
```

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

**Validation Reasons:**
- "Unknown Clinician" (name not in directory)
- "Invalid Shift Code" (shift_ref not in crosswalk)
- "Clinician Mismatch" (authorization assigned to different clinician)
- "Account Mismatch" (payout account differs from directory)
- "Amount Mismatch" (requested pay differs from approved)

**Validation Flow with Crosswalk:**
1. Fuzzy match clinician name → get clinician record
2. Check shift_ref exists in crosswalk → resolve to internal code
3. Look up authorization by internal code
4. Verify authorization.clinician_id matches clinician.clinician_id
5. Compare payout_account with directory
6. Compare requested_pay with approved_pay

## Field Service Work Order Audit

**Source Files:**
- `contractor_directory.xlsx` with sheets:
  - `contractors`: `contractor_id`, `legal_name`, `site_zone`, `payment_account`
  - `aliases`: `contractor_id`, `alias_name` (multiple rows per contractor)
- `work_orders.csv` with columns: `work_order_id`, `contractor_id`, `approved_amount`, `site_zone`, `status`
- `work_order_revisions.csv` with columns: `work_order_id`, `revision`, `revised_amount`, `site_zone`, `approval_state`
- `service_packets.pdf` with pages containing: Contractor Name, Payment Account, Work Order ID, Billed Amount

**Field Mappings:**
```python
FIELD_MAP = {
    "person_id": "contractor_id",
    "person_name": "contractor_name",
    "directory": "contractors",
    "alias_table": "aliases",
    "approval_id": "work_order_id",
    "approval_amount": "approved_amount",
    "payment_account": "payment_account",
    "requested_amount": "billed_amount",
    "status_field": "status"
}
```

**Alias Resolution:**
```python
# Build alias lookup: alias_name -> contractor_id
alias_lookup = {}
for _, row in aliases_df.iterrows():
    alias_lookup[row['alias_name'].strip().lower()] = row['contractor_id']

# Resolve contractor name
def resolve_contractor(name, contractors_df, alias_lookup):
    name_lower = name.strip().lower()
    # 1. Try exact match on legal_name
    match = contractors_df[contractors_df['legal_name'].str.lower() == name_lower]
    if not match.empty:
        return match.iloc[0]
    # 2. Try alias table
    if name_lower in alias_lookup:
        cid = alias_lookup[name_lower]
        return contractors_df[contractors_df['contractor_id'] == cid].iloc[0]
    # 3. Try fuzzy match on legal_name and aliases
    # ... fuzzy matching logic
    return None
```

**Revision Chain Resolution:**
```python
def get_approved_amount(work_order_id, work_orders_df, revisions_df):
    # Check base work order
    wo = work_orders_df[work_orders_df['work_order_id'] == work_order_id]
    if wo.empty:
        return None, "Invalid Work Order"
    
    wo_record = wo.iloc[0]
    
    # Check status
    if wo_record['status'] == 'closed':
        return None, "Invalid Work Order"  # Closed work orders are invalid
    
    # Find all approved revisions
    wo_revisions = revisions_df[
        (revisions_df['work_order_id'] == work_order_id) &
        (revisions_df['approval_state'] == 'approved')
    ]
    
    if wo_revisions.empty:
        return wo_record['approved_amount'], None
    
    # Use highest revision number
    latest = wo_revisions.loc[wo_revisions['revision'].idxmax()]
    return latest['revised_amount'], None
```

**Regex Patterns:**
```python
patterns = {
    "contractor_name": r'Contractor:\s*(.+?)(?:\n|$)',
    "payment_account": r'Payment Account:\s*(\S+)',
    "work_order_id": r'Work Order:\s*(\S+)',
    "billed_amount": r'Amount:\s*\$?([0-9,]+\.?\d*)',
}
```

**Validation Reasons:**
- "Unknown Contractor" (name not in directory or aliases)
- "Invalid Work Order" (work order not found or status is closed)
- "Contractor Mismatch" (work order assigned to different contractor)
- "Account Mismatch" (payment account differs from directory)
- "Amount Mismatch" (billed amount differs from latest approved)

**Validation Flow:**
1. Resolve contractor name (legal_name → alias table → fuzzy match)
2. Check work order exists and status is active
3. Verify work order.contractor_id matches resolved contractor.contractor_id
4. Compare payment_account with directory
5. Get latest approved revision amount (or base amount if no revisions)
6. Compare billed_amount with approved amount

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

| Generic Concept | Expense Claims | Speaker Honorariums | Clinic Shift Claims | Field Service Audit | Vendor Invoices |
|----------------|----------------|---------------------|-------------------|---------------------|-----------------|
| Person | Employee | Speaker | Clinician | Contractor | Vendor |
| Person ID | `employee_id` | `speaker_id` | `clinician_id` | `contractor_id` | `vendor_id` |
| Directory | Employee Directory | Speaker Registry | Clinician Directory | Contractor Directory | Vendor Master |
| Alias Table | No | No | No | Yes (contractor aliases) | Sometimes (DBA names) |
| External Ref | (none) | (none) | `shift_ref` | (none) | PO Number |
| Approval ID | `trip_id` | `approval_code` | `shift_code_internal` | `work_order_id` | `po_number` |
| Approval DB | Trip Approvals | Session Approvals | Shift Authorizations | Work Orders | Purchase Orders |
| Revision Chain | No | No | No | Yes (work order revisions) | Sometimes |
| Status Check | No | No | No | Yes (active/closed) | Sometimes |
| Payment Account | `bank_account` | `payment_account` | `payout_account` | `payment_account` | `payment_details` |
| Amount | `claim_total` | `requested_fee` | `requested_pay` | `billed_amount` | `invoice_amount` |
| Crosswalk | No | No | Yes (shift_ref → internal) | No | Sometimes |
