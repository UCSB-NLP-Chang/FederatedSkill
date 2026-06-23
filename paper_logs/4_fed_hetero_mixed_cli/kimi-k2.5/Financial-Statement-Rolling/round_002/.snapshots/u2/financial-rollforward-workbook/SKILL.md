---
name: financial-rollforward-workbook
description: Build multi-period financial roll-forward workbooks in Excel using openpyxl. Use for deferred revenue schedules, prepaid expense amortization, fixed asset rolls, accrual rollforwards, or any account requiring Beginning + Additions - Releases = Ending tracking across periods with GL reconciliation and cross-sheet summary links.
---

# Financial Rollforward Workbook Builder

## STOP: Read This BEFORE Writing Any Formulas

**The #1 cause of verifier failure is circular references in control rows.**

Before writing any formula to a control row (Period Totals, Ending Balance, Variance, GL Balance), ask yourself:
> Does this formula reference any cell on the SAME row?

If YES → STOP. You are about to create a circular reference. Use SUM of data rows instead.

### The Circular Reference Trap

**WRONG (circular - row 10 IS the Ending Balance row):**
```
Row 10 (Ending Balance):
  E10: =B10+C10-D10    ← B10 is empty, D10 references this same row!
  H10: =E10+F10-G10    ← E10 is on this same row!
```

**RIGHT (sum data rows, no self-reference):**
```
Row 10 (Ending Balance):
  E10: =SUM(E6:E8)     ← Sum Sep Ending Balance from data rows 6-8
  H10: =SUM(H6:H8)     ← Sum Oct Ending Balance from data rows 6-8
```

### Why This Happens

The rollforward formula `Beginning + Adds - Releases = Ending` is correct for **data rows** where each column contains actual values. But on a **control row**, applying this formula creates a circular reference because the "Ending" cell you're computing is on the same row you're referencing.

### The Rule

**Control row ending balances must SUM the ending balance column from data rows, never use rollforward formulas.**

This applies to ALL ending balance columns (intermediate and final), not just the last period.

---

## When to Use

- Deferred revenue rollforward schedules with GL reconciliation
- Prepaid expense amortization tracking
- Fixed asset depreciation rolls
- Accrual rollforward schedules (payroll, bonus, etc.)
- Any month-end close workpaper requiring period-to-period balance rollforwards
- Multi-customer, multi-period revenue recognition tracking

---

## Rollforward Structure

A financial rollforward follows this pattern for each period:
```
Beginning Balance + Additions (Billings/Accruals) - Releases (Recognition/Payments) = Ending Balance
```

The Ending Balance of one period becomes the Beginning Balance of the next.

---

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

---

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

---

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

### GL Balance Row
- Must be a SEPARATE row with hard-coded GL value from JSON
- Place in the ending balance column for the final period
- Variance = GL Balance - Calculated Ending Balance

### Cross-Sheet References
```
='SaaS Rev #2300'!N10
='Services Rev #2310'!N12
='Payroll Accrual #2105'!L9
```
Always quote sheet names with spaces or special characters (#).

---

## Anti-Patterns

| Issue | Cause | Fix |
|-------|-------|-----|
| Circular reference | Rollforward formula on control row references its own row | SUM the ending balance column from data rows instead |
| Hardcoded control row indices | Different sheets have different data counts | Compute: `totals_row = start_row + len(data_rows)` |
| Wrong GL placement | GL in wrong column/row or as formula | Place GL in dedicated row, hard-code value from JSON |
| Missing cross-sheet links | Summary uses hard-coded values | Use `='SheetName'!CellRef` syntax |
| Variance miscalc | Subtracting wrong direction | Variance = GL Balance - Calculated Ending |
| Numeric values as strings | CSV values not converted | Convert to float before writing: `float(v) if v else 0.0` |
| Missing `=` prefix | Formula stored as text | All formula strings must start with `=` |

---

## Output Precision

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

## Known Invariants (by sub-task)

### deferred-revenue-rollforward
- Control row positions must be dynamically computed from data row count
- GL Balance row must be a separate row with hard-coded value, not a formula
- Calculated Ending Balance must sum ending balance values from data rows
- Variance = GL Balance - Calculated Ending Balance
- Cross-sheet references must use exact sheet names with single quotes for names containing spaces or `#`

### accrual-rollforward
- Same invariants as deferred-revenue
- Ending balance columns (intermediate and final) must SUM from data rows, NOT use rollforward formulas on control rows
- Typical columns: Beginning Balance, [Period] Accruals, [Period] Releases, [Period] Ending Balance per period
- GL Balance values come from JSON keyed by period (e.g., `gl_balances['payroll_accrual_2105']['nov']`)
- Per-period variance in each ending balance column

### prepaid-expense-amortization
- (Reserved for future sub-tasks)

### fixed-asset-roll
- (Reserved for future sub-tasks)

---

## Validation Checklist

1. **No circular references**: Open workbook and verify no circular reference warnings
2. **Control row formulas**:
   - Period Totals uses SUM of data rows
   - Calculated Ending uses SUM of ending balance column (data rows only)
   - GL Balance has hard-coded values (no formulas)
   - Variance references GL minus Calculated Ending
3. **Per-period reconciliation**: Each period column (Sep, Oct, Nov) has its own GL and Variance
4. **Cross-foot**: Sum of line item ending balances equals calculated ending balance

---

## Scripts

- `scripts/build_rollforward.py` — Working template for deferred revenue rollforward with correct formula patterns and dynamic row calculation. Adapt column layout and account names per task.
- `scripts/verify_workbook.py` — Validates workbook structure: sheet order, headers, control row labels, and formula syntax. Detects circular references.

Read `scripts/build_rollforward.py` when creating a new rollforward to see the correct pattern for:
- Dynamic control row positioning
- SUM formulas referencing data rows only
- Hard-coded GL placement
