---
name: expense-claims-validation
description: Validate payment requests (expense claims, travel reimbursements, speaker honorariums, vendor invoices) from PDF documents against structured reference data (employee directories, approval databases). Use when cross-referencing document claims with master databases to detect fraud patterns (account mismatches, amount discrepancies, unauthorized travelers/speakers, unknown entities). Essential when source documents contain typos or slight name variations requiring fuzzy matching.
---

# Payment Request Validation

Cross-reference multi-page PDF requests against structured reference data (Excel/CSV directories, approval databases) to identify financial discrepancies and fraud indicators.

## Workflow

1. **Load Reference Data**
   - Load master directory (Excel/CSV) → DataFrame with `person_id`, `person_name`, `payment_account`
   - Load approval database (CSV) → DataFrame with `approval_id`, `approved_amount`, `person_id`
   - Build lookup indexes: `name_lower → person_record` and `approval_id → approval_record`

2. **Parse Request Document**
   - Use `pdfplumber` (not PyPDF2) to extract text per page
   - Regex extract fields: requester name, payment account, approval code, requested amount
   - Preserve page numbers for reporting

3. **Fuzzy Match Names**
   - Normalize claim names: lowercase, strip whitespace, normalize punctuation (Dr. → Dr, Prof. → Prof)
   - Calculate similarity against all directory names using **Levenshtein distance** (not simple sequence matching)
   - Threshold: ≥90% similarity = match; <90% = "Unknown"
   - Use matched canonical name for downstream validation

4. **Validate Five Fraud Indicators** (in order)
   - **Unknown Person**: Best name match <90% similarity
   - **Invalid Approval Code**: `approval_id` not found in approvals database
   - **Authorization Mismatch**: Approval exists but `approval.person_id ≠ requester.person_id`
   - **Account Mismatch**: Request payment account ≠ directory payment account record
   - **Amount Mismatch**: |`requested_amount - approved_amount`| > $0.01 tolerance

5. **Output Results**
   - JSON array of flagged requests with `request_page_number`, `person_name`, `requested_amount`, `payment_account`, `approval_code`, `reason`
   - Include notes on fuzzy-matched typos for audit trail

## Domain Mapping

Map the generic pattern to your specific domain:

| Generic Concept | Expense Claims | Speaker Honorariums | Vendor Invoices |
|----------------|----------------|---------------------|-----------------|
| Person | Employee | Speaker | Vendor |
| Person ID | `employee_id` | `speaker_id` | `vendor_id` |
| Directory | Employee Directory | Speaker Registry | Vendor Master |
| Approval ID | `trip_id` | `approval_code` | `po_number` |
| Approval DB | Trip Approvals | Session Approvals | Purchase Orders |
| Payment Account | `bank_account` | `payment_account` | `payment_details` |
| Amount | `claim_total` | `requested_fee` | `invoice_amount` |

## Validation Rules Reference

| Check | Failure Condition | Data Sources |
|-------|------------------|--------------|
| Person Existence | No directory match ≥90% similarity | Master Directory |
| Approval Validity | `approval_id` not in approvals database | Approvals DB |
| Authorization | `approval.person_id` ≠ `requester.person_id` | Approval + Directory |
| Payment Account | `request.account` ≠ `directory.account` | Request PDF + Directory |
| Amount | \|`requested` - `approved`\| > 0.01 | Request PDF + Approval |

## File Format Handling

| Format | Tool | Notes |
|--------|------|-------|
| `.xlsx`, `.xls` | Python/pandas (`pd.read_excel`) | **Read tool fails on binary Excel files** |
| `.csv` | Read tool or Python/pandas | Works directly |
| `.pdf` | `pdfplumber` (Python) | Better layout handling than PyPDF2 |

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

## Key Implementation Details

### Fuzzy Matching (Critical)
- **Algorithm**: Use `python-Levenshtein` or `rapidfuzz` for `ratio()` calculation
- **Anti-pattern**: Simple character-by-character comparison fails on insertions (e.g., "Reys" vs "Reyes" scored 80% vs 95% with Levenshtein)
- **Threshold**: 90% catches single-character typos in average-length names (8-12 chars)

### PDF Parsing
- **Tool**: `pdfplumber` handles layout variations better than `PyPDF2`
- **Pattern**: `pdfplumber.open(path).pages` → `page.extract_text()`
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

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### travel-expense-claim-validation & speaker-honorarium-review & clinic-shift-claims
- Validation priority order: Unknown Entity → Invalid Reference Code → Entity Mismatch → Account Mismatch → Amount/Fee Mismatch. Stop at first failure.
- Fuzzy match threshold: 90% Levenshtein ratio (not simple sequence matching).
- Amount tolerance: 0.01 for currency comparisons.
- Entity names frequently contain typos ("Briann" vs "Brian", "Reys" vs "Reyes", "Ptel" vs "Patel", "Elis" vs "Ellis") — always use fuzzy matching, never require exact match.

## When Validation Fails

- **Module errors**: Use virtual environment; avoid system Python package conflicts. If restricted, use `--break-system-packages`.
- **Zero matches**: Lower fuzzy threshold to 80% temporarily to inspect near-misses
- **Regex misses**: Print raw `page.extract_text()` to adjust patterns for PDF layout changes
- **Amount parsing**: Normalize currency symbols and commas: `amount = float(re.sub(r'[$,]', '', amount_str))`

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
- `references/domain-examples.md` - Concrete field mappings for common scenarios