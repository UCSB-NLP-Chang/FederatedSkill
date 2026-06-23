---
name: expense-claims-validation
description: Validate payment requests (expense claims, travel reimbursements, speaker honorariums, vendor invoices, field service work orders, fleet maintenance chargebacks, research stipends, clinical trial releases) from PDF documents against structured reference data. Use when cross-referencing document claims with master databases to detect fraud patterns including account mismatches, amount discrepancies, unauthorized entities, invalid references, inactive approvals, location mismatches, and revision/version overrides. Essential when source documents contain packet references with multiple revisions, nested JSON approval structures, sparse amendment tables, typos, name variations, or when approval amounts may be revised.
---

# Payment Request Validation

Cross-reference multi-page PDF requests against structured reference data (Excel/CSV directories, approval databases) to identify financial discrepancies and fraud indicators.

## Workflow

1. **Load Reference Data**
   - Load master directory (Excel/CSV) → DataFrame with `person_id`, `person_name`, `payment_account`
   - **Check for alias sheets**: If using Excel, look for additional sheets ('aliases', 'variants', 'dba') containing name variations mapped to canonical IDs
   - Load approval database (CSV/JSON) → DataFrame with `approval_id`, `approved_amount`, `person_id`, `status`
   - **Nested JSON**: For hierarchical structures (e.g., sponsors.programs.awards), flatten into flat `approval_id → record` lookup
   - **Check for amendments/versions**: Load revision/amendment/version table if present (overrides original approved amounts)
   - Build lookup indexes: `name_lower → person_record`, `approval_id → approval_record`, `alias_name → person_id`

2. **Parse Request Document**
   - Use `pdfplumber` or `pdftotext` (poppler-utils) to extract text per page
   - `pdfplumber` handles complex layouts; `pdftotext` is faster for simple documents
   - **Filter Out-of-Scope Pages**: Before parsing, check if the page contains a consistent claim header (e.g., "Charge Request", "Invoice", "Claim", "Participant Release Request"). Skip cover pages, appendices, or blank pages that lack this header.
   - Regex extract fields: requester name, payment account, approval code, requested amount, location/campus, packet reference, revision number
   - Preserve page numbers for reporting

3. **Deduplicate Packet Revisions**
   - If documents contain packet references (e.g., `PKT-01`) with revision numbers (e.g., `Rev: 1`, `Rev: 2`), keep ONLY the highest revision per packet
   - Lower revisions of the same packet are superseded and should not be validated
   - Example: PKT-01 Rev 1 and PKT-01 Rev 2 → keep only Rev 2 for validation

4. **Fuzzy Match Names (with Aliases)**
   - Normalize claim names: lowercase, strip whitespace, normalize punctuation (Dr. → Dr, Prof. → Prof)
   - Search against both canonical names AND alias entries
   - Calculate similarity using **Levenshtein distance** (not simple sequence matching)
   - Threshold: ≥90% similarity = match; <90% = "Unknown"
   - Use matched canonical name for downstream validation

5. **Validate Seven Fraud Indicators** (in order, stop at first failure)
   - **Unknown Person**: Best name match <90% similarity (check aliases if present)
   - **Invalid Approval Code**: `approval_id` not found in approvals database OR status is inactive (archived, closed, cancelled)
   - **Inactive Approval**: Approval exists but `status` is 'closed', 'inactive', 'cancelled', or 'archived' (not 'active'/'open'/'approved')
   - **Authorization Mismatch**: Approval exists and is active, but `approval.person_id ≠ requester.person_id`
   - **Account Mismatch**: Request payment account ≠ directory payment account record
   - **Location/Campus Mismatch**: Claim location/campus ≠ expected location from approval/amendment (when location fields exist)
   - **Amount Mismatch**: |`requested_amount - effective_approved_amount`| > $0.01 tolerance (use amended amount if revisions exist)

6. **Output Results**
   - JSON array of flagged requests with `request_page_number`, `person_name`, `requested_amount`, `payment_account`, `approval_code`, `reason`
   - Include notes on fuzzy-matched typos for audit trail

## Domain Mapping

Map the generic pattern to your specific domain:

| Generic Concept | Expense Claims | Speaker Honorariums | Vendor Invoices | Field Service Work Orders | Fleet Maintenance Chargebacks | Research Stipends | Clinical Trial Releases |
|----------------|----------------|---------------------|-----------------|---------------------------|-------------------------------|-------------------|-------------------------|
| Person | Employee | Speaker | Vendor | Contractor | Provider | Recipient | Participant |
| Person ID | `employee_id` | `speaker_id` | `vendor_id` | `contractor_id` | `provider_id` | `recipient_code` | `participant_code` |
| Directory | Employee Directory | Speaker Registry | Vendor Master | Contractor Directory | Provider Directory | Recipient Roster | Participant Registry |
| Aliases | - | - | DBA names | Legal name variants | DBA names | Name variants | Name aliases |
| Approval ID | `trip_id` | `approval_code` | `po_number` | `work_order_id` | `order_id` | `award_ref` | `award_ref` |
| Approval DB | Trip Approvals | Session Approvals | Purchase Orders | Work Orders | Maintenance Orders (JSON) | Award Authorizations | Award Catalog (nested JSON) |
| Packet ID | - | - | - | - | - | - | `packet_ref` |
| Revision Field | - | - | - | - | - | - | `revision_no` |
| Status Field | - | - | - | `status` (active/closed) | `lifecycle` (approved/closed) | `state` (active/archived) | `status` (active/archived) |
| Revisions | - | - | Change orders | Amendments | Amendments (decision field) | Adjustments (state field) | Versions (approval_state) |
| Location Field | - | - | - | `site_zone` | `depot_region` | `campus_code` | - |
| Payment Account | `bank_account` | `payment_account` | `payment_details` | `payment_account` | `payment_account` | `bank_token` | `payment_token` |
| Amount | `claim_total` | `requested_fee` | `invoice_amount` | `approved_amount` | `approved_charge` | `approved_value` | `approved_amount` |

## Validation Rules Reference

| Check | Failure Condition | Data Sources |
|-------|------------------|--------------|
| Person Existence | No directory match ≥90% similarity | Master Directory (+ Aliases sheet if present) |
| Approval Validity | `approval_id` not in approvals database OR status is 'archived'/'inactive'/'closed' | Approvals DB |
| Authorization | `approval.person_id` ≠ `requester.person_id` | Approval + Directory |
| Payment Account | `request.account` ≠ `directory.account` | Request PDF + Directory |
| Location/Campus | `claim.location` ≠ `expected.location` (post-amendment) | Claim PDF + Approvals + Amendments |
| Amount | \|`requested` - `effective_approved`\| > 0.01 | Request PDF + Approval + Amendments |

## File Format Handling

| Format | Tool | Notes |
|--------|------|-------|
| `.xlsx`, `.xls` | Python/pandas (`pd.read_excel`) | **Read tool fails on binary Excel files** |
| `.csv` | Read tool or Python/pandas | Works directly |
| `.json` | `json` module or `pandas.json_normalize` | Flatten nested arrays/objects before indexing |
| `.pdf` | `pdfplumber` (Python) or `pdftotext` (poppler-utils) | `pdfplumber` for complex layouts; `pdftotext` for fast plain-text |

### Reading Excel Files (Critical)

**Never use the Read tool on `.xlsx` or `.xls` files** — they are binary and return garbled output.

```bash
python3 -c "import pandas as pd; df = pd.read_excel('/path/to/file.xlsx'); print(df.to_string())"
```

### Multi-Sheet Excel Files

Many directories include alias/variant names in separate sheets:

```python
xl = pd.ExcelFile('contractor_directory.xlsx')
print(f"Sheets: {xl.sheet_names}")  # Check for 'aliases', 'variants', 'dba'

contractors = xl.parse('contractors')
aliases = xl.parse('aliases')  # columns: contractor_id, alias_name

# Build alias lookup: variant name -> canonical contractor_id
alias_lookup = {}
for _, row in aliases.iterrows():
    alias_lookup[row['alias_name'].lower()] = row['contractor_id']
```

### Flattening Nested JSON

For deeply nested approval structures (e.g., sponsors → programs → awards):

```python
import json

with open('award_catalog.json') as f:
    data = json.load(f)

# Flatten nested structure into approval_id -> record lookup
awards_by_id = {}
for sponsor in data['sponsors']:
    for program in sponsor['programs']:
        for award in program['awards']:
            awards_by_id[award['award_ref']] = {
                **award,
                'sponsor_name': sponsor['sponsor_name'],
                'program_id': program['program_id']
            }
```

## Key Implementation Details

### Fuzzy Matching (Critical)
- **Algorithm**: Use `python-Levenshtein` or `rapidfuzz` for `ratio()` calculation
- **Anti-pattern**: Simple character-by-character comparison fails on insertions (e.g., "Reys" vs "Reyes" scored 80% vs 95% with Levenshtein)
- **Threshold**: 90% catches single-character typos in average-length names (8-12 chars)
- **Aliases**: Always check alias table before declaring "Unknown"

### Approval Status Validation
Many approval systems have status fields. Treat 'archived', 'closed', 'cancelled', 'inactive' as invalid:

```python
if approval['status'].lower() not in ('active', 'open', 'approved'):
    return False, "Invalid Award Ref"  # Not just "Inactive" - often same as invalid
```

### Amendment/Version Resolution
When amendment/revision/version tables exist, resolve the effective approved amount:

```python
# Base amount from approvals
base_amount = approval['approved_amount']

# Check for revisions - filter to approved entries only
versions = versions_df[versions_df['award_ref'] == award_ref]
versions = versions[versions['approval_state'] == 'approved']

if not versions.empty:
    # Get latest revision (highest version_no)
    latest = versions.loc[versions['version_no'].idxmax()]
    # CRITICAL: Only override if field is not null/empty
    effective_amount = latest['version_amount'] if pd.notna(latest['version_amount']) else base_amount
else:
    effective_amount = base_amount
```

**Sparse Amendment Tables**: Some version/amendment tables have rows where certain override fields are empty. Only apply non-empty values from the latest approved revision.

### Packet Deduplication (Packet References)
When documents contain packet IDs with multiple revisions:

```python
# Group pages by packet_ref, keep only highest revision
packets = {}
for page in pages:
    key = page['packet_ref']
    if key not in packets or page['revision_no'] > packets[key]['revision_no']:
        packets[key] = page

# Validate only retained pages
pages_to_validate = list(packets.values())
```

### PDF Parsing
- **Tool**: `pdfplumber` handles layout variations better than `PyPDF2`; `pdftotext` is a fast alternative
- **pdfplumber pattern**: `pdfplumber.open(path).pages` → `page.extract_text()`
- **pdftotext per-page extraction**: `pdftotext -f <page_num> -l <page_num> <file.pdf> -`

### Dependencies
```bash
pip install --break-system-packages pdfplumber pandas openpyxl python-Levenshtein
# OR for faster matching:
pip install --break-system-packages rapidfuzz
```

## Anti-Patterns

- **Do not use Read tool on `.xlsx` files** - they are binary and will fail. Use Python/pandas instead.
- **Do not assume exact name matches** - watch for typos and use fuzzy matching
- **Do not validate all revisions of a packet** - deduplicate to highest revision first
- **Do not apply null/empty amendment overrides** - check `pd.notna()` before overriding base values
- **Do not skip building lookup tables** - repeated linear searches are slow and error-prone
- **Do not use PyPDF2** for complex PDF layouts - prefer pdfplumber
- **Do not hardcode field names** - map domain-specific fields using the Domain Mapping table
- **Do not assume approval codes belong to the requesting entity** - always verify the match
- **Do not ignore status fields** - an existing approval may be closed or archived
- **Do not forget amendment tables** - revised amounts override original approvals

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs. Pass raw float values directly.

## Known invariants (by sub-task)

### travel-expense-claim-validation & speaker-honorarium-review & clinic-shift-claims & field-service-workorder-audit
- Validation priority order: Unknown Entity → Invalid Reference Code → Inactive Status → Entity Mismatch → Account Mismatch → Amount/Fee Mismatch. Stop at first failure.
- Fuzzy match threshold: 90% Levenshtein ratio.
- Amount tolerance: 0.01 for currency comparisons.

### fleet-maintenance-chargeback-audit
- Nested JSON structure: Orders live under `depots[].orders[]` — flatten before validation.
- Status field: `lifecycle` (not `status`), valid value is `'approved'`.
- Amendment resolution: Only apply amendments where `decision == 'approved'`; use highest `amendment_no`.

### research-stipend-reconciliation & clinical-trial-participant-release-audit
- Validation priority order: Unknown Recipient → Invalid Award Ref (includes archived status) → Recipient Mismatch → Account Mismatch → Amount Mismatch. Stop at first failure.
- **Packet deduplication**: Documents may contain multiple revisions of the same packet (e.g., PKT-01 Rev 1 and Rev 2). Keep ONLY highest revision per packet_ref.
- **Nested JSON**: Awards often live in sponsors[].programs[].awards — flatten into award_ref → record lookup.
- **Sparse version tables**: Version rows may have empty override fields (e.g., `version_amount` is null). Only apply non-empty overrides.
- Status field: `state` or `status` — 'archived'/'closed' makes award invalid.
- Fuzzy match threshold: 90% Levenshtein ratio.
- Amount tolerance: 0.01 for currency comparisons.

## When Validation Fails

- **Module errors**: Use virtual environment; otherwise use `--break-system-packages`.
- **Zero matches**: Lower fuzzy threshold to 80% temporarily to inspect near-misses.
- **Regex misses**: Print raw `page.extract_text()` to adjust patterns.
- **Amount parsing**: Normalize currency symbols and commas: `amount = float(re.sub(r'[$,]', '', amount_str))`

## References

- `references/fuzzy-matching-guide.md` - Algorithm details and threshold tuning
- `references/domain-examples.md` - Concrete field mappings including clinical trials with packet revisions and nested JSON
- `references/sparse-amendments.md` - Handling version/amendment tables with empty override fields