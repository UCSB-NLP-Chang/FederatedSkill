---
name: financial-rollforward-workbook
description: Build multi-period financial roll-forward workbooks in Excel using openpyxl. Use for deferred revenue schedules, prepaid expense amortization, fixed asset rolls, or any account requiring Beginning + Additions - Releases = Ending tracking across periods with GL reconciliation and cross-sheet summary links.
---

# Financial Rollforward Workbook Builder

## When to Use
- Deferred revenue rollforward schedules with GL reconciliation
- Prepaid expense amortization tracking
- Fixed asset depreciation rolls
- Any month-end close workpaper requiring period-to-period balance rollforwards
- Multi-customer, multi-period revenue recognition tracking

## Rollforward Structure

A financial rollforward follows this pattern for each period:
```
Beginning Balance + Additions (Billings) - Releases (Recognition) = Ending Balance
```

The Ending Balance of one period becomes the Beginning Balance of the next.

## Workflow

1. **Load Source Data**: Read CSVs into lists of dicts via `csv.DictReader`, JSON via `json.load`. Normalize numeric fields to float: `float(v) if v else 0.0`.
2. **Initialize Workbook**: Create `Workbook()`, set sheet names in required order.
3. **Populate Detail Sheets**:
   - Write headers at row 5.
   - Write data rows starting at row 6. Apply `#,##0.00` number format to monetary columns.
   - Compute control row positions dynamically: `totals_row = first_data_row + len(data_rows)`, then increment for each control row.
   - Write control rows with labels and formulas.
4. **Build Summary Sheet**:
   - Map summary cells to control rows on detail sheets using cross-sheet references: `='Sheet Name'!CellRef`.
   - Quote sheet names containing spaces or special characters.
5. **Save & Verify**: Save to `.xlsx`. Run `scripts/verify_workbook.py` to validate structure.

## Required Workbook Layout

### Detail Sheets (one per account)
- Row 5: Column headers
- Rows 6+: Line items with actual data values
- Control rows after data (positions computed dynamically):
  - **Period Totals**: SUM formulas for each activity column
  - **Calculated Ending Balance**: Sum of ending balance values from data rows (NOT a rollforward formula on control rows)
  - **Variance**: GL Balance minus Calculated Ending Balance
  - **GL Balance**: Hard-coded value from source JSON (NOT a formula)

### Summary Sheet
- Company name and period ending date
- Links to control row values from each detail sheet via cross-sheet references
- Total GL Balance aggregation across accounts

## Critical Formula Patterns

### Control Rows — Dynamic Positioning
```python
totals_row = start_row + len(data_rows)
calc_ending_row = totals_row + 1
variance_row = calc_ending_row + 1
gl_row = variance_row + 1
```

### Period Totals — SUM of Data Rows
```
=SUM(B6:B9)     # for each activity column, adjust range for actual data rows
```

### Calculated Ending Balance — NOT Self-Referencing
WRONG (circular): `=B11+C11-D11` in row 11 (row 11 IS the ending row, references itself)
RIGHT: `=SUM(N6:N9)` where rows 6-9 contain data rows

### GL Balance Row
- Must be a SEPARATE row with hard-coded GL value from JSON
- Place in the ending balance column for the final period
- Variance = GL Balance - Calculated Ending Balance

### Cross-Sheet References
```
='SaaS Rev #2300'!N10
='Services Rev #2310'!N12
```
Always quote sheet names with spaces or special characters (#).

## Anti-Patterns

| Issue | Cause | Fix |
|-------|-------|-----|
| Circular reference | Formula references its own row | Use SUM over data rows; never reference the row containing the formula |
| Hardcoded control row indices | Different sheets have different data counts | Compute: `totals_row = start_row + len(data_rows)` |
| Wrong GL placement | GL in wrong column/row or as formula | Place GL in dedicated row, hard-code value from JSON |
| Missing cross-sheet links | Summary uses hard-coded values | Use `='SheetName'!CellRef` syntax |
| Variance miscalc | Subtracting wrong direction | Variance = GL Balance - Calculated Ending |
| Numeric values as strings | CSV values not converted | Convert to float before writing: `float(v) if v else 0.0` |
| Missing `=` prefix | Formula stored as text | All formula strings must start with `=` |

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Number Formatting

Apply `#,##0.00` number format to monetary columns during data population:
```python
cell.number_format = '#,##0.00'
```
This is display-only; the underlying value remains full precision.

## Known invariants (by sub-task)

### deferred-revenue-rollforward
- Control row positions must be dynamically computed from data row count — never hardcoded (R0 u1: circular references from hardcoded row 11)
- GL Balance row must be a separate row with hard-coded value, not a formula (R0 u1: GL Balance was placed in wrong column/row)
- Calculated Ending Balance must sum ending balance values from data rows, NOT compute from control row formulas
- Variance = GL Balance - Calculated Ending Balance, not the reverse
- Cross-sheet references must use exact sheet names with single quotes for names containing spaces or `#` (e.g., `='SaaS Rev #2300'!N10`)
- Summary sheet must use cross-sheet references, not hard-coded values

### prepaid-expense-amortization
- (Reserved for future sub-tasks — document invariants as failures surface)

### fixed-asset-roll
- (Reserved for future sub-tasks — document invariants as failures surface)

## Scripts

- `scripts/build_rollforward.py` — Working template for deferred revenue rollforward with correct formula patterns and dynamic row calculation. Adapt column layout and account names per task.
- `scripts/verify_workbook.py` — Validates workbook structure: sheet order, headers, control row labels, and formula syntax.

## Validation Steps

1. **Check for circular references**: Verify no formula references its own row
2. **Verify formula dependencies**: Each formula should only reference data rows or other control rows above it
3. **Cross-foot totals**: Sum of line item ending balances should equal calculated ending balance
4. **GL reconciliation**: Variance should be zero
5. **Run verify script**: `python3 scripts/verify_workbook.py <workbook_path>`
