---
name: financial-rollforward-workbook
description: Build multi-period financial roll-forward workbooks in Excel using openpyxl. Use for deferred revenue schedules, prepaid expense amortization, fixed asset rolls, accrual rollforwards, warranty reserves, commission asset schedules, or any account requiring Beginning + Additions - Releases = Ending tracking across periods with GL reconciliation and cross-sheet summary links.
---

# Financial Rollforward Workbook Builder

## STOP: READ THIS FIRST — THE #1 VERIFIER FAILURE

**Every round, workers fail because they apply rollforward formulas (=B+C-D) to control rows. This creates circular references.**

### The Two Types of Rows

| Row Type | What It Contains | Formula for Ending Balance |
|----------|------------------|---------------------------|
| **Data rows** | Individual line items (customers, claim groups, payees) | Rollforward formula: `=B{r}+C{r}-D{r}` |
| **Control rows** | Aggregates (Period Totals, Ending Balance, Variance, GL Balance) | SUM of data rows: `=SUM(E6:E8)` |

### The Category Error

Applying `=B10+C10-D10` to row 10 (which IS the Ending Balance control row) is wrong because:
- Row 10 is the row you're computing
- B10, C10, D10 are empty or contain other formulas
- The formula references itself → circular reference

### RIGHT WAY — Check the Row Type

```python
# STEP 1: Identify row type
if row_label in ["Period Totals", "Ending Balance", "Calculated Ending Balance", "Variance", "GL Balance"]:
    # This is a CONTROL ROW — use SUM of data rows only
    ws.cell(row=r, column=end_col, value=f"=SUM({col_letter}{data_start}:{col_letter}{data_end})")
else:
    # This is a DATA ROW — rollforward formula is correct
    ws.cell(row=r, column=end_col, value=f"=B{r}+C{r}-D{r}")
```

### MANDATORY CHECKPOINT

Before writing any formula, ask:
1. Is this row a control row (Period Totals, Ending Balance, Variance, GL Balance)?
2. If YES → Does this formula reference any cell on this same row?
3. If YES → STOP. Use SUM of data rows instead.

### CRITICAL: Never Put Formulas in Non-Monetary Columns

Columns like "Useful Life Months", "Notes", or "Asset Account" contain metadata, not amounts. **Never place formulas in these columns.**

```python
# WRONG: Formula in non-monetary column (e.g., column O = Useful Life Months)
ws.cell(row=totals_row, column=15, value=f"=SUM(O{start}:O{end})")

# RIGHT: Skip non-monetary columns when writing Period Totals
# Only write SUM formulas for monetary columns (B through N)
for col in range(2, 15):  # columns B-N only
    col_letter = get_column_letter(col)
    ws.cell(row=totals_row, column=col, value=f"=SUM({col_letter}{start_row}:{col_letter}{end_row})")
```

**Non-monetary columns to skip: Useful Life Months, Notes, Asset Account, Contract Months**

---

## VARIANT DETECTION — Choose the Right Skill

**Before starting any rollforward task, identify which variant you have:**

| Check | If YES → Use | If NO → Use |
|-------|--------------|-------------|
| Source data has `action` column with `override`/`insert` values? | `rebate-rollforward` | Continue checking |
| Source data filtered by `status` field (e.g., status=open)? | `rebate-rollforward` | Continue checking |
| Source data is **nested JSON** with `accounts[]→groups[]→items[]` structure? | `project-cost-rollforward` | Continue checking |
| Items have `revision` field requiring deduplication? | `project-cost-rollforward` | Continue checking |
| CSV overrides patch specific `row_id` fields (no action column)? | `project-cost-rollforward` | Continue checking |
| Columns are **Cap Adds** and **Amortization** (not Billings/Recognition)? | `project-cost-rollforward` | `financial-rollforward-workbook` (this skill) |

### How to Detect

1. **Check for action column**: If patch CSV has `action` column with `override`/`insert` → rebate-rollforward.
2. **Check for status filtering**: If filtering by `status` field (e.g., status=open) → rebate-rollforward.
3. **Check column headers**: If you see "Cap Adds" and "Amortization" → project-cost variant. If you see "Billings/Recognition", "Accruals/Releases", "Incurred/Claims Paid", "Capitalized/Amortization" → standard rollforward.
4. **Check data structure**: Nested JSON with revision tracking → project-cost. Flat CSV → standard or rebate.
5. **Check summary requirements**: Link to column O → project-cost or rebate. Link to column N → standard.

### Critical Rule

**DO NOT apply this skill's patterns to a project-cost or rebate task!**

- **Project-cost** uses: Running balance formulas, revision deduplication, CSV overrides by row_id, summary→O
- **Rebate** uses: Running balance formulas, status filtering, action-based patches (override/insert), summary→O

If any of these apply, switch to the appropriate skill immediately.

---

## When to Use

- Deferred revenue rollforward schedules with GL reconciliation
- Prepaid expense amortization tracking
- Fixed asset depreciation rolls
- Accrual rollforward schedules (payroll, bonus, etc.)
- Warranty reserve schedules with claims tracking
- Commission asset capitalization and amortization schedules
- Any month-end close workpaper requiring period-to-period balance rollforwards
- Multi-customer, multi-period revenue recognition tracking

---

## Rollforward Structure

A financial rollforward follows this pattern for each period:
```
Beginning Balance + Additions (Billings/Accruals/Capitalized) - Releases (Recognition/Payments/Amortized) = Ending Balance
```

The Ending Balance of one period becomes the Beginning Balance of the next (implicit in data rows).

---

## Workflow

1. **Load Source Data**: Read CSVs into lists of dicts via `csv.DictReader`, JSON via `json.load`. Normalize numeric fields to float: `float(v) if v else 0.0`. Filter to `record_status == 'active'` or `eligible == true` if status/eligibility column exists.

2. **Sort Data**: Sort alphabetically by key field (customer name, claim group, payee name, etc.) before writing rows.

3. **Initialize Workbook**: Create `Workbook()`, delete default "Sheet" if present, create detail sheets and summary sheet in required order.

4. **Populate Detail Sheets**:
   - Write headers at row 5.
   - Write data rows starting at row 6. Apply `#,##0.00` number format to monetary columns.
   - Sort data rows alphabetically by key field if not pre-sorted.
   - Compute control row positions dynamically: `totals_row = first_data_row + len(data_rows)`, then increment for each control row.
   - **Run checkpoint before writing any control row formula** (see STOP section above).
   - Write control rows with labels and formulas.

5. **Build Summary Sheet**:
   - Map summary cells to control rows on detail sheets using cross-sheet references: `='Sheet Name'!CellRef`.
   - **CRITICAL**: Link Ending Balance and GL Balance to the **final period's ending balance column** (e.g., column N for Oct), NOT to totals columns (e.g., O).
   - Quote sheet names containing spaces or special characters (#).

6. **Save & Verify**: Save to `.xlsx`. Run `scripts/verify_workbook.py` to validate structure. **Do not claim completion until verify script passes.**

---

## Decision Rule: Which Formula Pattern?

| Row Type | Column Type | Formula Pattern |
|----------|-------------|-----------------|
| Data row (line item) | Ending balance columns (E, H, K, N) | `=B{r}+C{r}-D{r}` (rollforward) |
| Period Totals | All monetary columns B-N | `=SUM(B{start}:B{end})` |
| Ending Balance (control) | Ending balance columns (E, H, K, N) | `=SUM(E{start}:E{end})` (NOT rollforward!) |
| GL Balance | Ending balance columns only | Hard-coded value from JSON |
| Variance | Final period column | `=N{gl_row}-N{calc_row}` |
| Any control row | Non-monetary columns (O, P, Q) | SKIP — no formulas in metadata |

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
for col in range(2, 15):  # columns B-N only; skip non-monetary
    col_letter = get_column_letter(col)
    ws.cell(row=totals_row, column=col, value=f"=SUM({col_letter}{start_row}:{col_letter}{end_row})")
```

### Calculated Ending Balance — SUM Data Row Ending Balances
```python
# For each ending balance column, sum the data rows
ws.cell(row=calc_ending_row, column=5, value=f"=SUM(E{start_row}:E{end_row})")  # Jul Ending
ws.cell(row=calc_ending_row, column=8, value=f"=SUM(H{start_row}:H{end_row})")  # Aug Ending
ws.cell(row=calc_ending_row, column=11, value=f"=SUM(K{start_row}:K{end_row})")  # Sep Ending
ws.cell(row=calc_ending_row, column=14, value=f"=SUM(N{start_row}:N{end_row})")  # Oct Ending (final)
```

### GL Balance Row — Hard-Coded Values
```python
# Place GL in each period's ending balance column
ws.cell(row=gl_row, column=5, value=gl_data['jul'])
ws.cell(row=gl_row, column=8, value=gl_data['aug'])
ws.cell(row=gl_row, column=11, value=gl_data['sep'])
ws.cell(row=gl_row, column=14, value=gl_data['oct'])
```

### Variance — Per-Period Calculation
```python
ws.cell(row=variance_row, column=5, value=f"=E{gl_row}-E{calc_ending_row}")  # Jul
ws.cell(row=variance_row, column=8, value=f"=H{gl_row}-H{calc_ending_row}")  # Aug
ws.cell(row=variance_row, column=14, value=f"=N{gl_row}-N{calc_ending_row}")  # Oct (final)
```

### Cross-Sheet References — Final Period Only
```python
# WRONG: Links to column O (totals/metrics)
summary.cell(row=r, column=2, value="='Field Comm Asset #1510'!O10")

# RIGHT: Links to final period ending balance column (N)
summary.cell(row=r, column=2, value="='Field Comm Asset #1510'!N10")
```

Always quote sheet names with spaces or special characters (#).

---

## Anti-Patterns

| Issue | Cause | Fix |
|-------|-------|-----|
| Circular reference | Rollforward formula on control row references its own row | SUM the ending balance column from data rows instead |
| Wrong row type | Treating control rows like data rows | Control rows aggregate; data rows track individual items |
| Hardcoded control row indices | Different sheets have different data counts | Compute: `totals_row = start_row + len(data_rows)` |
| Wrong GL placement | GL in wrong column or as formula | Place GL in dedicated row, hard-code value from JSON |
| Summary links to wrong column | Linking to totals column (O) instead of ending balance column (N) | Link summary to final period's ending balance column |
| Missing cross-sheet links | Summary uses hard-coded values | Use `='SheetName'!CellRef` syntax |
| Including archived records | Not filtering source data | Filter to `status == 'active'` or `eligible == true` |
| Variance miscalc | Subtracting wrong direction | Variance = GL Balance - Calculated Ending |
| Missing `=` prefix | Formula stored as text | All formula strings must start with `=` |
| Formula in non-monetary column | Placing SUM in metadata columns (Useful Life, Notes) | Skip non-monetary columns when writing control rows |

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
- Same circular reference rules apply
- Ending balance columns must SUM from data rows on control rows, NOT use rollforward formulas
- Typical columns: Beginning Balance, [Period] Accruals, [Period] Releases, [Period] Ending Balance per period
- GL Balance values come from JSON keyed by period (e.g., `gl_balances['payroll_accrual_2105']['nov']`)
- Place GL in each period's ending balance column (E for Jul, H for Aug, K for Sep)
- Calculate variance per-period, not just final total

### warranty-reserve-rollforward
- Filter source data to `record_status == 'active'` only; exclude archived records
- Sort claim groups alphabetically by name within each sheet
- Columns typically: Claim Group, Beginning Balance, [Period] Incurred, [Period] Claims Paid, [Period] Ending Balance per period
- GL Balances provided per period in JSON; hardcode each period's GL in the corresponding ending balance column
- **Summary sheet must link to final period's ending balance column** (e.g., N for Oct), NOT totals column (O)
- Do not link summary to intermediate calculations or totals columns

### commission-asset-rollforward
- Filter to `eligible == true` rows only; exclude ineligible placeholder records
- Join activity data with metadata by `line_key`; sort by payee name, then line_key
- Column layout: Payee, Beginning Balance, then for each period (Jul/Aug/Sep/Oct): [Period] Capitalized, [Period] Amortization, [Period] Ending Balance, followed by Useful Life Months, Notes, Asset Account
- **CRITICAL: Columns O, P, Q (Useful Life Months, Notes, Asset Account) are metadata — NEVER put formulas in these columns**
- Control row positions: Period Totals (row 9), Ending Balance (row 10), Variance (row 11), GL Balance (row 12) — positions are example, compute dynamically
- Period Totals: SUM monetary columns B-N only; skip columns O, P, Q
- Calculated Ending Balance: SUM ending balance columns (E, H, K, N) from data rows
- GL Balance: Hard-coded values from JSON, placed in each period's ending balance column
- **Summary must link to column N (Oct Ending Balance), NOT column O**
- Variance formula: `=N{gl_row}-N{calc_row}` (GL minus Calculated Ending in final period column)

### prepaid-expense-amortization
- (Reserved for future sub-tasks)

### fixed-asset-roll
- (Reserved for future sub-tasks)

---

## Scripts

- `scripts/build_rollforward.py` — Working template for deferred revenue rollforward with correct formula patterns and dynamic row calculation. Adapt column layout and account names per task.
- `scripts/verify_workbook.py` — Validates workbook structure: sheet order, headers, control row labels, formula syntax, and **detects circular references**.

---

## Validation Steps

1. **Run verify script FIRST**: `python3 scripts/verify_workbook.py <workbook_path>` — exits with error if circular references found. **Do not proceed to completion until this passes.**
2. **Check formula dependencies**: Each formula should only reference data rows (rows 6 to end_row), never control rows
3. **Cross-foot totals**: Sum of line item ending balances should equal calculated ending balance
4. **GL reconciliation**: Variance should be zero for each period
5. **Summary column check**: Verify summary formulas point to final period ending balance column (N), not totals column (O)
6. **Non-monetary column check**: Verify NO formulas exist in metadata columns (Useful Life, Notes, Asset Account)
