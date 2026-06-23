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

## Fleet Maintenance Chargeback Audit

**Source Files:**
- `provider_directory.xlsx` with sheets:
  - `providers`: `provider_id`, `provider_name`, `depot_region`, `payment_account`
  - `aliases`: `provider_id`, `alias_name` (multiple rows per provider)
- `maintenance_orders.json` with nested structure: `depots[].orders[]` containing `order_id`, `provider_id`, `approved_charge`, `lifecycle`
- `maintenance_adjustments.csv` with columns: `order_id`, `amendment_no`, `amended_charge`, `decision`
- `chargeback_packets.pdf` with pages containing: Provider Name, Payment Account, Order ID, Chargeback Total

**Field Mappings:**
```python
FIELD_MAP = {
    "person_id": "provider_id",
    "person_name": "provider_name",
    "directory": "providers",
    "alias_table": "aliases",
    "approval_id": "order_id",
    "approval_amount": "approved_charge",
    "payment_account": "payment_account",
    "requested_amount": "chargeback_total",
    "status_field": "lifecycle"
}
```

**Nested JSON Order Extraction:**
```python
# Flatten nested orders from JSON
orders = []
for depot in data['depots']:
    for order in depot['orders']:
        orders.append(order)
orders_df = pd.DataFrame(orders)
```

**Separate Amendment File Resolution:**
```python
def get_approved_charge(order_id, orders_df, adjustments_df):
    # Check base order
    order = orders_df[orders_df['order_id'] == order_id]
    if order.empty:
        return None, "Invalid Order ID"
    
    order_record = order.iloc[0]
    
    # Check lifecycle status
    if order_record['lifecycle'] == 'closed':
        return None, "Invalid Order ID"
    
    # Find approved amendments
    amendments = adjustments_df[
        (adjustments_df['order_id'] == order_id) &
        (adjustments_df['decision'] == 'approved')
    ]
    
    if amendments.empty:
        return order_record['approved_charge'], None
    
    # Use highest amendment number
    latest = amendments.loc[amendments['amendment_no'].idxmax()]
    return latest['amended_charge'], None
```

**Regex Patterns:**
```python
patterns = {
    "provider_name": r'Provider:\s*(.+?)(?:\n|$)',
    "payment_account": r'Payment Account:\s*(\S+)',
    "order_id": r'Order ID:\s*(\S+)',
    "chargeback_total": r'Chargeback Total:\s*\$?([0-9,]+\.?\d*)',
}
```

**Validation Reasons:**
- "Unknown Provider" (name not in directory or aliases)
- "Invalid Order ID" (order not found or lifecycle is closed)
- "Provider Mismatch" (order assigned to different provider)
- "Account Mismatch" (payment account differs from directory)
- "Amount Mismatch" (chargeback differs from latest approved charge)

**Validation Flow:**
1. Resolve provider name (provider_name → alias table → fuzzy match)
2. Check order exists and lifecycle is approved (not closed)
3. Verify order.provider_id matches resolved provider.provider_id
4. Compare payment_account with directory
5. Get latest approved amendment charge (or base charge if no amendments)
6. Compare chargeback_total with approved charge

## Research Stipend Reconciliation

**Source Files:**
- `recipient_roster.xlsx` with columns: `recipient_code`, `registered_name`, `campus_code`, `bank_token`
- `award_authorizations.csv` with columns: `award_ref`, `recipient_code`, `approved_value`, `campus_code`, `state`
- `award_adjustments.csv` with columns: `award_ref`, `revision_no`, `adjusted_value`, `campus_code`, `state`
- `stipend_packets.pdf` with pages containing: Recipient Name, Bank Token, Award Ref, Requested Value, Campus

**Field Mappings:**
```python
FIELD_MAP = {
    "person_id": "recipient_code",
    "person_name": "registered_name",
    "directory": "recipient_roster",
    "approval_id": "award_ref",
    "approval_amount": "approved_value",
    "payment_account": "bank_token",
    "requested_amount": "requested_value",
    "status_field": "state",
    "location_field": "campus_code"
}
```

**Multi-Field Adjustment Resolution:**
Adjustments can modify multiple fields, not just amounts. Build a complete adjusted record:
```python
def get_adjusted_award(award_ref, awards_df, adjustments_df):
    # Get base award
    award = awards_df[awards_df['award_ref'] == award_ref]
    if award.empty:
        return None, "Invalid Award Ref"
    
    award_record = award.iloc[0].to_dict()
    
    # Check state (archived awards are invalid)
    if award_record['state'] == 'archived':
        return None, "Invalid Award Ref"
    
    # Find approved adjustments
    approved_adj = adjustments_df[
        (adjustments_df['award_ref'] == award_ref) &
        (adjustments_df['state'] == 'approved')
    ]
    
    if not approved_adj.empty:
        # Use highest revision number
        latest = approved_adj.loc[approved_adj['revision_no'].idxmax()]
        # Override with adjusted values (amount, campus, etc.)
        award_record['approved_value'] = latest['adjusted_value']
        award_record['campus_code'] = latest['campus_code']
    
    return award_record, None
```

**Regex Patterns:**
```python
patterns = {
    "recipient_name": r'Recipient:\s*(.+?)(?:\n|$)',
    "bank_token": r'Bank Token:\s*(\S+)',
    "award_ref": r'Award Ref:\s*(\S+)',
    "requested_value": r'Requested Value:\s*\$?([0-9,]+\.?\d*)',
    "campus_code": r'Campus:\s*(\S+)',
}
```

**Validation Reasons:**
- "Unknown Recipient" (name not in roster)
- "Invalid Award Ref" (award not found or state is archived)
- "Recipient Mismatch" (award belongs to different recipient)
- "Account Mismatch" (bank token differs from roster)
- "Campus Mismatch" (campus differs from adjusted/base award)
- "Amount Mismatch" (requested value differs from approved)

**Validation Flow:**
1. Fuzzy match recipient name → get recipient record
2. Check award exists and state is active (not archived)
3. Get adjusted award record (apply approved adjustments for amount AND campus)
4. Verify award.recipient_code matches recipient.recipient_code
5. Compare bank_token with roster
6. Compare campus_code with adjusted award (not base award)
7. Compare requested_value with adjusted approved_value

**Key Insight:** Campus codes can be modified by adjustments. Always validate against the adjusted campus, not the base authorization campus.

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

| Generic Concept | Expense Claims | Speaker Honorariums | Clinic Shift Claims | Field Service Audit | Fleet Maintenance | Research Stipends | Vendor Invoices |
|----------------|----------------|---------------------|---------------------|---------------------|-------------------|-------------------|-----------------|
| Person | Employee | Speaker | Clinician | Contractor | Provider | Recipient | Vendor |
| Person ID | `employee_id` | `speaker_id` | `clinician_id` | `contractor_id` | `provider_id` | `recipient_code` | `vendor_id` |
| Directory | Employee Directory | Speaker Registry | Clinician Directory | Contractor Directory | Provider Directory | Recipient Roster | Vendor Master |
| Alias Table | No | No | No | Yes (contractor aliases) | Yes (provider aliases) | No | Sometimes (DBA names) |
| External Ref | (none) | (none) | `shift_ref` | (none) | (none) | (none) | PO Number |
| Approval ID | `trip_id` | `approval_code` | `shift_code_internal` | `work_order_id` | `order_id` | `award_ref` | `po_number` |
| Approval DB | Trip Approvals | Session Approvals | Shift Authorizations | Work Orders | Maintenance Orders | Award Authorizations | Purchase Orders |
| Revision Chain | No | No | No | Yes (work order revisions) | Yes (amendments) | Yes (award adjustments) | Sometimes |
| Status Check | No | No | No | Yes (active/closed) | Yes (lifecycle) | Yes (active/archived) | Sometimes |
| Location Field | (none) | (none) | `unit_code` | `site_zone` | `depot_region` | `campus_code` | (none) |
| Location Adjusted | No | No | No | Sometimes | No | Yes | No |
| Payment Account | `bank_account` | `payment_account` | `payout_account` | `payment_account` | `payment_account` | `bank_token` | `payment_details` |
| Amount | `claim_total` | `requested_fee` | `requested_pay` | `billed_amount` | `chargeback_total` | `requested_value` | `invoice_amount` |
| Crosswalk | No | No | Yes (shift_ref → internal) | No | No | No | Sometimes |
