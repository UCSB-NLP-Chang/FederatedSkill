---
name: expense-claims-validation
description: Validate expense, travel, honorarium, work-order, or stipend claims from PDF documents against structured reference data (directories, approval databases, revision logs). Use when cross-referencing document claims with master databases to detect fraud patterns (account mismatches, amount discrepancies, unauthorized entities, invalid references, location mismatches). Essential when source documents contain typos, aliases, or require revision-aware field resolution.
---

# Expense & Operational Claims Validation

Cross-reference multi-page PDF claims against structured reference data (Excel/CSV/JSON directories, approval databases, revision logs) to identify financial discrepancies and fraud indicators.

## Workflow

1. **Load Reference Data**
   - Load directory (Excel/CSV/JSON) → DataFrame with `entity_id`, `entity_name`, `payment_account`
   - Load aliases/crosswalk (if present) → Map `alias_name` → `entity_id`
   - Load approval/order database (CSV/JSON) → DataFrame with `reference_id`, `approved_amount`, `entity_id`, `status`
   - **JSON Handling**: If data is nested (e.g., `depots[].orders[]`), flatten to a single list of records before indexing.
   - Load revisions/amendments (if present) → Filter `approval_state == 'approved'` (or `decision == 'approved'`), group by `reference_id`, keep highest revision/amendment number.
   - Build lookup indexes: `name_lower → record`, `alias_lower → entity_id`, `reference_id → record`

2. **Parse Claims Document**
   - Use `pdfplumber` or `pdftotext` (poppler-utils) to extract text per page
   - Regex extract fields: `Entity Name`, `Payment Account`, `Reference ID`, `Requested Fee/Total`, `Location/Campus`
   - Preserve page numbers for reporting

3. **Resolve Entity Identity**
   - Normalize claim name: lowercase, strip whitespace, normalize titles (Dr. → Dr)
   - **Exact Alias Match**: Check against aliases table first. If match found, use canonical `entity_id`.
   - **Fuzzy Match**: If no alias match, calculate Levenshtein similarity against directory names.
   - Threshold: ≥90% similarity = match; <90% = "Unknown Entity"

4. **Validate Reference Status**
   - Check if `reference_id` exists in approval/order database.
   - Verify `status` is `active`, `approved`, or `valid`.
   - If `closed`, `draft`, `cancelled`, `archived`, or missing → Flag as "Invalid Reference" (or domain-specific equivalent like "Invalid Work Order").

5. **Resolve Expected Values from Amendments**
   - Start with base values from approval database.
   - If amendments/revisions table exists, filter to `approved`/`active` state.
   - Group by `reference_id`, keep highest revision/amendment number.
   - **Apply all overridden fields** from the latest amendment (amount, campus, status, etc.), not just amounts.

6. **Validate Six Fraud Indicators** (in order, stop at first failure)
   - **Unknown Entity**: Best name/alias match <90% similarity
   - **Invalid Reference**: `reference_id` not found or status is not active/approved
   - **Entity Mismatch**: Reference exists but `reference.entity_id ≠ claimant.entity_id`
   - **Account Mismatch**: Claim payment account ≠ entity payment account record
   - **Location/Campus Mismatch**: Claim location/campus ≠ expected location (check amendment overrides)
   - **Amount Mismatch**: |`requested_amount - expected_amount`| > $0.01 tolerance

7. **Output Results**
   - JSON array of flagged claims with `page_number`, `entity_name`, `requested_amount`, `payment_account`, `reference_id`, `reason`
   - Include notes on fuzzy-matched typos or alias resolutions for audit trail

## Validation Rules Reference

| Check | Failure Condition | Data Sources |
|-------|------------------|--------------|
| Entity Existence | No directory/alias match ≥90% similarity | Directory + Aliases |
| Reference Validity | `reference_id` missing or status ≠ active/approved | Approvals/Orders |
| Authorization | `reference.entity_id` ≠ `claimant.entity_id` | Approvals + Directory |
| Payment Account | `claim.account` ≠ `entity.account` | Claim PDF + Directory |
| Location/Campus | `claim.location` ≠ `expected.location` (post-amendment) | Claim PDF + Approvals + Amendments |
| Amount/Fee | \|`requested` - `expected`\| > 0.01 | Claim PDF + Approvals + Revisions |

## File Format Handling

| Format | Tool | Notes |
|--------|------|-------|
| `.xlsx`, `.xls` | Python/pandas (`pd.read_excel`) | **Read tool fails on binary Excel files** |
| `.csv` | Read tool or Python/pandas | Works directly |
| `.json` | `json` module or `pandas.json_normalize` | Flatten nested arrays/objects before indexing |
| `.pdf` | `pdfplumber` or `pdftotext` | `pdfplumber` for complex layouts; `pdftotext` (poppler-utils) for fast, reliable plain-text extraction |

### Reading Excel Files (Critical)

**Never use the Read tool on `.xlsx` or `.xls` files** — they are binary and return garbled output.

```bash
python3 -c "import pandas as pd; df = pd.read_excel('/path/to/file.xlsx'); print(df.to_string())"
```

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs. Pass raw float values directly.
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision.

## Key Implementation Details

### Alias & Fuzzy Matching
- **Priority**: Always check explicit aliases/crosswalks before fuzzy matching.
- **Algorithm**: Use `python-Levenshtein` or `rapidfuzz` for `ratio()` calculation.
- **Threshold**: 90% catches single-character typos in average-length names.
- **Preprocessing**: Normalize punctuation (Dr. → Dr), strip whitespace, lowercase.

### Revision/Amendment Handling
- Filter revisions by `approval_state == 'approved'` (or equivalent like `decision == 'approved'`).
- Group by `reference_id`, sort by revision/amendment number descending, take top 1.
- **Field Overrides**: Amendments may update multiple fields (amount, campus, status, zone). Apply all overridden fields from the latest approved revision.

### Dependencies
```bash
pip install --break-system-packages pdfplumber pandas openpyxl python-Levenshtein
```

## When Validation Fails

- **Module errors**: Use virtual environment or `--break-system-packages`.
- **Zero matches**: Lower fuzzy threshold to 80% temporarily to inspect near-misses.
- **Regex misses**: Print raw `page.extract_text()` to adjust patterns.
- **Amount parsing**: Normalize currency symbols and commas: `amount = float(re.sub(r'[$,]', '', amount_str))`

## Scripts

Use `scripts/validate_claims.py` as a template. Configure the `VALIDATION_CONFIG` dictionary for file paths, thresholds, and field mappings.

## References

- `references/fuzzy-matching-guide.md` - Algorithm details and threshold tuning
- `references/domain-examples.md` - Concrete field mappings for different domains (expense claims, speaker honorariums, vendor invoices, clinic shifts, field service work orders, fleet maintenance chargebacks, research stipends)
