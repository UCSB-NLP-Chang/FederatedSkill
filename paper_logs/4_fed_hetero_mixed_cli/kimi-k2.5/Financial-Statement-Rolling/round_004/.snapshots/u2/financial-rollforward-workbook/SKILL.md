---
name: financial-rollforward-workbook
description: Build multi-period financial roll-forward workbooks in Excel using openpyxl. Use for deferred revenue schedules, prepaid expense amortization, fixed asset rolls, accrual rollforwards, warranty reserves, commission asset tracking, or any account requiring Beginning + Additions - Releases = Ending tracking across periods with GL reconciliation and cross-sheet summary links.
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

### CRITICAL: Never Put Formulas in Non-Monetary Columns

Columns like "Useful Life Months", "Contract Months", "Notes", or "Asset Account" contain metadata, not amounts. **Never place formulas in these columns.** If you need a totals column, create a dedicated column or place the total in an appropriate monetary column.

```python
# WRONG: Formula in non-monetary column O (Useful Life Months)
ws.cell(row=totals_row, column=15, value=f"=C{totals_row}+F{totals_row}+I{totals_row}+L{totals_row}")

# RIGHT: Skip non-monetary columns entirely when writing Period Totals row
# Only place formulas in monetary columns (B through N for typical commission asset layout)
for col in range(2, 15):  # Columns B through N only
    if col in monetary_columns:  # Skip metadata columns
        ws.cell(row=totals_row, column=col, value=f"=SUM({col_letter}{start_row}:{col_letter}{end_row})")
```

---

## Data Rows vs Control Rows — Critical Distinction

### Data Rows (Line Items)
Data rows contain individual line items (customers, claim groups, assets, etc.).

**Ending balance columns on data rows should use rollforward formulas:**
```python
# Jun Ending = Beginning + Jun Accruals - Jun Claims Paid
ws.cell(row=r, column=5, value=f"=B{r}+C{r}-D{r}")
# Jul Ending = Jun Ending + Jul Accruals - Jul Claims Paid
ws.cell(row=r, column=8, value=f"=E{r}+F{r}-G{r}")
```

### Control Rows (Totals, Reconciliation)
Control rows aggregate data rows and reconcile to GL.

**Ending balance columns on control rows MUST SUM from data rows:**
```python
# Sum Jun Ending from all data rows
ws.cell(row=calc_ending_row, column=5, value=f"=SUM(E{start_row}:E{end_row})")
# Sum Jul Ending from all data rows
ws.cell(row=calc_ending_row, column=8, value=f"=SUM(H{start_row}:H{end_row})")
```

### Why This Matters
- Data rows track individual item rollforwards → rollforward formulas are correct
- Control rows aggregate and reconcile → SUM from data rows is correct
- Using rollforward formulas on control rows is a **category error** that produces wrong totals

---

## When to Use

- Deferred revenue rollforward schedules with GL reconciliation
- Prepaid expense amortization tracking
- Fixed asset depreciation rolls
- **Warranty reserve rollforwards** with claim groups and incurred/paid tracking
- **Commission asset rollforwards** with capitalized/amortized tracking
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

2. **Filter Active Records**: For warranty reserves, commission assets, or accruals with status fields, filter to `eligible: true` or `record_status == 'active'` before processing. Exclude archived/placeholder records.

3. **Initialize Workbook**: Create `Workbook()`, set sheet names in required order.

4. **Populate Detail Sheets**:
   - Write headers at row 5.
   - Write data rows starting at row 6. Apply `#,##0.00` number format to monetary columns.
   - Sort data rows alphabetically by key field (customer, claim group, payee, etc.) if not pre-sorted.
   - Compute control row positions dynamically: `totals_row = first_data_row + len(data_rows)`, then increment for each control row.
   - Write control rows with labels and formulas.

5. **Build Summary Sheet**:
   - Map summary cells to control rows on detail sheets using cross-sheet references: `='Sheet Name'!CellRef`.
   - **CRITICAL**: Link Ending Balance and GL Balance to the **final period's ending balance column** (e.g., if Oct is the last period in column N, link to N10 and N12, NOT column O).
   - Quote sheet names containing spaces or special characters.

6. **Save & Verify**: Save to `.xlsx`. Run `scripts/verify_workbook.py` to validate structure.

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
- **Must link to the final period's ending balance column for Ending Balance and GL Balance**
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
ws.cell(row=calc_ending_row, column=5, value=f"=SUM(E{start_row}:E{end_row})")  # Jun Ending
ws.cell(row=calc_ending_row, column=8, value=f"=SUM(H{start_row}:H{end_row})")  # Jul Ending
ws.cell(row=calc_ending_row, column=11, value=f"=SUM(K{start_row}:K{end_row})")  # Aug Ending
ws.cell(row=calc_ending_row, column=14, value=f"=SUM(N{start_row}:N{end_row})")  # Sep/Oct Ending (final)
```

### GL Balance Row
- Must be a SEPARATE row with hard-coded GL value from JSON
- Place in the ending balance column for each period (e.g., columns E, H, K, N for period endings)
- **Do NOT place formulas in GL Balance row** - only hardcoded values in period columns
- For the summary sheet link, use the final period's column (e.g., N for Oct)
- Variance = GL Balance - Calculated Ending Balance (place in final period column)

### Cross-Sheet References — Final Period Only
```python
# WRONG: Links to column O (totals/metrics column, not ending balance)
summary.cell(row=r, column=2, value="='Field Comm Asset #1510'!O10")

# RIGHT: Links to final period ending balance column (N = Oct Ending)
summary.cell(row=r, column=2, value="='Field Comm Asset #1510'!N10")
```

Always quote sheet names with spaces or special characters (#).

---

## Anti-Patterns

| Issue | Cause | Fix |
|-------|-------|-----|
| Circular reference | Rollforward formula on control row references its own row | SUM the ending balance column from data rows instead |
| Hardcoded control row indices | Different sheets have different data counts | Compute: `totals_row = start_row + len(data_rows)` |
| Wrong GL placement | GL in wrong column/row or as formula | Place GL in final period ending balance column, hard-code value from JSON |
| Summary links to totals column | Confusing calculated totals column with Ending Balance | Link summary Ending Balance to final period's ending balance column (e.g., N), not totals column (e.g., O) |
| Missing cross-sheet links | Summary uses hard-coded values | Use `='SheetName'!CellRef` syntax |
| Variance miscalc | Subtracting wrong direction or wrong column | Variance = GL Balance - Calculated Ending (both in final period column) |
| Numeric values as strings | CSV values not converted | Convert to float before writing: `float(v) if v else 0.0` |
| Missing `=` prefix | Formula stored as text | All formula strings must start with `=` |
| Including archived records | Not filtering source data | Filter to `status == 'active'` or `eligible == true` before building rows |
| GL Balance row has extra formulas | Adding calculated columns to GL row | GL row should only contain hardcoded period values, no formulas |

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

### warranty-reserve-rollforward
- Filter source data to `record_status == 'active'` only; exclude archived records
- Sort claim groups alphabetically by name within each sheet
- Columns typically: Claim Group, Beginning Balance, [Period] Incurred/Accruals, [Period] Claims Paid, [Period] Ending Balance per period
- GL Balances provided per period in JSON; hardcode each period's GL in the corresponding ending balance column
- **Summary sheet must link to final period's ending balance column** (e.g., if periods are Jun/Jul/Aug/Sep in columns E/H/K/N, link to column N for Ending Balance and GL Balance)
- Do not link summary to intermediate calculations or totals columns

### commission-asset-rollforward
- Filter to `eligible: true` rows only; exclude ineligible placeholder records
- Join activity data with metadata by `line_key`; exclude metadata-only rows with no activity match
- Sort by payee name, then line_key
- Column layout: Payee, Beginning Balance, then for each period (Jul/Aug/Sep/Oct): [Period] Capitalized, [Period] Amortization, [Period] Ending Balance, followed by Useful Life Months, Notes, Asset Account
- Control row positions: Period Totals (row 9), Ending Balance (row 10), Variance (row 11), GL Balance (row 12)
- **CRITICAL**: Final period (Oct) Ending Balance is in column N (14), not column O (15)
- **Summary must link to column N for Ending Balance and GL Balance**, not column O
- GL Balance values come from JSON keyed by period; hardcode in period ending balance columns (E, H, K, N for Jul/Aug/Sep/Oct)
- Variance formula: `=N12-N10` (GL minus Calculated Ending in final period column)
- Do not add formulas to GL Balance row beyond the hardcoded period values

### prepaid-expense-amortization
- (Reserved for future sub-tasks)

### fixed-asset-roll
- (Reserved for future sub-tasks)

---

## Troubleshooting

### "test_legacy_pytest_suite" failure
This usually indicates one of these structural errors:
1. **Wrong Summary Links**: Summary sheet links to column O (totals) instead of column N (final period ending balance). Check the column headers to identify which column contains the final period's ending balance and link to that column specifically.
2. **GL Balance as Formula**: GL Balance row contains a formula instead of hardcoded values. GL represents the actual general ledger balance and must be hardcoded from source JSON.
3. **Circular Reference**: Control row formula references its own row. Use SUM of data rows instead.

### Verifier mismatch on Ending Balance values
- Verify that Calculated Ending Balance row uses SUM of data rows, not a rollforward formula
- Check that data rows themselves have correct rollforward formulas (Beginning + Adds - Releases = Ending)
- Ensure no rounding is applied to numeric values before writing to cells

### Missing records in output
- Check filtering logic: ensure `eligible: true` or `status == 'active'` filter is applied correctly
- Verify join logic: ensure metadata rows without matching activity are excluded, not included with zero values

---

## Validation Checklist

1. **No circular references**: Open workbook and verify no circular reference warnings
2. **Control row formulas**:
   - Period Totals uses SUM of data rows
   - Calculated Ending uses SUM of ending balance column (data rows only)
   - GL Balance has hard-coded values (no formulas) in ending balance columns
   - Variance references GL minus Calculated Ending
3. **Per-period reconciliation**: Each period column has its own GL and Variance (if required by task)
4. **Cross-foot**: Sum of line item ending balances equals calculated ending balance
5. **Summary alignment**: Summary sheet links point to final period ending balance column, not totals columns
6. **Active records only**: Verify archived/placeholder/ineligible records excluded from data rows
7. **GL row purity**: GL Balance row contains only hardcoded values, no formulas

---

## Scripts

- `scripts/build_rollforward.py` — Working template for deferred revenue rollforward with correct formula patterns and dynamic row calculation. Adapt column layout and account names per task.
- `scripts/verify_workbook.py` — Validates workbook structure: sheet order, headers, control row labels, and formula syntax. Detects circular references.

Read `scripts/build_rollforward.py` when creating a new rollforward to see the correct pattern for:
- Dynamic control row positioning
- SUM formulas referencing data rows only
- Hard-coded GL placement
- Cross-sheet reference syntax
