---
name: financial-rollforward-workbook
description: Build Excel financial roll-forward workbooks from CSV/JSON source data. Use for deferred revenue schedules, prepaid expenses, fixed asset rolls, or any accounting work requiring Beginning + Additions - Releases = Ending tracking across periods with GL reconciliation.
---

# Financial Roll-Forward Workbook Builder

Build structured Excel workbooks for financial roll-forward schedules with automated formulas and GL reconciliation.

## When to Use

- Deferred revenue recognition schedules
- Prepaid expense amortization
- Fixed asset depreciation rolls
- Any account requiring period-to-period balance roll-forwards with Beginning + Additions - Releases = Ending logic

## Workflow

1. **Load Source Data**
   - Read CSVs into lists of dicts via `csv.DictReader`
   - Load GL control totals from JSON via `json.load`
   - Normalize numeric fields: `float(v) if v else 0.0`

2. **Structure the Workbook**
   - Create `Workbook()`, set sheet names in required order
   - **Detail sheets**: One per account (e.g., "SaaS Rev #2300")
   - **Control rows** at bottom of each detail sheet
   - **Summary sheet**: Cross-sheet links to control row totals

3. **Column Layout (per period group)**
   - Pattern: `Beginning | Additions | Releases | Ending Balance`
   - Roll-forward formula: `Ending = Previous Period Ending + Additions - Releases`

4. **Populate Detail Sheets**
   - Write headers at row 5
   - Write data rows starting at row 6
   - **Calculate control row positions dynamically**: `first_control_row = 6 + len(data_rows)`
   - Apply `#,##0.00` number format to monetary columns

5. **Control Row Structure (in order)**
   - **Period Totals**: SUM formulas for each activity column
   - **Calculated Ending Balance**: SUM of ending balance column from data rows
   - **Variance**: `=GL_Balance - Calculated_Ending`
   - **GL Balance**: Hard-coded value from JSON (NOT a formula)

6. **Build Summary Sheet**
   - Use cross-sheet references: `='Sheet Name'!CellRef`
   - Quote sheet names containing spaces or special characters
   - Link to control row values from each detail sheet

7. **Save & Verify**
   - Save as `.xlsx`
   - Run `scripts/verify_workbook.py` to validate structure

## Critical Formula Patterns

### Correct Ending Balance Formula
Do NOT create circular references. Reference the data rows directly:
```
=SUM(N6:N9)  # Sum of ending balance column from data rows
```

### Anti-Pattern: Circular References
| WRONG | RIGHT |
|-------|-------|
| `=B11+C11-D11` in row 11 (references itself) | `=SUM(E6:E9)` where rows 6-9 contain the data |

### GL Balance Row
- Must be a **separate row** with **hard-coded GL value**
- GL Balance goes in the ending balance column (typically column N/14)
- Variance = GL Balance - Calculated Ending Balance

## Cross-Sheet References
- Syntax: `='Sheet Name'!O10`
- Use single quotes around sheet names with spaces or special characters
- Summary totals: `=B9+B15` (sum across account sections)

## Anti-Patterns

- **Don't** hardcode control row indices; calculate from `len(data_rows) + first_data_row`
- **Don't** create formulas that reference their own row (circular references)
- **Don't** write GL Balance as a formula; it must be a hard-coded value
- **Don't** place GL Balance in wrong column; use the ending balance column
- **Don't** write numeric values as strings; convert CSV floats explicitly
- **Don't** forget the `=` prefix when assigning formulas to cells

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### deferred-revenue-rollforward
- Control rows must be dynamically positioned based on data row count
- GL Balance row must be separate and hard-coded (not a formula)
- Variance = GL Balance - Calculated Ending Balance (not reversed)
- Circular references cause immediate verifier failure

## Validation Steps

1. **Check for circular references**: Open workbook and verify no circular reference warnings
2. **Verify formula dependencies**: Each formula should only reference cells above it or data rows
3. **Cross-foot totals**: Sum of customer ending balances should equal calculated ending balance
4. **GL reconciliation**: Variance should be zero or explainable difference

## Common Failure Modes

| Issue | Cause | Fix |
|-------|-------|-----|
| Circular reference | Formula references its own row | Reference data rows instead |
| Wrong GL placement | GL in wrong column/row | Place GL in dedicated row, ending balance column |
| Missing links | Summary not linked to details | Use sheet references like `='SaaS Rev #2300'!O10` |
| Variance miscalc | Subtracting wrong direction | Variance = GL - Calculated Ending |

## Scripts

- `scripts/build_rollforward.py` - Working template with correct formula patterns
- `scripts/verify_workbook.py` - Validates structure and formulas after generation
