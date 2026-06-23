---
name: expense-claim-validation
description: Validate payment requests (expense claims, speaker honorariums, clinic shift claims, field service invoices, contractor billing packets, fleet maintenance chargebacks, research stipends, clinical trial participant releases, etc.) against authoritative registries and approvals. Use when screening expense reports, auditing reimbursement requests, reviewing speaker honorariums, validating shift claims, auditing field service work orders, validating contractor billing packets, auditing fleet maintenance chargebacks, reconciling research stipend disbursements, validating clinical trial participant releases, or flagging discrepancies across PDF claims, Excel registry data, and CSV/JSON approval records.
---

# Payment Request Validation

Cross-reference payment requests against authoritative data sources to detect fraud, errors, and policy violations.

## Workflow

1. **Load reference data**
   - Registry (Excel): Use Python with `openpyxl` or `pandas` — the Read tool cannot parse binary Excel files
   - Check for multiple sheets: `contractors`, `aliases`, `name_variants`, `providers`, `provider_aliases`, `participants` — load and merge all
   - Approvals (CSV or JSON): Load directly with Python. JSON may be nested under depot/region/sponsor/program keys
   - Adjustments/Amendments/Versions (CSV): Load if amendments modify approved amounts or other fields (campus, location, participant_code, etc.)
   - Build lookup structures: person/provider/participant by name (including all aliases), approval/award by code/ID, person/provider by ID

2. **Extract requests from PDF**
   - Use Read tool on PDF to get text content
   - Parse structured data: page number, person/contractor/provider/participant name, amount, payment account, approval/work order/award code, campus/location code (if present)

3. **Apply amendments/versions** (if applicable)
   - For simple amendments: filter where `decision == 'approved'` (ignore rejected), apply latest `amendment_no`
   - For revision-based systems: group by approval code, select maximum revision number with `approval_state == 'approved'`
   - For version-override systems: process versions sequentially, handle null values carefully (see `references/version_override_systems.md`)
   - Override base approved values with amended/versioned values (amount, campus_code, participant_code, etc.)
   - Track amendment/revision/version number for audit trail

4. **Validate each request** — check all dimensions:
   - **Person/provider/participant exists**: Name in registry or aliases (use fuzzy match for typos, spacing errors, missing words)
   - **Payment account matches**: Requested account equals registered account
   - **Approval/work order/award code valid**: Code exists in approvals AND status/lifecycle is 'approved'/'active' (not 'closed', 'draft', 'pending', 'archived')
   - **Amount matches**: Requested amount equals approved amount (after amendments/versions, use latest approved revision)
   - **Ownership**: Approval's person_id/provider_id/participant_code matches requester's person_id/provider_id/participant_code
   - **Campus/location matches** (if applicable): Requested campus/location code equals approved/amended campus code

5. **Generate alerts**
   - Output JSON array with flagged requests
   - Use field name `claim_page_number` (or domain variant like `request_page_number`)
   - Include: claim_page_number, person/provider/participant name, requested amount, reason, relevant details

## Validation Rules

| Check | Failure Condition | Alert Reason |
|-------|-------------------|--------------|
| Person lookup | Name not in registry or aliases (after fuzzy match) | "Unknown Person" / "Unknown Speaker" / "Unknown Employee" / "Unknown Clinician" / "Unknown Contractor" / "Unknown Provider" / "Unknown Recipient" / "Unknown Participant" |
| Payment account | `request.account != registry.account` | "Account Mismatch" / "Payout Account Mismatch" / "Bank Token Mismatch" / "Token Mismatch" |
| Approval existence | Code not in approvals | "Invalid Approval Code" / "Invalid Trip ID" / "Invalid Shift Code" / "Invalid Work Order" / "Invalid Order ID" / "Invalid Award Ref" / "Invalid Grant ID" |
| Approval status | Code exists but lifecycle != 'approved' (e.g., 'closed', 'draft', 'archived') | "Invalid Order ID" / "Closed Work Order" / "Draft Approval" / "Archived Award" |
| Amount | `requested_amount != approved_amount` (within $0.01, after amendments) | "Amount Mismatch" / "Fee Mismatch" |
| Ownership | `approval.person_id != requester.person_id` | "Ownership Mismatch" / "Speaker Mismatch" / "Traveler Mismatch" / "Clinician Mismatch" / "Contractor Mismatch" / "Provider Mismatch" / "Participant Mismatch" / "Recipient Mismatch" |
| Campus/location | `request.campus_code != approved.campus_code` (after amendments) | "Campus Mismatch" / "Location Mismatch" |

## Name Matching (Critical)

**Build comprehensive name index including aliases:**
```python
# Load both main registry and aliases sheet
name_to_id = {}
for _, row in contractors_df.iterrows():
    name_to_id[normalize(row['legal_name'])] = row['contractor_id']
for _, row in aliases_df.iterrows():
    name_to_id[normalize(row['alias_name'])] = row['contractor_id']
```

**Normalize before matching:**
- Lowercase, strip whitespace
- Remove titles: Dr., Prof., Mr., Ms., Mrs., Ltd, LLC, Co, Company
- Collapse multiple spaces to single space

**Fuzzy matching rules:**
- Threshold ≥0.80 for typos like "Ptel"→"Patel"
- **Critical for spacing errors**: "Blue Peak Mechanic" → "Blue Peak Mechanical" (missing 'al')
- Accept matches with ≤2 character differences OR 80%+ similarity
- Examples: "Alice Chenn" → "Alice Chen", "Blue Peak Mechanic" → "Blue Peak Mechanical", "Sofia Mendez" → "Sofia Mendes", "Noor Hadaad" → "Noor Haddad", "Aiden Moor" → "Aiden Moore", "Eli Grnt" → "Eli Grant"

## Handling Amendments, Revisions, and Versions

Three related but distinct patterns:

### Amendment Systems
Simple post-hoc changes with decision field:
```python
# Filter to approved decisions only
approved_amends = [a for a in amendments if a['decision'] == 'approved']
# Apply latest amendment_no for each order
```

### Revision Systems
Multiple snapshots with state tracking:
```python
# Group by approval_code, get max revision_no where approval_state == 'approved'
```

### Version Override Systems
Sequential overrides where null values matter:
```python
# Process versions in order; null amount means "no value set"
# See references/version_override_systems.md for detailed patterns
```

**See `references/version_override_systems.md` for:**
- Null value handling in version sequences
- Nested sponsor/program/award JSON flattening
- Clinical trial and research grant specific patterns

## Lifecycle Status Checking

**Critical**: An order code that exists but is not 'approved' should still flag:

```python
# Check both existence AND status
if order_id not in orders:
    reason = "Invalid Order ID"  # Does not exist
elif orders[order_id]['lifecycle'] != 'approved':
    reason = "Invalid Order ID"  # Exists but not approved (closed, draft, archived, etc.)
```

Common status values:
- `approved` / `active` → Valid
- `closed` / `completed` / `draft` / `pending` / `archived` → Invalid (flag as "Invalid Order ID" or specific reason)

## JSON Approvals with Nested Structure

Some systems nest orders under depot/region or sponsor/program keys:

```python
# Flatten nested JSON approvals
orders = {}
with open('maintenance_orders.json') as f:
    data = json.load(f)
    for depot in data['depots']:
        for order in depot['orders']:
            orders[order['order_id']] = {...}

# Or for clinical trials
for sponsor in data['sponsors']:
    for program in sponsor['programs']:
        for award in program['awards']:
            awards[award['award_ref']] = {...}
```

## Output Format

**Use exact field names** — tests may validate field names strictly:

```json
[
  {
    "claim_page_number": 2,
    "person_name": "Victor Han",
    "requested_amount": 520.0,
    "payment_account": "BAD-702",
    "approval_code": "SHIFT-B2",
    "reason": "Account Mismatch"
  }
]
```

**Required fields:**
- `claim_page_number` (integer, 1-based page index) — or domain-specific variant like `request_page_number`
- `person_name` or `provider_name` or `recipient_name` or `participant_name` (string, original name from claim)
- `requested_amount` (number)
- `reason` (string from Validation Rules table)

**Optional but recommended:**
- `payment_account` / `bank_token` / `payment_token` (string)
- `approval_code` / `award_ref` / `grant_id` (string, original code from claim)
- `campus_code` / `site_code` (string, if applicable)

## Field Name Adaptation

The script uses generic field names. Adapt to your domain:

| Generic | Travel Expense | Clinic Shift | Speaker Honorarium | Field Service | Fleet Maintenance | Research Stipend | Clinical Trial |
|---------|---------------|--------------|-------------------|---------------|-------------------|------------------|----------------|
| person_name | employee_name | clinician_name | speaker_name | contractor_name | provider_name | recipient_name | participant_name |
| person_id | employee_id | clinician_id | speaker_id | contractor_id | provider_id | recipient_code | participant_code |
| approval_code | trip_id | shift_ref/shift_code | engagement_id | work_order_id | order_id | award_ref | award_ref |
| payment_account | bank_account | payout_account | payment_account | payment_account | payment_account | bank_token | payment_token |
| approved_amount | approved_amount | approved_pay | honorarium_fee | approved_amount | approved_charge | approved_value/adjusted_value | approved_amount/version_amount |
| lifecycle | status | status | status | status | lifecycle | state | status |
| campus_code | - | - | - | - | - | campus_code | site_code |
| page_field | claim_page_number | claim_page_number | claim_page_number | claim_page_number | claim_page_number | request_page_number | request_page_number |

## Anti-Patterns

- **Do not** attempt to read Excel files with the Read tool — it fails on binary formats
- **Do not** assume exact name matches — implement fuzzy matching for typos AND spacing errors
- **Do not** check only the main registry sheet — always check for aliases/name variants sheets
- **Do not** ignore amendment decision fields — only apply amendments where `decision == 'approved'`
- **Do not** check only approval existence — verify lifecycle/status is 'approved' (watch for 'archived')
- **Do not** forget crosswalk resolution — external codes often differ from internal approval codes
- **Do not** ignore approval status — check if work order is active/approved, not just present
- **Do not** forget revision/version handling — use latest approved revision amount, not original
- **Do not** stop at first failure — check all validation dimensions to catch compound issues
- **Do not** skip the ownership check — requesters may use valid approval codes that belong to others
- **Do not** use inconsistent output field names — use `claim_page_number` (or domain variant) not `page`
- **Do not** ignore campus/location amendments — amendments may change location codes, not just amounts
- **Do not** assume versions always provide values — null amounts in latest version may invalidate the request

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| Cannot read registry | Excel is binary | Switch to Python with `openpyxl` or `pandas` |
| False negatives on valid requests | Exact name matching | Implement fuzzy matching with threshold ≥0.80 |
| Valid contractor flagged unknown | Missing aliases sheet | Check for `aliases`, `name_variants`, or similar sheets |
| Spacing errors not caught | Fuzzy threshold too strict or normalization incomplete | Normalize spaces, use difflib.SequenceMatcher |
| "Invalid Code" for valid-looking codes | Missing crosswalk step | Check if external→internal code mapping exists |
| Wrong amount for revised work orders | Not handling amendments | Filter by `decision == 'approved'`, apply amended amounts |
| Valid order flagged invalid | Checking existence only, not lifecycle | Verify `lifecycle == 'approved'` or `status == 'active'` (reject 'archived') |
| Missing fraud patterns | Single-dimension checks | Validate all six dimensions per request (including campus/location) |
| Test failures on field names | Using `page` instead of `claim_page_number` | Use exact field names from Output Format section |
| Campus mismatch undetected | Not checking amended campus codes | Apply amended campus_code when processing revisions |
| Null amount in latest version | Version override system with sparse updates | See `references/version_override_systems.md` — null may mean "no valid amount" |
| Nested JSON not parsing | Sponsor/program or depot/region nesting | Flatten structure before building lookup dict |

## Scripts

- `scripts/validate_claims.py` — Full validation pipeline with fuzzy matching, crosswalk support, alias handling, amendment processing, lifecycle checking, and all validation dimensions. Adapt field names in the `HEADERS` config at top of file for your specific data.

## References

- `references/amendment_patterns.md` — Detailed patterns for handling amendments, revisions, and decision-based approval systems
- `references/json_approvals.md` — Patterns for flattening nested JSON approval structures (depot/region patterns)
- `references/campus_location_validation.md` — Patterns for validating campus/location code mismatches and amendments that change location fields
- `references/version_override_systems.md` — Patterns for version-based systems with null handling, nested sponsor/program structures, clinical trial and research grant specific patterns
