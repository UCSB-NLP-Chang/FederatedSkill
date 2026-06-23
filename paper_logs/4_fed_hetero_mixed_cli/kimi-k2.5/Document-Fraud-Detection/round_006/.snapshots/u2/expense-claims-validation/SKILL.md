---
name: expense-claims-validation
description: Validate payment requests (expense claims, travel reimbursements, speaker honorariums, vendor invoices, field service work orders, fleet maintenance chargebacks, research stipends) from PDF documents against structured reference data (directories, approval databases, revision logs). Use when cross-referencing document claims with master databases to detect fraud patterns (account mismatches, amount discrepancies, unauthorized entities, invalid references, inactive approvals, location mismatches). Essential when source documents contain typos, name variations, nested JSON approval structures, or when approval amounts may be revised by amendment tables.
---

# Payment Request Validation

Cross-reference multi-page PDF requests against structured reference data (Excel/CSV directories, approval databases) to identify financial discrepancies and fraud indicators.

## Workflow

1. **Load Reference Data**
   - Load master directory (Excel/CSV) → DataFrame with `person_id`, `person_name`, `payment_account`
   - **Check for alias sheets**: If using Excel, look for additional sheets ('aliases', 'variants', 'dba') containing name variations mapped to canonical IDs
   - Load approval database (CSV) → DataFrame with `approval_id`, `approved_amount`, `person_id`, `status`
   - **Check for amendments**: Load revision/amendment table if present (overrides original approved amounts)
   - Build lookup indexes: `name_lower → person_record`, `approval_id → approval_record`, `alias_name → person_id`

2. **Parse Request Document**
   - Use `pdfplumber` or `pdftotext` (poppler-utils) to extract text per page
   - `pdfplumber` handles complex layouts; `pdftotext` is faster for simple documents
   - Regex extract fields: requester name, payment account, approval code, requested amount, location/campus
   - Preserve page numbers for reporting

3. **Fuzzy Match Names (with Aliases)**
   - Normalize claim names: lowercase, strip whitespace, normalize punctuation (Dr. → Dr, Prof. → Prof)
   - Search against both canonical names AND alias entries
   - Calculate similarity using **Levenshtein distance** (not simple sequence matching)
   - Threshold: ≥90% similarity = match; <90% = "Unknown"
   - Use matched canonical name for downstream validation

4. **Validate Seven Fraud Indicators** (in order, stop at first failure)
   - **Unknown Person**: Best name match <90% similarity (check aliases if present)
   - **Invalid Approval Code**: `approval_id` not found in approvals database
   - **Inactive Approval**: Approval exists but `status` is 'closed', 'inactive', 'cancelled', or 'archived' (not 'active'/'open'/'approved')
   - **Authorization Mismatch**: Approval exists and is active, but `approval.person_id ≠ requester.person_id`
   - **Account Mismatch**: Request payment account ≠ directory payment account record
   - **Location/Campus Mismatch**: Claim location/campus ≠ expected location from approval/amendment (when location fields exist)
   - **Amount Mismatch**: |`requested_amount - effective_approved_amount`| > $0.01 tolerance (use amended amount if revisions exist)

5. **Output Results**
   - JSON array of flagged requests with `request_page_number`, `person_name`, `requested_amount`, `payment_account`, `approval_code`, `reason`
   - Include notes on fuzzy-matched typos for audit trail

## Domain Mapping

Map the generic pattern to your specific domain:

| Generic Concept | Expense Claims | Speaker Honorariums | Vendor Invoices | Field Service Work Orders | Fleet Maintenance Chargebacks | Research Stipends |
|----------------|----------------|---------------------|-----------------|---------------------------|-------------------------------|-------------------|
| Person | Employee | Speaker | Vendor | Contractor | Provider | Recipient |
| Person ID | `employee_id` | `speaker_id` | `vendor_id` | `contractor_id` | `provider_id` | `recipient_code` |
| Directory | Employee Directory | Speaker Registry | Vendor Master | Contractor Directory | Provider Directory | Recipient Roster |
| Aliases | - | - | DBA names | Legal name variants | DBA names | Name variants |
| Approval ID | `trip_id` | `approval_code` | `po_number` | `work_order_id` | `order_id` | `award_ref` |
| Approval DB | Trip Approvals | Session Approvals | Purchase Orders | Work Orders | Maintenance Orders (JSON) | Award Authorizations |
| Status Field | - | - | - | `status` (active/closed) | `lifecycle` (approved/closed) | `state` (active/archived) |
| Revisions | - | - | Change orders | Amendments | Amendments (decision field) | Adjustments (state field) |
| Location Field | - | - | - | `site_zone` | `depot_region` | `campus_code` |
| Payment Account | `bank_account` | `payment_account` | `payment_details` | `payment_account` | `payment_account` | `bank_token` |
| Amount | `claim_total` | `requested_fee` | `invoice_amount` | `approved_amount` | `approved_charge` | `approved_value` |

## Validation Rules Reference

| Check | Failure Condition | Data Sources |
|-------|------------------|--------------|
| Person Existence | No directory match ≥90% similarity | Master Directory (+ Aliases sheet if present) |
| Approval Validity | `approval_id` not in approvals database | Approvals DB |
| Approval Status | `status` is 'closed', 'inactive', 'cancelled', or 'archived' | Approvals DB |
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
| `.pdf` | `pdfplumber` (Python) or `pdftotext` (poppler-utils) | `pdfplumber` for complex layouts; `pdftotext` for fast, reliable plain-text extraction |

### Reading Excel Files (Critical)

**Never use the Read tool on `.xlsx` or `.xls` files** — they are binary and return garbled output.

```bash
python3 -c "import pandas as pd; df = pd.read_excel('/path/to/file.xlsx'); print(df.to_string())"
```

Or use openpyxl directly:
```python
from openpyxl import load_workbook
wb = load_workbook('/path/to/file.xlsx')
ws = wb.active
for row in ws.iter_rows(values_only=True):
    print(row)
```

### Multi-Sheet Excel Files

Many directories include alias/variant names in separate sheets:

```python
# Load main directory
xl = pd.ExcelFile('contractor_directory.xlsx')
print(f"Sheets: {xl.sheet_names}")  # Check for 'aliases', 'variants', 'dba'

contractors = xl.parse('contractors')
aliases = xl.parse('aliases')  # columns: contractor_id, alias_name

# Build alias lookup: variant name -> canonical contractor_id
alias_lookup = {}
for _, row in aliases.iterrows():
    alias_lookup[row['alias_name'].lower()] = row['contractor_id']
```

## Key Implementation Details

### Fuzzy Matching (Critical)
- **Algorithm**: Use `python-Levenshtein` or `rapidfuzz` for `ratio()` calculation
- **Anti-pattern**: Simple character-by-character comparison fails on insertions (e.g., "Reys" vs "Reyes" scored 80% vs 95% with Levenshtein)
- **Threshold**: 90% catches single-character typos in average-length names (8-12 chars)
- **Aliases**: Always check alias table before declaring "Unknown"

### Approval Status Validation
Many approval systems have status fields. Always validate:
```python
if approval['status'].lower() not in ('active', 'open', 'approved'):
    return False, "Inactive Approval", matched_person
```

Common status values indicating rejection:
- `closed`, `inactive`, `cancelled`, `expired`, `void`, `archived`

### Amount Revision Handling
When amendment/revision tables exist, resolve the effective approved amount and other overridden fields:

```python
# Base amount from approvals
base_amount = approval['approved_amount']

# Check for revisions (higher revision number = more recent)
# Filter to approved revisions only (decision/state == 'approved')
amendments = amendments_df[amendments_df['approval_id'] == approval_id]
amendments = amendments[amendments['decision'] == 'approved']  # or 'state' == 'approved'
if not amendments.empty:
    # Get latest revision
    latest = amendments.loc[amendments['revision'].idxmax()]
    effective_amount = latest['revised_amount']
    # Amendments may override other fields (campus, location, zone)
    effective_location = latest.get('campus_code', approval.get('campus_code'))
else:
    effective_amount = base_amount
    effective_location = approval.get('campus_code')

# Now compare requested vs effective_amount and effective_location
```

**Multi-field amendments:** Some domains have adjustments that modify multiple fields (amount, campus_code, site_zone). Apply all overridden fields from the latest approved revision.

### PDF Parsing
- **Tool**: `pdfplumber` handles layout variations better than `PyPDF2`; `pdftotext` (poppler-utils) is a fast alternative for simple documents
- **pdfplumber pattern**: `pdfplumber.open(path).pages` → `page.extract_text()`
- **pdftotext pattern**: `pdftotext -layout file.pdf -` or `pdftotext file.pdf -` for plain text
- **Regex tip**: Use case-insensitive patterns with optional whitespace: `r'Speaker:\s*(.+)'`

### Dependencies
```bash
pip install --break-system-packages pdfplumber pandas openpyxl python-Levenshtein
# OR for faster matching:
pip install --break-system-packages rapidfuzz
```
*Note: Use `--break-system-packages` if running in a restricted system Python environment without venv.*

## Anti-Patterns

- **Do not use Read tool on `.xlsx` files** - they are binary and will fail. Use Python/pandas instead.
- **Do not assume exact name matches** - watch for typos ("Dana Kapor" vs "Dana Kapoor", "Naomi Reys" vs "Naomi Reyes", "Dr Evelyn" vs "Dr. Evelyn")
- **Do not skip building lookup tables** - repeated linear searches are slow and error-prone
- **Do not use PyPDF2** for complex PDF layouts - prefer pdfplumber for table-aware extraction
- **Do not hardcode field names** - map domain-specific fields (e.g., `approval_code`) to the generic pattern using the Domain Mapping table
- **Do not assume approval codes belong to the requesting entity** - always verify the approval's assigned entity matches the requester
- **Do not ignore status fields** - an existing approval may be closed or cancelled
- **Do not forget amendment tables** - revised amounts override original approvals

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### travel-expense-claim-validation & speaker-honorarium-review & clinic-shift-claims & field-service-workorder-audit
- Validation priority order: Unknown Entity → Invalid Reference Code → Inactive Status → Entity Mismatch → Account Mismatch → Amount/Fee Mismatch. Stop at first failure.
- Fuzzy match threshold: 90% Levenshtein ratio (not simple sequence matching).
- Amount tolerance: 0.01 for currency comparisons.
- Entity names frequently contain typos ("Briann" vs "Brian", "Reys" vs "Reyes", "Ptel" vs "Patel", "Elis" vs "Ellis") — always use fuzzy matching, never require exact match.
- Check for alias/variant name tables when fuzzy matching fails.
- Verify approval status is active/open before checking authorization.
- Apply amendment/revision overrides to approved amounts before comparison.

### fleet-maintenance-chargeback-audit
- Validation priority order: Unknown Provider → Invalid Order ID → Inactive Order → Provider Mismatch → Account Mismatch → Amount Mismatch. Stop at first failure.
- Nested JSON structure: Orders live under `depots[].orders[]` — flatten into flat `order_id → order_record` lookup before validation.
- Status field: Fleet maintenance uses `lifecycle` (not `status`), valid value is `'approved'`; `closed`/`cancelled` → "Invalid Order ID" or "Inactive Order".
- Amendment resolution: Only apply amendments where `decision == 'approved'`; ignore `rejected`/`pending` entries. Use highest `amendment_no`.
- Amount tolerance: 0.01 for currency comparisons.

### research-stipend-reconciliation
- Validation priority order: Unknown Recipient → Invalid Award Ref → Recipient Mismatch → Account Mismatch → Campus Mismatch → Amount Mismatch. Stop at first failure.
- Status field: Award authorizations use `state` (not `status`), valid values are `'active'` or `'approved'`; `archived`/`cancelled` → "Invalid Award Ref".
- Adjustment resolution: Adjustments can modify **multiple fields** (amount + campus_code), not just amounts. Apply all overridden fields from the latest approved adjustment.
- Campus validation: Compare claimed campus against **adjusted campus** from latest approved adjustment, not the base authorization campus.
- Amount tolerance: 0.01 for currency comparisons.

## When Validation Fails

- **Module errors**: Use virtual environment; avoid system Python package conflicts. If restricted, use `--break-system-packages`.
- **Zero matches**: Lower fuzzy threshold to 80% temporarily to inspect near-misses
- **Regex misses**: Print raw `page.extract_text()` to adjust patterns for PDF layout changes
- **Amount parsing**: Normalize currency symbols and commas: `amount = float(re.sub(r'[$,]', '', amount_str))`
- **Multi-sheet Excel**: Use `pd.ExcelFile()` to inspect sheet names before assuming single sheet

## Intermediate Crosswalks

Some domains use a two-step code resolution (e.g., external shift code → internal code → approval).
- Load crosswalk table first.
- Resolve `claim_code` → `internal_code` via crosswalk. If missing → "Invalid Reference Code".
- Use `internal_code` to lookup in approvals database.
- Validation order remains the same; treat crosswalk failure as step 2.

**Example:** Clinic shift claims use `SHIFT-A1` (external) → crosswalk → `INT-5101` (internal) → authorization with approved pay and clinician assignment.

## Scripts

Use `scripts/validate_claims.py` as a template. Configure the `VALIDATION_CONFIG` dictionary for:
- File paths (directory, approvals, requests PDF)
- Fuzzy match threshold (default 90)
- Amount tolerance (default 0.01)
- Field name mappings (adapt to your domain)
- Output JSON path

## References

- `references/fuzzy-matching-guide.md` - Algorithm details, threshold tuning, and punctuation normalization
- `references/domain-examples.md` - Concrete field mappings for common scenarios including field service work orders with aliases and amendments
