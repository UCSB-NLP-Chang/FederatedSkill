# Domain Examples for Payment Validation

Concrete field mappings for adapting the validation pattern to different domains.

## Fleet Maintenance Chargeback Audit

**Source Files:**
- `provider_directory.xlsx` with sheets:
  - `providers`: `provider_id`, `provider_name`, `depot_region`, `payment_account`
  - `aliases`: `provider_id`, `alias_name` (DBA/name variants like "Atlas Fleet Svcs")
- `depots.json`: Nested structure with depots containing orders:
  ```json
  {
    "depots": [
      {
        "depot_code": "D-NORTH",
        "orders": [
          {"order_id": "MO-9001", "provider_id": "P801", "approved_charge": 1800.0, "lifecycle": "approved"}
        ]
      }
    ]
  }
  ```
- `amendments.csv`: `order_id`, `amendment_no`, `amended_charge`, `decision` (approved/rejected)
- `chargeback_packets.pdf`: pages containing Provider, Depot, Payment Account, Order ID, Chargeback Total

**Field Mappings:**
```python
FIELD_MAP = {
    "person_id": "provider_id",
    "person_name": "provider_name",
    "directory": "providers",
    "alias_sheet": "aliases",
    "approval_id": "order_id",
    "approval_amount": "approved_charge",
    "payment_account": "payment_account",
    "requested_amount": "chargeback_total",
    "status_field": "lifecycle",
    "amendment_id": "order_id",
    "amendment_amount": "amended_charge"
}
```

**Flattening Nested JSON Approvals:**
```python
import json

# Load nested depot structure
with open('depots.json') as f:
    depots_data = json.load(f)

# Flatten into order_id → order record lookup
orders_by_id = {}
for depot in depots_data['depots']:
    depot_code = depot['depot_code']
    for order in depot['orders']:
        orders_by_id[order['order_id']] = {
            **order,
            'depot_code': depot_code  # Denormalize for validation
        }
```

**Amendment Resolution (with Decision Check):**
```python
# Amendments may be rejected; only apply approved amendments
amendments_df = pd.read_csv('amendments.csv')
amendments_df = amendments_df[amendments_df['decision'] == 'approved']

# Build effective amount lookup
amendment_by_order = {}
for _, row in amendments_df.iterrows():
    order_id = row['order_id']
    # Higher amendment_no = more recent
    if order_id not in amendment_by_order or row['amendment_no'] > amendment_by_order[order_id]['amendment_no']:
        amendment_by_order[order_id] = row

# Resolve effective amount
def get_effective_amount(order_id, base_amount):
    if order_id in amendment_by_order:
        return amendment_by_order[order_id]['amended_charge']
    return base_amount
```

**Status Validation (Lifecycle Field):**
```python
order = orders_by_id.get(order_id)
if not order:
    return False, "Invalid Order ID", provider
if order.get('lifecycle', '').lower() != 'approved':
    return False, "Inactive Order", provider  # closed, cancelled, etc.
```

**Regex Patterns:**
```python
patterns = {
    "provider_name": r'Provider:\s*(.+?)(?:\n|$)',
    "depot": r'Depot:\s*(.+?)(?:\n|$)',
    "payment_account": r'Payment Account:\s*(\S+)',
    "order_id": r'Order ID:\s*(\S+)',
    "chargeback_total": r'Chargeback Total:\s*\$?([0-9,]+\.?\d*)',
}
```

**Validation Reasons:**
- "Unknown Provider" (name not in directory or aliases)
- "Invalid Order ID" (MO-XXXX not found in any depot)
- "Inactive Order" (order lifecycle is 'closed', 'cancelled', etc.)
- "Provider Mismatch" (order assigned to different provider_id)
- "Account Mismatch" (payment account differs from directory)
- "Amount Mismatch" (chargeback differs from approved/amended amount)

## Field Service Work Order Audit

**Source Files:**
- `contractor_directory.xlsx` with sheets:
  - `contractors`: `contractor_id`, `legal_name`, `site_zone`, `payment_account`
  - `aliases`: `contractor_id`, `alias_name` (DBA/name variants)
- `work_orders.csv`: `work_order_id`, `contractor_id`, `approved_amount`, `site_zone`, `status` (active/closed)
- `amendments.csv`: `work_order_id`, `revision`, `revised_amount`, `site_zone`, `approval_state`
- `service_packets.pdf`: pages containing Contractor, Service Zone, Payment Account, Work Order, Billed Total

**Field Mappings:**
```python
FIELD_MAP = {
    "person_id": "contractor_id",
    "person_name": "legal_name",
    "directory": "contractors",
    "alias_sheet": "aliases",
    "approval_id": "work_order_id",
    "approval_amount": "approved_amount",
    "payment_account": "payment_account",
    "requested_amount": "billed_total",
    "status_field": "status",
    "amendment_id": "work_order_id",
    "amendment_amount": "revised_amount"
}
```

**Alias Resolution:**
```python
# Build canonical name lookup
xl = pd.ExcelFile('contractor_directory.xlsx')
contractors = xl.parse('contractors')
aliases = xl.parse('aliases')

# Primary lookup by canonical name
emp_by_name = {}
for _, row in contractors.iterrows():
    key = str(row['legal_name']).strip().lower()
    emp_by_name[key] = row.to_dict()

# Add aliases pointing to same records
alias_to_id = {}
for _, row in aliases.iterrows():
    alias_to_id[row['alias_name'].lower()] = row['contractor_id']

# During matching: check canonical names first, then aliases
# If alias match found, lookup canonical record by contractor_id
```

**Status Validation:**
```python
wo = work_orders_by_id.get(wo_id)
if not wo:
    return False, "Invalid Work Order", contractor
if wo.get('status', '').lower() != 'active':
    return False, "Inactive Work Order", contractor  # or "Closed Work Order"
```

**Amendment Resolution:**
```python
# Get base approved amount
wo = work_orders_by_id[wo_id]
base_amount = float(wo['approved_amount'])

# Check for amendments (higher revision = more recent)
amendments = amendments_df[amendments_df['work_order_id'] == wo_id]
if not amendments.empty:
    latest = amendments.loc[amendments['revision'].idxmax()]
    effective_amount = float(latest['revised_amount'])
else:
    effective_amount = base_amount

# Validate against effective_amount
if abs(requested - effective_amount) > 0.01:
    return False, "Amount Mismatch", contractor
```

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

**Validation Reasons:**
- "Unknown Contractor" (name not in directory or aliases)
- "Invalid Work Order" (WO not found)
- "Inactive Work Order" (WO status is closed/cancelled)
- "Contractor Mismatch" (WO assigned to different contractor)
- "Account Mismatch" (payment account differs from directory)
- "Amount Mismatch" (billed amount differs from approved/revised amount)

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

## Research Stipend Reconciliation

**Source Files:**
- `recipient_roster.xlsx` with sheets:
  - `recipients`: `recipient_code`, `registered_name`, `campus_code`, `bank_token`
  - `aliases`: `recipient_code`, `name_variant`
- `award_authorizations.csv`: `award_ref`, `recipient_code`, `approved_value`, `campus_code`, `state` (active/archived)
- `award_adjustments.csv`: `award_ref`, `revision_no`, `adjusted_value`, `campus_code`, `state` (approved/rejected)
- `stipend_packets.pdf`: pages containing Recipient, Campus, Bank Token, Award Ref, Requested Amount

**Field Mappings:**
```python
FIELD_MAP = {
    "person_id": "recipient_code",
    "person_name": "registered_name",
    "directory": "recipients",
    "alias_sheet": "aliases",
    "approval_id": "award_ref",
    "approval_amount": "approved_value",
    "payment_account": "bank_token",
    "requested_amount": "requested_amount",
    "location_field": "campus_code",
    "status_field": "state",
    "amendment_id": "award_ref",
    "amendment_amount": "adjusted_value"
}
```

**Amendment Resolution (Multi-Field Override):**
```python
# Adjustments can override campus_code, not just amount
adjustments_df = pd.read_csv('award_adjustments.csv')
adjustments_df = adjustments_df[adjustments_df['state'] == 'approved']

amendment_by_award = {}
for _, row in adjustments_df.iterrows():
    award_ref = row['award_ref']
    if award_ref not in amendment_by_award or row['revision_no'] > amendment_by_award[award_ref]['revision_no']:
        amendment_by_award[award_ref] = row

# Resolve effective values
def get_effective_values(award_ref, base_record):
    if award_ref in amendment_by_award:
        adj = amendment_by_award[award_ref]
        return {
            'amount': float(adj['adjusted_value']),
            'campus': adj['campus_code']
        }
    return {
        'amount': float(base_record['approved_value']),
        'campus': base_record['campus_code']
    }
```

**Status Validation:**
```python
award = awards_by_id.get(award_ref)
if not award:
    return False, "Invalid Award Ref", recipient
if award.get('state', '').lower() not in ('active', 'approved'):
    return False, "Invalid Award Ref", recipient  # archived, cancelled, etc.
```

**Regex Patterns:**
```python
patterns = {
    "recipient_name": r'Recipient:\s*(.+?)(?:\n|$)',
    "campus": r'Campus:\s*(\S+)',
    "bank_token": r'Bank Token:\s*(\S+)',
    "award_ref": r'Award Ref:\s*(\S+)',
    "requested_amount": r'Requested Amount:\s*\$?([0-9,]+\.?\d*)',
}
```

**Validation Reasons:**
- "Unknown Recipient" (name not in roster or aliases)
- "Invalid Award Ref" (award not found or state is archived/cancelled)
- "Recipient Mismatch" (award assigned to different recipient_code)
- "Account Mismatch" (bank token differs from roster)
- "Campus Mismatch" (campus differs from award/adjustment)
- "Amount Mismatch" (requested amount differs from approved/adjusted amount)

## Adaptation Checklist

When adapting to a new domain:

1. Identify the person/entity being validated (employee, speaker, vendor, contractor, provider)
2. Identify the directory/registry containing their records
3. Check for alias/variant name tables (separate sheets in Excel, or separate CSVs)
4. Identify the approval reference (trip, session, PO, contract, work order, maintenance order)
5. Check if approval database is nested JSON (depots containing orders) - flatten if needed
6. Check for approval status fields (active, closed, lifecycle, archived, etc.)
7. Check for amendment/revision tables that override approved amounts or other fields (check for decision/rejected amendments)
8. Map the ID field names (person_id → domain-specific ID)
9. Map the account/payment field (bank_account, payment_account, payment_details, payout_account)
10. Map the amount field (claim_total, requested_fee, invoice_amount, approved_charge)
11. Adjust regex patterns to match PDF field labels in the new domain
12. Update validation reason messages to use domain-appropriate terminology
