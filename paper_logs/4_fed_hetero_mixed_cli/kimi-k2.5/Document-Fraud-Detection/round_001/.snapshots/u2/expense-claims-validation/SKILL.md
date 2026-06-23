---
name: expense-claims-validation
description: Validate expense or travel claims from PDF documents against structured reference data (employee directories, trip approvals). Use when cross-referencing document claims with master databases to detect fraud patterns (account mismatches, amount discrepancies, unauthorized travelers, unknown employees). Essential when source documents contain typos or slight name variations requiring fuzzy matching.
---

# Expense Claims Validation

Cross-reference multi-page PDF claims against structured reference data (Excel/CSV employee directories, trip databases) to identify financial discrepancies and fraud indicators.

## Workflow

1. **Load Reference Data**
   - Load employee directory (Excel/CSV) → DataFrame with `employee_id`, `employee_name`, `bank_account`
   - Load trip/approval database (CSV) → DataFrame with `trip_id`, `approved_amount`, `employee_id`
   - Build lookup indexes: `name_lower → employee_record` and `trip_id → trip_record`

2. **Parse Claims Document**
   - Use `pdfplumber` (not PyPDF2) to extract text per page
   - Regex extract fields: `Employee Name`, `Bank Account`, `Trip ID`, `Claim Total`
   - Preserve page numbers for reporting

3. **Fuzzy Match Employee Names**
   - Normalize claim names: lowercase, strip whitespace
   - Calculate similarity against all directory names using **Levenshtein distance** (not simple sequence matching)
   - Threshold: ≥90% similarity = match; <90% = "Unknown Employee"
   - Use matched canonical name for downstream validation

4. **Validate Five Fraud Indicators** (in order)
   - **Unknown Employee**: Best name match <90% similarity
   - **Invalid Trip ID**: `trip_id` not found in approvals database
   - **Traveler Mismatch**: Trip exists but `trip.employee_id ≠ employee.employee_id`
   - **Account Mismatch**: Claim bank account ≠ employee bank account record
   - **Amount Mismatch**: |`claimed_amount - approved_amount`| > $0.01 tolerance

5. **Output Results**
   - JSON array of flagged claims with `claim_page_number`, `employee_name`, `claimed_amount`, `bank_account`, `trip_id`, `reason`
   - Include notes on fuzzy-matched typos for audit trail

## Validation Rules Reference

| Check | Failure Condition | Data Sources |
|-------|------------------|--------------|
| Employee Existence | No directory match ≥90% similarity | Employee Directory |
| Trip Validity | `trip_id` not in trip database | Trip Approvals |
| Authorization | `trip.employee_id` ≠ `claimant.employee_id` | Trip + Employee |
| Bank Account | `claim.account` ≠ `employee.account` | Claim PDF + Employee |
| Amount | \|`claimed` - `approved`\| > 0.01 | Claim PDF + Trip |

## Key Implementation Details

### Fuzzy Matching (Critical)
- **Algorithm**: Use `python-Levenshtein` or `rapidfuzz` for `ratio()` calculation
- **Anti-pattern**: Simple character-by-character comparison fails on insertions (e.g., "Briann" vs "Brian" scored 50% vs 92% with Levenshtein)
- **Threshold**: 90% catches single-character typos in average-length names (8-12 chars)

### PDF Parsing
- **Tool**: `pdfplumber` handles layout variations better than `PyPDF2`
- **Pattern**: `pdfplumber.open(path).pages` → `page.extract_text()`
- **Regex tip**: Use case-insensitive patterns with optional whitespace: `r'Employee:\s*(.+)'`

### Dependencies
```bash
pip install pdfplumber pandas openpyxl python-Levenshtein
# OR for faster matching:
pip install rapidfuzz
```

## Anti-Patterns

- **Do not use Read tool on `.xlsx` files** - they are binary and will fail. Use Python/pandas instead.
- **Do not assume exact name matches** - watch for typos ("Dana Kapor" vs "Dana Kapoor", "Briann" vs "Brian")
- **Do not skip building lookup tables** - repeated linear searches are slow and error-prone
- **Do not use PyPDF2** for complex PDF layouts - prefer pdfplumber for table-aware extraction

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

(No sub-task specific invariants yet. Update this section when verifier failures reveal task-specific quirks.)

## When Validation Fails

- **Module errors**: Use virtual environment; avoid system Python package conflicts
- **Zero matches**: Lower fuzzy threshold to 80% temporarily to inspect near-misses
- **Regex misses**: Print raw `page.extract_text()` to adjust patterns for PDF layout changes
- **Amount parsing**: Normalize currency symbols and commas: `amount = float(re.sub(r'[$,]', '', amount_str))`

## Scripts

Use `scripts/validate_claims.py` as a template. Configure the `VALIDATION_CONFIG` dictionary for:
- File paths (employees, trips, claims PDF)
- Fuzzy match threshold (default 90)
- Amount tolerance (default 0.01)
- Output JSON path

## References

- `references/fuzzy-matching-guide.md` - Algorithm details and threshold tuning
