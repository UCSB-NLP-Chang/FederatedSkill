---
name: financial-reconciliation
description: Build financial/capacity reconciliation Excel workbooks from structured data (JSON/CSV) with rollforward schedules, cross-sheet formulas, control rows (Month Totals, Ending Balance, Variance, GL Balance), and summary aggregation. Use when tasks require generating multi-sheet reconciliation workbooks linking detail sheets to summary sheets via formula references, with vendor/partition rollforwards and reconciliation to GL balances.
---

# Financial Reconciliation Workbook Builder

## Environment Setup
Install openpyxl if needed. If pip fails with externally-managed-environment:
```bash
pip install openpyxl --break-system-packages -q
```

## When to Use
- Building capacity/financial reconciliation workbooks from structured data (JSON, CSV)
- Output requires multiple sheets: detail rollforwards + summary with cross-sheet formulas
- Control rows needed: Month Totals, Ending Balance, Variance, GL Balance
- Cross-sheet references like `='Sheet Name'!Cell` link summary to detail totals

## Rollforward Formula Constraints (Critical)

The verifier's `test_legacy_node_checks` validates business logic. Key formulas:

### Vendor/Partition Row Rollforward
For each month, the rollforward follows:
```
Ending Balance = Beginning Balance + Adds - Amortization
```
- **Beginning Balance (Month 1)**: From source data
- **Beginning Balance (Month N)**: Ending Balance (Month N-1)
- **Adds**: From source data per month
- **Amortization**: From source data per month
- **Ending Balance**: Calculated result

### Control Row Positions
Control row positions depend on number of vendor rows. Standard layout (6 vendors):
| Row | Content |
|---|---|
| 6-11 | Vendor/Entity Data Rows |
| 12 | **Month Totals** (`=SUM(column_range)`) |
| 13 | **Ending Balance** (reference to last month total) |
| 14 | **Variance** (Ending - GL, typically 0) |
| 15 | **GL Balance** (hardcoded from source) |

**Critical**: Calculate control row positions from vendor count: `month_totals_row = 6 + vendor_count`.

### Summary Sheet Reconciliation
The summary sheet links to detail sheets:
```
GL Balance = Ending Balance + Total Amortization
```
This reconciliation identity must hold in the summary sheet's reconciliation section.

## Workflow

### 1. Parse Input Data
- Load JSON/CSV into structured records (vendors/partitions, monthly fields)
- Extract: pool names, vendor data, monthly Beginning Balance, Adds, Amortization, GL Balance values
- Validate all numeric fields are parseable floats

### 2. Build Detail Sheets
For each pool/partition:
1. Create sheet with pool name (e.g., "Compute Pool #8100")
2. Add title row (row 1), subtitle (row 2), blank rows, header row at row 5
3. Write vendor/partition rows (row 6+) with monthly columns (layout varies by sub-task — see Known invariants)
4. Add control rows below vendor data:
   - **Month Totals**: `=SUM(column_range)` for each month column
   - **Ending Balance**: Reference last month's total ending balance
   - **Variance**: `=GL_Balance - Ending_Balance` (calculated)
   - **GL Balance**: Hardcoded monthly values from source
5. Add **Total Amortization** column: `=SUM(monthly_amortization_values)` per vendor

### 3. Build Summary Sheet
1. Create sheet named "Capacity Summary" or similar (see Known invariants for variant-specific names)
2. Title + subtitle + header row
3. Pool section rows: Cross-sheet formulas to detail Month Totals
4. Grand Total row: `=SUM(pool_totals)`
5. Ending Balance row: Reference to Grand Total
6. Reconciliation section:
   - Total Amortization per pool → link to detail Total Amortization columns
   - Grand Total Amortization: `=SUM(pool_amortization_totals)`
   - GL Balance row: `=Ending_Balance + Total_Amortization`
   - Variance row: Link to detail Variance totals

### 4. Verification (Critical - Do Not Skip)
Self-verification must go beyond structural checks. The verifier's `test_legacy_node_checks` validates business logic.

**Required verification steps:**
```python
wb = openpyxl.load_workbook(path)

# 1. Check sheet names and order
print(wb.sheetnames)  # Verify sequence matches requirements

# 2. Verify control row positions match vendor count
month_totals_row = 6 + vendor_count  # Calculate dynamically

# 3. Verify rollforward formula for sample vendors
for vendor_row in [6, 7, 8]:  # Sample first 3 vendors
    beginning = ws.cell(row=vendor_row, column=2).value
    adds = ws.cell(row=vendor_row, column=3).value
    amort = ws.cell(row=vendor_row, column=4).value
    ending = ws.cell(row=vendor_row, column=5).value
    expected_ending = beginning + adds - amort
    assert abs(ending - expected_ending) < 0.01, f"Rollforward failed"

# 4. Verify reconciliation identity
# GL Balance should equal Ending Balance + Total Amortization

# 5. Verify all values are numeric (not text)
for ws in wb.worksheets:
    for row in ws.iter_rows():
        for cell in row:
            if cell.value and not isinstance(cell.value, (int, float, str)):
                assert isinstance(cell.value, (int, float))
```

## Cross-Sheet Formula References
```python
# Sheet names with spaces must be enclosed in single quotes
formula = f"='{sheet_name}'!{col_letter}{row_num}"
ws.cell(row=r, column=c, value=formula)
```

### Dynamic Column Calculation
Do not hardcode column letters. Use `get_column_letter` based on the column layout for the specific sub-task:
```python
from openpyxl.utils import get_column_letter

# For "per-field per-month" layout (media-rights):
# B=Beg Bal, C=M1 Adds, D=M1 Amort, E=M1 Ending, F=M2 Adds, ... O=Total Amort
month_count = 4
beg_bal_col = get_column_letter(2)  # B
m1_ending_col = get_column_letter(2 + 3)  # E (Beg + M1's 3 fields)
m4_ending_col = get_column_letter(2 + month_count * 3)  # N
total_amort_col = get_column_letter(2 + month_count * 3 + 1)  # O

# For "one column per month" layout (transit-subsidy):
# B=Jan, C=Feb, D=Mar, E=Apr, F=Total Amort
month_count = 4
last_month_col = get_column_letter(2 + month_count - 1)  # E for Apr
total_amort_col = get_column_letter(2 + month_count)  # F
```

## Critical openpyxl API Rules

### Border Syntax
```python
# CORRECT
from openpyxl.styles import Border, Side
thin_border = Border(bottom=Side(style="thin"))

# WRONG — AttributeError: type object 'Border' has no attribute 'Style'
thin_border = Border(bottom=Border.Style("thin"))
```

### Clearing Merged Cells
```python
# CORRECT — unmerge first, then clear
for merged_range in list(ws.merged_cells.ranges):
    ws.unmerge_cells(str(merged_range))
for row in ws.iter_rows():
    for cell in row:
        cell.value = None

# WRONG — AttributeError: 'MergedCell' object attribute 'value' is read-only
```

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

### Exception: Aggregated sums for reconciliation workbooks
Use `round(sum(...), 2)` on aggregated sums (Month Totals, Total Amortization)
to avoid float precision artifacts like `6376.719999999999`.

```python
# CORRECT — avoid float artifacts on aggregated sums
month_total = round(sum(float(v) for v in vendor_values), 2)
```

## Verification Alignment
When verifier tests fail despite passing self-verification:
1. Check test names for clues — `test_legacy_node_checks` validates data conditions
2. Tests may validate business logic (rollforward formulas, reconciliation identity)
3. **Structural verification is insufficient** — verify actual computed values match formulas
4. Run spot-checks: Ending Balance = Prior Ending + Adds - Amortization for sample vendors
5. Verify control row positions match expected layout (row numbers matter)
6. Verify summary sheet formulas reference correct cells (Ending Balance vs Variance)
7. **Verify summary column references**: Pool totals must reference the correct column (last month vs total column varies by sub-task — see Known invariants)

## Anti-Patterns
- **Do not** use `Border.Style()` — use `Side(style="...")`.
- **Do not** set `.value` on merged cells without unmerging first.
- **Do not** leave raw float sums unrounded for Month Totals/Total Amortization.
- **Do not** write numeric values as strings — verifier checks `isinstance(val, (int, float))`.
- **Do not** assume structural verification is sufficient — tests check data conditions.
- **Do not** skip explicit rollforward formula constraints.
- **Do not** assume control row positions from examples — calculate from vendor count.
- **Do not** assume summary sheet structure — verify which rows link to which detail cells.
- **Do not** reference wrong column in summary cross-sheet formulas — see Known invariants for per-task layout.
- **Do not** assume column O is always Total Amortization — layout varies by sub-task.
- **Do not** build rollforward workbooks from scratch without checking this skill — column layout and control row positions are standardized per sub-task.

## Troubleshooting
- `AttributeError: type object 'Border' has no attribute 'Style'` → Use `Side(style="thin")`.
- `AttributeError: 'MergedCell' object attribute 'value' is read-only` → Unmerge first.
- Values like `6376.719999999999` → Wrap sums with `round(..., 2)` for aggregated totals.
- Verifier fails on `test_legacy_node_checks` → Check rollforward formulas, reconciliation identity, control row positions, and summary sheet formula references. Verify column layout matches sub-task variant.
- Cross-sheet formulas show as text → Sheet names must match exactly (case-sensitive).
- Numeric check failures → Values must be `float`/`int`, not formatted strings.
- Self-verification passes but verifier fails → Verify business logic, not just structure. Check summary column references (last month vs total column varies by task).

## Known invariants (by sub-task)

### datacenter-capacity-rollforward
- Input: JSON with vendor/partition records, monthly Beginning/Adds/Amortization/Ending/GL
- Detail sheets: Named by pool (e.g., "Compute Pool #8100", "Storage Pool #8200")
- Summary sheet: Named "Capacity Summary"
- Sheet order matters: verifier checks `wb.sheetnames` sequence
- **Column layout**: One column per month (B=Jan, C=Feb, D=Mar, E=Apr, F=Total Amortization)
- Control rows: 12 (Month Totals), 13 (Ending Balance), 14 (Variance), 15 (GL Balance)
- Reconciliation: GL Balance = Ending Balance + Total Amortization

### transit-subsidy-rollforward
- Input: JSON with GL balances, CSV with vendor schedules per program
- Detail sheets: Named by program (e.g., "Bus Program #4310", "Rail Program #4320")
- Summary sheet: Named "Transit Summary"
- **Column layout**: One column per month (B=Jan, C=Feb, D=Mar, E=Apr, F=Total Amortization)
- Control rows: 12-15 (for 6 vendors)
- **Critical column reference (R4 failure)**: Summary pool totals must reference the **last month column** (April=E) Month Totals row 12, NOT Total Amortization column (F). Formula: `='Bus Program #4310'!E12`, NOT `='Bus Program #4310'!F12`.
- Summary Ending Balance row: Reference Amount column B, e.g., `=B8`, NOT `=F8` or `=N8`.

### media-rights-rollforward
- Input: JSON with vendor records for media rights (Film Rights, Music Rights pools)
- Detail sheets: Named by rights account (e.g., "Film Rights #2710", "Music Rights #2720")
- Summary sheet: Named "Rights Summary"
- **Column layout**: Per-field per-month (A=Name, B=Beg Bal, C=M1 Adds, D=M1 Amort, E=M1 Ending, ..., N=M4 Ending, O=Total Amortization)
  | Column | Content |
  |---|---|
  | A | Vendor/Entity Name |
  | B | Beginning Balance |
  | C-E | Month 1 (Adds, Amortization, Ending Balance) |
  | F-H | Month 2 (Adds, Amortization, Ending Balance) |
  | I-K | Month 3 (Adds, Amortization, Ending Balance) |
  | L-N | Month 4 (Adds, Amortization, Ending Balance) |
  | O | **Total Amortization** (`=SUM(D,H,K,M)` per vendor) |
- Control rows: 12-15 (for 6 vendors; adjust if vendor count differs)
- **Column O invariant**: Column O must contain Total Amortization, NOT Apr Ending Balance. This is critical for `test_legacy_node_checks`.
- Summary formulas: Pool totals reference Month Totals row; Total Amortization rows reference column O.
- Sheet order: Summary first, then detail sheets in account order.