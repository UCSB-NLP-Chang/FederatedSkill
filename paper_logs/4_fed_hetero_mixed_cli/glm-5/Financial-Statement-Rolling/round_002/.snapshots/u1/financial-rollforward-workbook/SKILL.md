---
name: financial-rollforward-workbook
description: Build multi-period financial roll-forward workbooks in Excel using openpyxl. Use for deferred revenue schedules, prepaid expense amortization, fixed asset rolls, accrual rollforwards, or any account requiring Beginning + Additions - Releases = Ending tracking across periods with GL reconciliation and cross-sheet summary links.
---

# Financial Rollforward Workbook Builder

## STOP: READ THIS FIRST — Circular Reference Prevention

**The #1 failure mode is circular references from rollforward formulas on control rows.**

### The Rule
**Control row ending balances MUST SUM the ending balance column from data rows.**
**Never use rollforward formulas (=B+C-D) on control rows.**

### Why This Fails
The rollforward formula `Beginning + Adds - Releases = Ending` works on **data rows** where each column has actual values. But on a **control row**, using `=B10+C10-D10` creates a circular reference because:
- Row 10 IS the Ending Balance row
- The formula references B10, C10, D10 which are on the same row you're computing
- Those cells are empty or contain other formulas — circular dependency

### WRONG (Circular Reference)
```
Row 10 (Ending Balance control row):
  E10: =B10+C10-D10    ← B10 is on this same row!
  H10: =E10+F10-G10    ← E10 is on this same row!
  K10: =H10+I10-J10    ← K10 is on this same row!
```

### RIGHT (No Self-Reference)
```
Row 10 (Ending Balance control row):
  E10: =SUM(E6:E8)     ← Sum Sep Ending from data rows 6-8
  H10: =SUM(H6:H8)     ← Sum Oct Ending from data rows 6-8
  K10: =SUM(K6:K8)     ← Sum Nov Ending from data rows 6-8
```

### Checkpoint Before Writing Control Rows
**Before writing any formula to a control row, ask:**
1. Does this formula reference any cell on the SAME row?
2. If YES — STOP. Use SUM over data rows instead.

---

## When to Use
- Deferred revenue rollforward schedules with GL reconciliation
- Prepaid expense amortization tracking
- Fixed asset depreciation rolls
- Accrual rollforward schedules (payroll, bonus, etc.)
- Any month-end close workpaper requiring period-to-period balance rollforwards
- Multi-customer, multi-period revenue recognition tracking

## Multi-Period Column Layout

For schedules with multiple periods (e.g., Sep/Oct/Nov), the column pattern repeats:

| Period | Beginning | Additions | Releases | Ending Balance |
|--------|-----------|-----------|----------|----------------|
| Sep | Beg Balance (B) | Sep Accruals (C) | Sep Releases (D) | Sep Ending (E) |
| Oct | (Oct Beginning is Sep Ending in data rows) | Oct Accruals (F) | Oct Releases (G) | Oct Ending (H) |
| Nov | (Nov Beginning is Oct Ending in data rows) | Nov Accruals (I) | Nov Releases (J) | Nov Ending (K) |

**Key**: Each period's Ending Balance column gets its own GL placement and variance calculation.

## Rollforward Structure

A financial rollforward follows this pattern for each period:
```
Beginning Balance + Additions (Billings/Accruals) - Releases (Recognition/Payments) = Ending Balance
```

The Ending Balance of one period becomes the Beginning Balance of the next (implicit in data rows).

## Workflow

1. **Load Source Data**: Read CSVs into lists of dicts via `csv.DictReader`, JSON via `json.load`. Normalize numeric fields to float: `float(v) if v else 0.0`.
2. **Initialize Workbook**: Create `Workbook()`, set sheet names in required order.
3. **Populate Detail Sheets**:
   - Write headers at row 5.
   - Write data rows starting at row 6. Apply `#,##0.00` number format to monetary columns.
   - Compute control row positions dynamically: `totals_row = first_data_row + len(data_rows)`, then increment for each control row.
   - **Run checkpoint before writing control row formulas** (see STOP section above).
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
  - **Period Totals**: SUM formulas for each activity column from data rows
  - **Calculated Ending Balance**: SUM of ending balance values from data rows (NOT rollforward formula)
  - **Variance**: GL Balance minus Calculated Ending Balance (per-period for multi-period)
  - **GL Balance**: Hard-coded value from source JSON (NOT a formula)

### Summary Sheet
- Company name and period ending date
- Links to control row values from each detail sheet via cross-sheet references
- Total GL Balance aggregation across accounts

## Control Row Formula Patterns

### Dynamic Positioning
```python
totals_row = start_row + len(data_rows)
calc_ending_row = totals_row + 1
variance_row = calc_ending_row + 1
gl_row = variance_row + 1
```

### Period Totals — SUM of Data Rows
```python
for col in range(2, 12):  # Adjust range for your columns
    col_letter = get_column_letter(col)
    ws.cell(row=totals_row, column=col, value=f"=SUM({col_letter}{start_row}:{col_letter}{end_row})")
```

### Calculated Ending Balance — SUM Data Row Ending Balances
```python
# For each ending balance column, sum the data rows
ws.cell(row=calc_ending_row, column=5, value=f"=SUM(E{start_row}:E{end_row})")  # Sep Ending
ws.cell(row=calc_ending_row, column=8, value=f"=SUM(H{start_row}:H{end_row})")  # Oct Ending
ws.cell(row=calc_ending_row, column=11, value=f"=SUM(K{start_row}:K{end_row})")  # Nov Ending
```

### GL Balance Row — Hard-Coded Values
- Must be a SEPARATE row with hard-coded GL value from JSON
- For multi-period: place GL in each period's ending balance column
```python
# Sep GL in column E (Sep Ending column)
ws.cell(row=gl_row, column=5, value=gl_data['sep'])
# Oct GL in column H (Oct Ending column)
ws.cell(row=gl_row, column=8, value=gl_data['oct'])
# Nov GL in column K (Nov Ending column)
ws.cell(row=gl_row, column=11, value=gl_data['nov'])
```

### Variance — Per-Period Calculation
```python
# Sep Variance: GL - Calculated Ending
ws.cell(row=variance_row, column=5, value=f"=E{gl_row}-E{calc_ending_row}")
# Oct Variance
ws.cell(row=variance_row, column=8, value=f"=H{gl_row}-H{calc_ending_row}")
# Nov Variance
ws.cell(row=variance_row, column=11, value=f"=K{gl_row}-K{calc_ending_row}")
```

### Cross-Sheet References
```
='SaaS Rev #2300'!N10
='Services Rev #2310'!N12
='Payroll Accrual #2105'!L9
```
Always quote sheet names with spaces or special characters (#).

## Anti-Patterns

| Issue | Cause | Fix |
|-------|-------|-----|
| Circular reference | Rollforward formula on control row references its own row | SUM the ending balance column from data rows instead |
| Hardcoded control row indices | Different sheets have different data counts | Compute: `totals_row = start_row + len(data_rows)` |
| Wrong GL placement | GL in wrong column/row or as formula | Place GL in dedicated row, hard-code value from JSON |
| GL as formula | Using `=L9-L10` instead of hard-coded | Insert hard-coded values from JSON |
| Missing per-period variance | Only calculated variance for final column | Add variance formula for each period's ending balance column |
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
- Control row positions must be dynamically computed from data row count
- GL Balance row must be a separate row with hard-coded value, not a formula
- Calculated Ending Balance must sum ending balance values from data rows
- Variance = GL Balance - Calculated Ending Balance
- Cross-sheet references must use exact sheet names with single quotes for names containing spaces or `#`

### accrual-rollforward
- Same circular reference rules apply
- Ending balance columns (intermediate and final) must SUM from data rows, NOT use rollforward formulas on control rows
- Typical columns: Beginning Balance, [Period] Accruals, [Period] Releases, [Period] Ending Balance per period
- GL Balance values come from JSON keyed by period (e.g., `gl_balances['payroll_accrual_2105']['sep']`)
- Place GL in each period's ending balance column (E for Sep, H for Oct, K for Nov)
- Calculate variance per-period, not just final total

### prepaid-expense-amortization
- (Reserved for future sub-tasks)

### fixed-asset-roll
- (Reserved for future sub-tasks)

## Scripts

- `scripts/build_rollforward.py` — Working template for deferred revenue rollforward with correct formula patterns and dynamic row calculation. Adapt column layout and account names per task.
- `scripts/verify_workbook.py` — Validates workbook structure: sheet order, headers, control row labels, formula syntax, and **detects circular references**.

## Validation Steps

1. **Run verify script FIRST**: `python3 scripts/verify_workbook.py <workbook_path>` — it detects circular references
2. **Check for circular references**: Verify no formula references its own row
3. **Verify formula dependencies**: Each formula should only reference data rows or other control rows above it
4. **Cross-foot totals**: Sum of line item ending balances should equal calculated ending balance
5. **GL reconciliation**: Variance should be zero