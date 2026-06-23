---
name: expense-claims-validation
description: Validate expense, travel, or honorarium claims from PDF documents against structured reference data (employee/speaker directories, trip/session approvals). Use when cross-referencing document claims with master databases to detect fraud patterns (account mismatches, amount discrepancies, unauthorized travelers/speakers, unknown entities). Essential when source documents contain typos or slight name variations requiring fuzzy matching.
---

# Expense & Honorarium Claims Validation

Cross-reference multi-page PDF claims against structured reference data (Excel/CSV directories, approval databases) to identify financial discrepancies and fraud indicators.

## Workflow

1. **Load Reference Data**
   - Load directory (Excel/CSV) → DataFrame with `entity_id`, `entity_name`, `payment_account`
   - Load approval database (CSV) → DataFrame with `approval_code`, `approved_amount`, `entity_id`
   - Build lookup indexes: `name_lower → record` and `approval_code → record`

2. **Parse Claims Document**
   - Use `pdfplumber` (not PyPDF2) to extract text per page
   - Regex extract fields: `Entity Name`, `Payment Account`, `Approval Code`, `Requested Fee/Total`
   - Preserve page numbers for reporting

3. **Fuzzy Match Entity Names**
   - Normalize claim names: lowercase, strip whitespace
   - Calculate similarity against all directory names using **Levenshtein distance**
   - Threshold: ≥90% similarity = match; <90% = "Unknown Entity"
   - Use matched canonical name for downstream validation

4. **Validate Five Fraud Indicators** (in order)
   - **Unknown Entity**: Best name match <90% similarity
   - **Invalid Approval Code**: `approval_code` not found in approvals database
   - **Entity Mismatch**: Approval exists but `approval.entity_id ≠ claimant.entity_id`
   - **Account Mismatch**: Claim payment account ≠ entity payment account record
   - **Amount/Fee Mismatch**: |`requested_amount - approved_amount`| > $0.01 tolerance

5. **Output Results**
   - JSON array of flagged claims with `page_number`, `entity_name`, `requested_amount`, `payment_account`, `approval_code`, `reason`
   - Include notes on fuzzy-matched typos for audit trail

## Validation Rules Reference

| Check | Failure Condition | Data Sources |
|-------|------------------|--------------|
| Entity Existence | No directory match ≥90% similarity | Directory |
| Approval Validity | `approval_code` not in approvals database | Approvals |
| Authorization | `approval.entity_id` ≠ `claimant.entity_id` | Approvals + Directory |
| Payment Account | `claim.account` ≠ `entity.account` | Claim PDF + Directory |
| Amount/Fee | \|`requested` - `approved`\| > 0.01 | Claim PDF + Approvals |

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

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### travel-expense-claim-validation & speaker-honorarium-review
- Validation priority order: Unknown Entity → Invalid Approval Code → Entity Mismatch → Account Mismatch → Amount/Fee Mismatch. Stop at first failure.
- Fuzzy match threshold: 90% Levenshtein ratio (not simple sequence matching).
- Amount tolerance: 0.01 for currency comparisons.
- Entity names frequently contain typos ("Briann" vs "Brian", "Reys" vs "Reyes", "Dr Evelyn" vs "Dr. Evelyn") — always use fuzzy matching, never require exact match.

## Key Implementation Details

### Fuzzy Matching (Critical)
- **Algorithm**: Use `python-Levenshtein` or `rapidfuzz` for `ratio()` calculation
- **Anti-pattern**: Simple character-by-character comparison fails on insertions (e.g., "Briann" vs "Brian" scored 50% vs 92% with Levenshtein)
- **Threshold**: 90% catches single-character typos in average-length names (8-12 chars)

### PDF Parsing
- **Tool**: `pdfplumber` handles layout variations better than `PyPDF2`
- **Pattern**: `pdfplumber.open(path).pages` → `page.extract_text()`
- **Regex tip**: Use case-insensitive patterns with optional whitespace: `r'Entity:\s*(.+)'`

### Dependencies
```bash
pip install --break-system-packages pdfplumber pandas openpyxl python-Levenshtein
# OR for faster matching:
pip install --break-system-packages rapidfuzz
```
*Note: Use `--break-system-packages` if running in a restricted system Python environment without venv (PEP 668).*

## When Validation Fails

- **Module errors**: Use virtual environment; avoid system Python package conflicts. If restricted, use `--break-system-packages`.
- **Zero matches**: Lower fuzzy threshold to 80% temporarily to inspect near-misses
- **Regex misses**: Print raw `page.extract_text()` to adjust patterns for PDF layout changes
- **Amount parsing**: Normalize currency symbols and commas: `amount = float(re.sub(r'[$,]', '', amount_str))`

## Common Variants

### Intermediate Crosswalks
Some domains use a two-step code resolution (e.g., external shift code → internal code → approval).
- Load crosswalk table first.
- Resolve `claim_code` → `internal_code` via crosswalk. If missing → "Invalid Code".
- Use `internal_code` to lookup in approvals database.
- Validation order remains the same; treat crosswalk failure as step 2.

## Scripts

Use `scripts/validate_claims.py` as a template. Configure the `VALIDATION_CONFIG` dictionary for:
- File paths (directory, approvals, claims PDF)
- Fuzzy match threshold (default 90)
- Amount tolerance (default 0.01)
- Output JSON path
- Field name mappings (e.g., `name_field`, `id_field`, `account_field`)

## References

- `references/fuzzy-matching-guide.md` - Algorithm details and threshold tuning
- `references/domain-examples.md` - Concrete field mappings for different domains (expense claims, speaker honorariums, vendor invoices, clinic shifts)
