---
name: financial-rollforward-workbook
description: Build multi-period financial rollforward workbooks with GL reconciliation. Use for deferred revenue schedules, prepaid expense amortization, fixed asset rolls, or any account requiring Beginning + Additions - Releases = Ending tracking across periods.
---

# Financial Rollforward Workbook Builder

## When to Use

- Deferred revenue recognition schedules (month-end close)
- Prepaid expense amortization rolls
- Fixed asset depreciation schedules
- Any account requiring period-to-period balance tracking with GL reconciliation

## Rollforward Structure

Every rollforward follows this pattern for each period:
```
Beginning Balance + Additions (Billings) - Releases (Recognition) = Ending Balance
```

The Ending Balance of one period becomes the Beginning Balance of the next.

## Workflow

1. **Load Source Data**: Read CSVs via `csv.DictReader`, JSON via `json.load`. Convert all numeric fields to `float(v) if v else 0.0`.
2. **Initialize Workbook**: Create `Workbook()` with sheet names matching account codes (e.g., "SaaS Rev #2300", "Services Rev #2310").
3. **Populate Detail Sheets**:
   - Write headers at row 5 (fixed position)
   - Write data rows starting at row 6
   - Compute control row positions dynamically: `first_control_row = first_data_row + len(data_rows)`
   - Apply `#,##0.00` number format to monetary columns during write
4. **Build Control Rows** (in order, after all data rows):
   - **Period Totals**: `=SUM(B6:B9)` for each activity column
   - **Calculated Ending Balance**: Sum of ending balance column from data rows (NOT self-referencing)
   - **GL Balance**: Hard-coded value from JSON (column N/14, separate row)
   - **Variance**: `=GL_Balance - Calculated_Ending`
5. **Build Summary Sheet**: Cross-sheet references to control rows: `='SaaS Rev #2300'!O10`
6. **Save & Verify**: Save as `.xlsx`, then run verification script.

## Critical Formula Patterns

### Correct Ending Balance Formula
The ending balance MUST reference data rows, not itself:
```python
# CORRECT: Sum ending balance column from data rows
ws.cell(row=calc_row, column=14, value=f"=SUM(N{start_row}:N{end_row})")

# WRONG: Self-referencing formula creates circular reference
ws.cell(row=11, column=14, value="=B11+C11-D11")  # Row 11 IS the ending row!
```

### Dynamic Row Calculation
```python
start_row = 6
end_row = start_row + len(data_rows) - 1
totals_row = end_row + 1
calc_ending_row = end_row + 2
variance_row = end_row + 3
gl_row = end_row + 4
```

### Cross-Sheet References
```python
# Quote sheet names with spaces or special characters
ws.cell(row=7, column=2, value=f"='SaaS Rev #2300'!O{totals_row}")
```

### GL Balance Placement
- **Column**: N (column 14) - hard-coded value from JSON, NOT a formula
- **Separate row**: Do NOT combine with other control rows
- **Variance formula**: `=N{gl_row}-N{calc_ending_row}` (GL minus Calculated)

## Anti-Patterns

| Issue | Wrong | Right |
|-------|-------|-------|
| Circular reference | `=B11+C11-D11` in row 11 | `=SUM(E6:E9)` referencing data rows |
| Hardcoded control rows | `ws.cell(row=11, ...)` | `ws.cell(row=end_row+1, ...)` |
| GL Balance formula | `=SUM(...)` | Hard-coded `gl_data.get('aug', 0)` |
| Missing `=` prefix | `"SUM(B6:B9)"` | `"=SUM(B6:B9)"` |
| Wrong GL column | Column O (15) | Column N (14) |

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### deferred-revenue-rollforward
- Control row labels must be exactly: "Period Totals", "Calculated Ending Balance", "Variance", "GL Balance"
- GL Balance in column N (14), hard-coded from JSON
- Summary sheet must have company name in row 1, period ending in row 2
- Variance must equal zero when GL ties to calculated ending

### prepaid-expense-amortization
- (Add sub-task specific invariants as they are discovered)

## Verification

Run `scripts/verify_workbook.py <path_to_xlsx>` after generation:
- Confirms sheet names match expected pattern
- Checks headers at row 5
- Validates control row labels exist
- Verifies formulas start with `=`
- Cross-references Summary links to detail sheets

## Scripts

- `scripts/build_rollforward.py` - Reference implementation for deferred revenue workbooks
- `scripts/verify_workbook.py` - Validation tool for workbook structure
