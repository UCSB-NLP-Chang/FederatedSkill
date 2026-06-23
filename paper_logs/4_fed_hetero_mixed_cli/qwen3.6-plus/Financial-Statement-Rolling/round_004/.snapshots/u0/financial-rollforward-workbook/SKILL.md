---
name: financial-rollforward-workbook
description: Build multi-period financial roll-forward workbooks in Excel using openpyxl. Use for deferred revenue schedules, prepaid expense amortization, fixed asset rolls, accrual rollforwards, warranty reserves, or any account requiring Beginning + Additions - Releases = Ending tracking across periods with GL reconciliation and cross-sheet summary links.
---

# Financial Rollforward Workbook Builder

## STOP: READ THIS BEFORE ANYTHING ELSE

**The #1 cause of verifier failure is circular references in control rows.**

### The Two Types of Rows

| Row Type | What It Contains | Formula for Ending Balance |
|----------|------------------|---------------------------|
| **Data rows** | Individual line items (customers, claim groups, etc.) | Rollforward formula: `=B{r}+C{r}-D{r}` |
| **Control rows** | Aggregates (Period Totals, Ending Balance, Variance, GL Balance) | SUM of data rows: `=SUM(E6:E8)` |

### The Category Error

Applying `=B10+C10-D10` to row 10 (which IS the Ending Balance control row) is wrong because:
- Row 10 is the row you're computing
- B10, C10, D10 are empty or contain other formulas
- The formula references itself → circular reference

### MANDATORY PRE-WRITE CHECKPOINT

Before writing any formula to a row, run this checkpoint:

**STEP 1:** Check the row label. Is it one of: Period Totals, Ending Balance, Calculated Ending Balance, Variance, GL Balance?
- If YES → This is a CONTROL ROW. Go to STEP 2.
- If NO → This is a DATA ROW. Use rollforward formula: `=B{r}+C{r}-D{r}`

**STEP 2:** For control rows, does the formula reference ANY cell on the same row?
- If YES → STOP. Use SUM of data rows instead.
- If NO → Proceed.

```python
# CORRECT PATTERN — Check row type first
if row_label in ["Period Totals", "Ending Balance", "Calculated Ending Balance", "Variance", "GL Balance"]:
    # CONTROL ROW — use SUM of data rows only
    ws.cell(row=r, column=end_col, value=f"=SUM({col_letter}{data_start}:{col_letter}{data_end})")
else:
    # DATA ROW — rollforward formula is correct
    ws.cell(row=r, column=end_col, value=f"=B{r}+C{r}-D{r}")
```

### NEVER Put Formulas in Non-Monetary Columns

Columns like "Useful Life Months", "Notes", "Asset Account", or any metadata columns contain text/values only. **Never place formulas in non-monetary columns.**

```python
# WRONG: Formula in non-monetary column
ws.cell(row=totals_row, column=15, value=f"=SUM(O{start_row}:O{end_row})")  # O is Useful Life

# RIGHT: Skip non-monetary columns when writing Period Totals
for col in monetary_columns_only:  # Only iterate monetary columns
    ws.cell(row=totals_row, column=col, value=f"=SUM({col_letter}{start_row}:{col_letter}{end_row})")
```

---

## Data Rows vs Control Rows — Critical Distinction

### Data Rows (Line Items)
Data rows contain individual line items (customers, claim groups, assets).

**Ending balance columns on data rows SHOULD use rollforward formulas:**
```python
# Sep Ending = Beginning + Sep Additions - Sep Releases
ws.cell(row=r, column=5, value=f"=B{r}+C{r}-D{r}")
# Oct Ending = Sep Ending + Oct Additions - Oct Releases
ws.cell(row=r, column=8, value=f"=E{r}+F{r}-G{r}")
```

### Control Rows (Totals, Reconciliation)
Control rows aggregate data rows and reconcile to GL.

**Ending balance columns on control rows MUST SUM from data rows:**
```python
# Sum Sep Ending from all data rows
ws.cell(row=calc_ending_row, column=5, value=f"=SUM(E{start_row}:E{end_row})")
# Sum Oct Ending from all data rows
ws.cell(row=calc_ending_row, column=8, value=f"=SUM(H{start_row}:H{end_row})")
```

---

## When to Use

- Deferred revenue rollforward schedules with GL reconciliation
- Prepaid expense amortization tracking
- Fixed asset depreciation rolls
- Warranty reserve schedules with claims tracking
- Accrual rollforward schedules (payroll, bonus, etc.)
- Any month-end close workpaper requiring period-to-period balance rollforwards
- Multi-customer, multi-period revenue recognition tracking

---

## Rollforward Structure

A financial rollforward follows this pattern for each period:
```
Beginning Balance + Additions (Billings/Accruals/Incurred) - Releases (Recognition/Payments/Claims Paid) = Ending Balance
```

The Ending Balance of one period becomes the Beginning Balance of the next (implicit in data rows).

---

## Workflow

1. **Load Source Data**: Read CSVs into lists of dicts via `csv.DictReader`, JSON via `json.load`. Normalize numeric fields to float: `float(v) if v else 0.0`. Filter to `record_status == 'active'` if a status column exists.

2. **Sort Data**: Sort alphabetically by key field (customer name, claim group, etc.) before writing rows.

3. **Initialize Workbook**: Create `Workbook()`, delete default "Sheet" if present, create detail sheets and summary sheet in required order.

4. **Populate Detail Sheets**:
   - Write headers at row 5.
   - Write data rows starting at row 6. Apply `#,##0.00` number format to monetary columns.
   - Compute control row positions dynamically: `totals_row = start_row + len(data_rows)`, then increment for each control row.
   - **RUN MANDATORY CHECKPOINT** before writing any control row formula (see STOP section).
   - Write control rows with labels and formulas.

5. **Build Summary Sheet**:
   - Map summary cells to control rows using cross-sheet references: `='Sheet Name'!CellRef`.
   - Link Ending Balance and GL Balance to the **final period's ending balance column** (e.g., column N for Sep), NOT to totals columns.
   - Quote sheet names containing spaces or special characters (#).

6. **Save**: Save to `.xlsx`.

7. **VERIFY (MANDATORY)**: Run `python3 scripts/verify_workbook.py <path>` from the skill directory. **Do NOT claim success until exit code is 0.**

---

## Control Row Formula Patterns

### Dynamic Positioning
```python
totals_row = start_row + len(data_rows)
calc_ending_row = totals_row + 1
variance_row = calc_ending_row + 1
gl_row = variance_row + 1
```

### Period Totals — SUM of Data Rows (Monetary Columns Only)
```python
for col in range(2, 15):  # Adjust range for your MONETARY columns only
    col_letter = get_column_letter(col)
    ws.cell(row=totals_row, column=col, 
           value=f"=SUM({col_letter}{start_row}:{col_letter}{end_row})")
# Skip non-monetary columns (Useful Life, Notes, Asset Account, etc.)
```

### Calculated Ending Balance — SUM Data Row Ending Balances
```python
# For each ending balance column, sum the data rows
ws.cell(row=calc_ending_row, column=5, value=f"=SUM(E{start_row}:E{end_row})")  # Sep Ending
ws.cell(row=calc_ending_row, column=8, value=f"=SUM(H{start_row}:H{end_row})")  # Oct Ending
ws.cell(row=calc_ending_row, column=11, value=f"=SUM(K{start_row}:K{end_row})")  # Nov Ending
```

### GL Balance Row — Hard-Coded Values
```python
# Place GL in each period's ending balance column
ws.cell(row=gl_row, column=5, value=gl_data['sep'])
ws.cell(row=gl_row, column=8, value=gl_data['oct'])
ws.cell(row=gl_row, column=11, value=gl_data['nov'])
```

### Variance — Per-Period Calculation
```python
ws.cell(row=variance_row, column=5, value=f"=E{gl_row}-E{calc_ending_row}")  # Sep Variance
ws.cell(row=variance_row, column=8, value=f"=H{gl_row}-H{calc_ending_row}")  # Oct Variance
```

---

## Cross-Sheet References

Syntax: `='Sheet Name'!CellRef`

Always quote sheet names with spaces or special characters:
```python
ws_summary.cell(row=7, column=2, value=f"='Payroll Accrual #2105'!E{gl_row}")
```

### Summary Sheet Linking (CRITICAL)

Link Ending Balance and GL Balance to the **final period's ending balance column**:

```python
# WRONG: Links to calculated totals column
ws_summary.cell(row=r, column=2, value="='Consumer Warranty #2440'!O10")  # O is totals

# RIGHT: Links to final period ending balance column
ws_summary.cell(row=r, column=2, value="='Consumer Warranty #2440'!N10")  # N is Sep Ending
```

---

## Anti-Patterns

| Issue | Wrong | Right |
|-------|-------|-------|
| Circular reference | `=B10+C10-D10` on row 10 (control row) | `=SUM(E6:E8)` referencing data rows only |
| Rollforward on control row | Using `=B+C-D` pattern on totals rows | Control rows must SUM from data rows |
| Hardcoded control row indices | `ws.cell(row=11, ...)` | `ws.cell(row=end_row+1, ...)` |
| Wrong GL placement | GL in wrong column or as formula | Place GL in dedicated row, hard-code value from JSON |
| Summary links to totals | Confusing totals column with ending balance | Link to final period's ending balance column |
| Missing cross-sheet links | Summary uses hard-coded values | Use `='SheetName'!CellRef` syntax |
| Variance miscalc | Subtracting wrong direction | Variance = GL Balance - Calculated Ending |
| Numeric values as strings | CSV values not converted | Convert to float: `float(v) if v else 0.0` |
| Missing `=` prefix | `"SUM(B6:B9)"` | `"=SUM(B6:B9)"` |
| Including archived records | Not filtering source data | Filter to `record_status == 'active'` |
| Skipping verification | Claiming success without running verify | Always run verify script first |
| Formula in non-monetary column | SUM in Useful Life/Notes column | Skip non-monetary columns in control row formulas |

---

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs. Pass raw float values directly:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision.

---

## Number Formatting

Apply `#,##0.00` number format to monetary columns:
```python
cell.number_format = '#,##0.00'
```
This is display-only; the underlying value remains full precision.

---

## Known Invariants (by sub-task)

### deferred-revenue-rollforward
- Control row labels: "Period Totals", "Calculated Ending Balance", "Variance", "GL Balance"
- GL Balance in column N (14), hard-coded from JSON
- Summary must have company name row 1, period ending row 2
- Variance must equal zero when GL ties
- Cross-sheet references must use single quotes for names with spaces or `#`

### accrual-rollforward
- Same invariants as deferred-revenue
- Ending balance columns must SUM from data rows on control rows, NOT rollforward formulas
- Typical columns: Beginning Balance, [Period] Accruals, [Period] Releases, [Period] Ending per period
- GL values keyed by period: `gl_balances['payroll_accrual_2105']['nov']`
- Per-period variance in each ending balance column

### warranty-reserve-rollforward
- Filter to `record_status == 'active'` only; exclude archived records
- Sort alphabetically by claim group name
- Typical columns: Claim Group, Beginning Balance, [Period] Incurred, [Period] Claims Paid, [Period] Ending per period
- GL values from JSON keyed by account and period
- **Summary must link to final period's ending balance column** (e.g., N for Sep), NOT totals column (O)
- Place GL in each period's ending balance column
- Per-period variance calculation

### prepaid-expense-amortization
- (Reserved for future sub-tasks)

### fixed-asset-roll
- (Reserved for future sub-tasks)

---

## Verification

**MANDATORY**: Run `scripts/verify_workbook.py <path>` after generation.

The script checks:
- Sheet existence and order
- Headers at row 5
- Control row labels
- **Circular reference detection** (formula referencing its own row)
- Cross-sheet reference syntax
- Formula syntax (`=` prefix)

Run from the skill directory:
```bash
python3 scripts/verify_workbook.py /path/to/workbook.xlsx
```

**Do NOT claim task success until the verify script exits with code 0.**

---

## Scripts

- `scripts/build_rollforward.py` — Working template for deferred revenue rollforward with correct formula patterns and dynamic row calculation. Adapt column layout and account names per task.
- `scripts/verify_workbook.py` — Validates workbook structure and detects circular references. **Always run before claiming completion.**

---

## Validation Checklist

1. **Run verify script FIRST**: `python3 scripts/verify_workbook.py <workbook_path>` — must exit with code 0
2. **No circular references**: Open workbook and verify no circular reference warnings
3. **Control row formulas**: SUM from data rows only, never rollforward pattern
4. **GL placement**: Hard-coded values in ending balance columns, never formulas
5. **Per-period reconciliation**: Each period has GL and Variance
6. **Summary alignment**: Links to final period ending balance column, not totals
7. **Active records only**: Archived/placeholder records excluded
8. **Non-monetary columns**: No formulas in metadata columns (Useful Life, Notes, Asset Account)
