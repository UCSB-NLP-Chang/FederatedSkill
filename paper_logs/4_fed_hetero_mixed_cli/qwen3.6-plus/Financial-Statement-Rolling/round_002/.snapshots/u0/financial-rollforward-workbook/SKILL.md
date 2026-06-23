---
name: financial-rollforward-workbook
description: Build multi-period financial roll-forward workbooks in Excel using openpyxl. Use for deferred revenue schedules, prepaid expense amortization, fixed asset rolls, accrual rollforwards, or any account requiring Beginning + Additions - Releases = Ending tracking across periods with GL reconciliation and cross-sheet summary links.
---

# Financial Rollforward Workbook Builder

## When to Use
- Deferred revenue rollforward schedules with GL reconciliation
- Prepaid expense amortization tracking
- Fixed asset depreciation rolls
- Accrual rollforward schedules (payroll, bonus, etc.)
- Any month-end close workpaper requiring period-to-period balance rollforwards
- Multi-customer, multi-period revenue recognition tracking

## STOP: Read This First — The Circular Reference Trap

**The #1 cause of verifier failure is circular references.**

When control rows contain formulas that reference their own row, Excel creates circular references:

**WRONG (circular — row 10 IS the Ending Balance control row):**
```
Row 10 (Ending Balance):
  E10: =B10+C10-D10    ← E10 references itself! Row 10 is the control row.
  H10: =E10+F10-G10    ← E10 is on this same row!
  K10: =H10+I10-J10    ← H10 is on this same row!
```

**RIGHT (sum data rows, no self-reference):**
```
Row 10 (Ending Balance):
  E10: =SUM(E6:E8)     ← Sum Sep Ending Balance from data rows 6-8
  H10: =SUM(H6:H8)     ← Sum Oct Ending Balance from data rows 6-8
  K10: =SUM(K6:K8)     ← Sum Nov Ending Balance from data rows 6-8
```

**Mandatory checkpoint before writing control row formulas:**
Ask yourself: "Does this formula reference any cell on the SAME row I'm writing?"
- If YES → STOP. Use SUM of data rows instead.
- If NO → Proceed.

**The Rule: Control row ending balances must SUM the ending balance column from data rows. NEVER use rollforward formulas (=Beginning+Adds-Releases) on control rows.**

This applies to ALL ending balance columns (intermediate periods and final), not just the last period.

---

## Rollforward Structure

A financial rollforward follows this pattern for each period:
```
Beginning Balance + Additions (Billings/Accruals) - Releases (Recognition/Payments) = Ending Balance
```

The Ending Balance of one period becomes the Beginning Balance of the next.

## Multi-Period Column Layout

For schedules with multiple periods (e.g., monthly quarters), repeat this column group:

| Column Group | Purpose | Example (Sep) | Example (Oct) | Example (Nov) |
|-------------|---------|---------------|---------------|---------------|
| Beginning | Start balance | Beginning Balance | (Sep Ending becomes Oct Beginning) | (Oct Ending becomes Nov Beginning) |
| Additions | New activity | Sep Accruals/Billings | Oct Accruals/Billings | Nov Accruals/Billings |
| Releases | Reductions | Sep Releases/Recognition | Oct Releases/Recognition | Nov Releases/Recognition |
| Ending | Calculated balance | Sep Ending Balance | Oct Ending Balance | Nov Ending Balance |

**Data rows**: Each row's ending balance values are pre-calculated. Control rows summarize these values.

---

## Workflow

1. **Load Source Data**: Read CSVs into lists of dicts via `csv.DictReader`, JSON via `json.load`. Normalize numeric fields to float: `float(v) if v else 0.0`.

2. **Initialize Workbook**: Create `Workbook()`, set sheet names in required order.
   ```python
   # Delete default sheet if present
   if "Sheet" in wb.sheetnames:
       wb.remove(wb["Sheet"])
   # Create sheets with explicit index positions
   ws_detail1 = wb.create_sheet("Account #2105", 0)
   ws_summary = wb.create_sheet("Summary", 1)
   ```

3. **Populate Detail Sheets**:
   - Write headers at row 5.
   - Write data rows starting at row 6. Apply `#,##0.00` number format to monetary columns.
   - Compute control row positions dynamically: `totals_row = first_data_row + len(data_rows)`.
   - Write control rows with labels and formulas.

4. **Build Control Rows** (in order, after all data rows):

   Calculate positions:
   ```python
   totals_row = start_row + len(data_rows)
   calc_ending_row = totals_row + 1
   variance_row = calc_ending_row + 1
   gl_row = variance_row + 1
   ```

   **Period Totals row**: SUM each activity column from data rows.
   ```python
   for col in range(2, 12):  # Adjust range for your columns
       col_letter = get_column_letter(col)
       ws.cell(row=totals_row, column=col, value=f"=SUM({col_letter}{start_row}:{col_letter}{end_row})")
   ```

   **Calculated Ending Balance row**: SUM of ending balance columns from data rows (never rollforward formula).
   ```python
   # For each ending balance column, sum the data rows
   ws.cell(row=calc_ending_row, column=5, value=f"=SUM(E{start_row}:E{end_row})")  # Sep Ending
   ws.cell(row=calc_ending_row, column=8, value=f"=SUM(H{start_row}:H{end_row})")  # Oct Ending
   ws.cell(row=calc_ending_row, column=11, value=f"=SUM(K{start_row}:K{end_row})")  # Nov Ending
   ```

   **GL Balance row**: Hard-coded values from JSON in each period's ending balance column (never a formula).
   ```python
   # Column E (Sep Ending) gets GL value for Sep
   ws.cell(row=gl_row, column=5, value=gl_data['sep'])
   # Column H (Oct Ending) gets GL value for Oct
   ws.cell(row=gl_row, column=8, value=gl_data['oct'])
   ```

   **Variance row**: `=GL_Balance - Calculated_Ending` for each period.
   ```python
   # Sep Variance in column E
   ws.cell(row=variance_row, column=5, value=f"=E{gl_row}-E{calc_ending_row}")
   # Oct Variance in column H
   ws.cell(row=variance_row, column=8, value=f"=H{gl_row}-H{calc_ending_row}")
   ```

5. **Build Summary Sheet**:
   - Map summary cells to control rows using cross-sheet references: `='Sheet Name'!CellRef`.
   - Quote sheet names containing spaces or special characters: `='Payroll Accrual #2105'!L{totals_row}`.
   - Total GL Balance: Sum of individual GL cells from each detail sheet.

6. **Save & Verify**: Save to `.xlsx`. Run `scripts/verify_workbook.py` to validate structure.

---

## Cross-Sheet References

Syntax: `='Sheet Name'!O10`

Always quote sheet names with spaces or special characters (#):
```python
ws_summary.cell(row=7, column=2, value=f"='Payroll Accrual #2105'!E{gl_row}")
```

---

## Anti-Patterns

| Issue | Wrong | Right |
|-------|-------|-------|
| Circular reference | `=B10+C10-D10` on row 10 (control row) | `=SUM(E6:E8)` referencing data rows only |
| Hardcoded control row indices | `ws.cell(row=11, ...)` | `ws.cell(row=end_row+1, ...)` |
| Wrong GL placement | GL in wrong column or as formula | Place GL in dedicated row, hard-code value from JSON |
| Missing cross-sheet links | Summary uses hard-coded values | Use `='SheetName'!CellRef` syntax |
| Variance miscalc | Subtracting wrong direction | Variance = GL Balance - Calculated Ending |
| Numeric values as strings | CSV values not converted | Convert to float: `float(v) if v else 0.0` |
| Missing `=` prefix | `"SUM(B6:B9)"` | `"=SUM(B6:B9)"` |
| GL Balance as formula | `=L9-L10` in GL row | Hard-coded JSON value |
| Missing period variance | Only final column variance | Add variance for each period's ending column |

---

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

---

## Number Formatting

Apply `#,##0.00` number format to monetary columns during data population:
```python
cell.number_format = '#,##0.00'
```
This is display-only; the underlying value remains full precision.

---

## Known invariants (by sub-task)

### deferred-revenue-rollforward
- Control row labels must be exactly: "Period Totals", "Calculated Ending Balance", "Variance", "GL Balance"
- GL Balance in column N (14), hard-coded from JSON
- Summary sheet must have company name in row 1, period ending in row 2
- Variance must equal zero when GL ties to calculated ending
- Cross-sheet references must use single quotes for names with spaces or `#`

### accrual-rollforward
- Control row labels: "Period Totals", "Ending Balance", "Variance", "GL Balance"
- Ending Balance control row: SUM of ending balance columns from data rows, NOT rollforward formula
- GL Balance values come from JSON keyed by period (e.g., `gl_balances['payroll_accrual_2105']['nov']`)
- Per-period GL placement: GL value goes in each period's ending balance column
- Per-period variance: `=GL - Calculated_Ending` for each period column
- Summary sheet row positions are often specified exactly (e.g., B7-B9, B12-B14, B16)

### prepaid-expense-amortization
- (Reserved for future sub-tasks)

### fixed-asset-roll
- (Reserved for future sub-tasks)

---

## Verification

Run `scripts/verify_workbook.py <path_to_xlsx>` after generation. The script checks:
- Sheet existence and order
- Headers at row 5
- Control row labels
- **Circular reference detection** (formula referencing its own row)
- Cross-sheet reference syntax
- Formula syntax (`=` prefix)

---

## Scripts

- `scripts/build_rollforward.py` — Working template for deferred revenue rollforward with correct formula patterns and dynamic row calculation. Adapt column layout and account names per task.
- `scripts/verify_workbook.py` — Validates workbook structure and detects circular references.

---

## Validation Steps

1. **Run verify script**: `python3 scripts/verify_workbook.py <workbook_path>` — exits with error if circular references found
2. **Check formula dependencies**: Each formula should only reference data rows (rows 6 to end_row), never control rows
3. **Cross-foot totals**: Sum of line item ending balances should equal calculated ending balance
4. **GL reconciliation**: Variance should be zero for each period