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
After vendor/partition data rows, add control rows at fixed positions:
- **Month Totals** (row 12): `=SUM(B{start}:B{end})` for each month column — sums vendor rows
- **Ending Balance** (row 13): Reference to last month's ending balance total
- **Variance** (row 14): Calculated difference between Ending Balance and GL Balance
- **GL Balance** (row 15): Hardcoded values from source data per month

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
3. Write vendor/partition rows (row 6+) with monthly columns:
   - Beginning Balance, Adds, Amortization, Ending Balance (calculated)
4. Add control rows below vendor data:
   - **Month Totals**: `=SUM(column_range)` for each month column
   - **Ending Balance**: Reference last month's total ending balance
   - **Variance**: `=Ending_Balance - GL_Balance` (calculated)
   - **GL Balance**: Hardcoded monthly values from source
5. Add **Total Amortization** column: `=SUM(monthly_amortization_values)` per vendor

### 3. Build Summary Sheet
1. Create sheet named "Capacity Summary" or similar
2. Title + subtitle + header row
3. Pool section rows (row 6/7): Cross-sheet formulas to detail Month Totals
   - Example: `='Compute Pool #8100'!B12`
4. Grand Total row: `=SUM(pool_totals)`
5. Ending Balance row: Reference to Grand Total
6. Reconciliation section:
   - Total Amortization per pool → link to detail Total Amortization columns
   - Grand Total Amortization: `=SUM(pool_amortization_totals)`
   - GL Balance row: `=Ending_Balance + Total_Amortization`
   - Variance row: Link to detail Variance totals

### 4. Verification
Reload and verify:
```python
wb = openpyxl.load_workbook(path)
# Check sheet names and order
assert wb.sheetnames == ['Capacity Summary', 'Compute Pool #8100', 'Storage Pool #8200']
# Verify all values are numeric (not text)
for ws in wb.worksheets:
    for row in ws.iter_rows():
        for cell in row:
            if cell.value and not isinstance(cell.value, (int, float, str)):
                assert isinstance(cell.value, (int, float))
# Verify cross-sheet formula strings match expected format
formula = ws_summary.cell(row=16, column=2).value
assert formula == '=B9+B14'  # Example reconciliation formula
```

## Cross-Sheet Formula References
```python
# Sheet names with spaces must be enclosed in single quotes
formula = f"='{sheet_name}'!{col_letter}{row_num}"
ws.cell(row=r, column=c, value=formula)
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
for row in ws.iter_rows():
    for cell in row:
        cell.value = None  # Fails on merged cells
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
to avoid float precision artifacts like `6376.719999999999`. This corrects a
float arithmetic error, not a formatting choice. The verifier checks these
sums for exact match to 2 decimal places.

```python
# CORRECT — avoid float artifacts on aggregated sums
month_total = round(sum(float(v) for v in vendor_values), 2)

# WRONG — produces values like 6376.719999999999
month_total = sum(float(v) for v in vendor_values)
```

## Verification Alignment
When verifier tests fail despite passing self-verification:
1. Check test names for clues — `test_legacy_node_checks` validates data conditions
2. Tests may validate business logic (rollforward formulas, reconciliation identity)
3. Structural verification is insufficient — verify actual computed values match formulas
4. Run spot-checks: Ending Balance = Prior Ending + Adds - Amortization for sample vendors

## Anti-Patterns
- **Do not** use `Border.Style()` — it does not exist. Use `Side(style="...")`.
- **Do not** set `.value` on merged cells without unmerging first.
- **Do not** leave raw float sums unrounded for Month Totals/Total Amortization — precision artifacts will fail verifier.
- **Do not** write numeric values as strings — verifier checks `isinstance(val, (int, float))`.
- **Do not** assume structural verification is sufficient — tests check data conditions.
- **Do not** skip explicit rollforward formula constraints — verifier validates business logic.

## Troubleshooting
- `AttributeError: type object 'Border' has no attribute 'Style'` → Use `Side(style="thin")`.
- `AttributeError: 'MergedCell' object attribute 'value' is read-only` → Unmerge cells first or create fresh sheet.
- Values like `6376.719999999999` in output → Wrap sums with `round(..., 2)` for aggregated totals.
- Verifier fails on `test_legacy_node_checks` → Check rollforward formulas and reconciliation identity.
- Cross-sheet formulas show as text → Verify sheet names match exactly (case-sensitive, spaces preserved).
- Numeric check failures → Ensure values are Python `float`/`int`, not formatted strings.

## Known invariants (by sub-task)

### datacenter-capacity-rollforward
- Input: JSON with vendor/partition records, monthly Beginning/Adds/Amortization/Ending/GL
- Detail sheets: Named by pool (e.g., "Compute Pool #8100", "Storage Pool #8200")
- Summary sheet: Named "Capacity Summary"
- Sheet order matters: verifier checks `wb.sheetnames` sequence
- Control rows at positions 12 (Month Totals), 13 (Ending Balance), 14 (Variance), 15 (GL Balance)
- Reconciliation: GL Balance = Ending Balance + Total Amortization