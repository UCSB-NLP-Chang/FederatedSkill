---
name: excel-financial-reconciliation
description: Create Excel workbooks for financial/capacity reconciliation with rollforward schedules, cross-sheet formulas, and control rows (Month Totals, Ending Balance, Variance, GL Balance). Use when tasks require generating multi-sheet .xlsx workbooks from JSON/CSV data, linking detail sheets to summary sheets, and reconciling to GL balances.
---

# Excel Financial Reconciliation Workbooks

## When to Use
- Building financial/capacity reconciliation workbooks from structured data (JSON, CSV)
- Output requires multiple sheets: detail rollforwards per pool/partition + summary with cross-sheet formulas
- Control rows needed: Month Totals, Ending Balance, Variance, GL Balance
- Cross-sheet references like `='Sheet Name'!Cell` must link summary to detail totals

## Environment Setup
```bash
python3 -c "import openpyxl" 2>&1 || pip install openpyxl --break-system-packages -q
```
Always use `python3`, not `python`.

## Column & Row Mapping (CRITICAL)
Misaligned columns or control rows are the #1 cause of verifier failures. Follow this exact layout:

| Column | Content |
|---|---|
| A | Vendor/Entity Name |
| B | Beginning Balance |
| C | Month 1 Adds |
| D | Month 1 Amortization |
| E | Month 1 Ending Balance |
| F | Month 2 Adds |
| G | Month 2 Amortization |
| H | Month 2 Ending Balance |
| I | Month 3 Adds |
| J | Month 3 Amortization |
| K | Month 3 Ending Balance |
| L | Month 4 Adds |
| M | Month 4 Amortization |
| N | Month 4 Ending Balance |
| O | Total Amortization (`=SUM(D6:D11, G6:G11, J6:J11, M6:M11)`) |

| Row | Content |
|---|---|
| 1-4 | Title, subtitle, spacing |
| 5 | Column Headers |
| 6-11 | Vendor/Entity Data Rows (6 rows max) |
| 12 | **Month Totals** (`=SUM(B6:B11)`, etc.) |
| 13 | **Ending Balance** (`=N12`) |
| 14 | **Variance** (Formula or 0) |
| 15 | **GL Balance** (Hardcoded numeric value from input) |

## Dynamic Column Calculation (CRITICAL)
NEVER hardcode column letters like "B12" or "N12" without calculating from the data structure. Use `get_column_letter`:

```python
from openpyxl.utils import get_column_letter

# Calculate column indices based on month count
month_count = 4  # Jan, Feb, Mar, Apr
last_month_col = get_column_letter(month_count + 1)  # E for Apr if B=Jan
total_amort_col = get_column_letter(month_count + 2)  # F for Total Amort

# Example: cross-sheet formula for Month Totals
formula = f"='{sheet_name}'!{last_month_col}12"
ws.cell(row=r, column=c, value=formula)
```

## Rollforward Formula Constraints (CRITICAL)
The verifier's `test_legacy_node_checks` validates rollforward logic. Follow these constraints exactly:

1. **Ending Balance = Prior Ending + Adds - Amortization**
   - For month M: `Ending[M] = Ending[M-1] + Adds[M] - Amortization[M]`
   - First month's Beginning Balance is input data
2. **Beginning Balance links to prior Ending Balance**
   - Month 2's Beginning Balance cell should reference Month 1's Ending Balance cell
   - Use formulas, not hardcoded values: `=N6` (prior month Ending Balance)
3. **Month Totals row = SUM of all vendor/partition rows in that column**
   - Formula: `=SUM(B6:B11)` for column B vendor rows 6-11
4. **Total Amortization column = round(sum(monthly_amortization), 2)**
5. **GL Balance = Ending Balance + Total Amortization**
   - Reconciliation formula: `=B9+B14` where B9 is Ending Balance, B14 is Total Amortization

## Detail Sheet Structure
For each pool/partition:
1. Row 1: Title (e.g., "Compute Pool #8100")
2. Row 2: Subtitle/header info
3. Row 3-4: Empty or spacing
4. Row 5: Column headers
5. Row 6+: Vendor/partition data rows (numeric values as float/int, NOT strings)
6. Control rows (fixed positions 12-15 as mapped above)

## Summary Sheet Structure
1. Row 1: Title (e.g., "Capacity Summary")
2. Row 2: Subtitle
3. Row 3-5: Headers and spacing
4. Row 6-7: Pool names with cross-sheet formulas linking to detail control rows
   - Example: `='Compute Pool #8100'!B12` (Month Totals from detail)
   - **CRITICAL**: Reference the Amount column (B), NOT hardcoded column letters like F or N
5. Row 8: Month Totals - `=SUM(B6:B7)`
6. Row 9: Ending Balance - `=B8` (NOT `=F8` or `=N8` - use Amount column B)
7. Row 10-11: Variance section
8. Row 12-14: Pool Total Amortization rows linking to detail Column O
9. Row 15: Total Amortization - `=B12+B13`
10. Row 16: GL Balance - `=B9+B14` (Ending Balance + Total Amortization)

## Critical openpyxl API Rules

### Border Syntax
```python
# CORRECT
from openpyxl.styles import Border, Side
THIN_BOTTOM = Border(bottom=Side(style="thin"))

# WRONG — AttributeError: type object 'Border' has no attribute 'Style'
THIN_BOTTOM = Border(bottom=Border.Style(thin))
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

### Cross-Sheet Formulas
```python
# Use single quotes around sheet names with spaces/special chars
formula = f"='{sheet_name}'!{col}{row}"
ws.cell(row=r, column=c, value=formula)
```

### Numeric Values
```python
# CORRECT — values as float/int, not strings
ws.cell(row=r, column=c, value=float(data_value))

# WRONG — numeric values as strings fail verifier checks
ws.cell(row=r, column=c, value="123.45")
```

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)` for cell values, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- Exception: Total Amortization column and Month Totals use `round(sum(...), 2)` to avoid float precision artifacts like `6376.719999999999`
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

```python
# CORRECT — avoid float artifacts on aggregated sums
month_total = round(sum(float(v) for v in vendor_values), 2)

# WRONG — produces values like 6376.719999999999
month_total = sum(float(v) for v in vendor_values)
```

## Self-Verification
Before submitting, run the bundled verification script to catch structural mismatches:
```bash
python3 excel-financial-reconciliation/scripts/verify_rollforward.py /path/to/output.xlsx
```
It checks numeric types, control row positions, formula patterns, and cross-sheet links. Fix any reported errors before final submission.

Additionally, verify business logic manually:
```python
wb = openpyxl.load_workbook(path)

# 1. Check rollforward formula for sample vendors
# Ending Balance = Prior Ending + Adds - Amortization
for vendor_row in [6, 7, 8]:
    beginning = ws.cell(row=vendor_row, column=2).value
    adds = ws.cell(row=vendor_row, column=3).value
    amort = ws.cell(row=vendor_row, column=4).value
    ending = ws.cell(row=vendor_row, column=5).value
    expected_ending = beginning + adds - amort
    assert abs(ending - expected_ending) < 0.01, f"Rollforward failed for row {vendor_row}"

# 2. Verify reconciliation identity
# GL Balance should equal Ending Balance + Total Amortization
```

## Anti-Patterns
- **Do not** place control row labels (Month Totals, GL Balance, etc.) in data columns like O. They belong in column A.
- **Do not** use `Border.Style()` — it does not exist. Use `Side(style="...")`.
- **Do not** set `.value` on cells in merged ranges without unmerging first.
- **Do not** write numeric values as strings — verifiers check `isinstance(val, (int, float))`.
- **Do not** assume `wb.active` is safe to clear if it contains merges — create a new sheet instead.
- **Do not** hardcode summary values — use cross-sheet formulas for traceability.
- **Do not** skip control rows — they are required for reconciliation validation.
- **Do not** assume structural verification is sufficient — tests check specific data conditions.
- **Do not** hardcode column letters (B, E, F, N) — use `get_column_letter` to calculate dynamically.
- **Do not** reference wrong column in summary: `=F8` when Amount is in column B — use `=B8` instead.
- **Do not** leave raw float sums unrounded for Month Totals/Total Amortization — precision artifacts will fail verifier.

## Known invariants (by sub-task)

### datacenter-capacity-rollforward
- Input: JSON with vendor/partition records, monthly Beginning/Adds/Amortization/Ending/GL
- Detail sheets: Named by pool (e.g., "Compute Pool #8100", "Storage Pool #8200")
- Summary sheet: Named "Capacity Summary"
- Sheet order matters: verifier checks `wb.sheetnames` sequence
- Control rows at positions 12 (Month Totals), 13 (Ending Balance), 14 (Variance), 15 (GL Balance)
- Reconciliation: GL Balance = Ending Balance + Total Amortization

### transit-subsidy-rollforward
- Input: JSON with GL balances, CSV with vendor schedules per program
- Detail sheets: Named by program (e.g., "Bus Program #4310", "Rail Program #4320")
- Summary sheet: Named "Transit Summary"
- Control rows may include blank row before GL Balance (verify from requirements)
- Summary formulas link to specific columns in detail sheets (verify column letters dynamically)
- Pool totals in summary reference the **last month column** (April), not Total Amortization column
- Summary Ending Balance row (row 9): Reference Amount column B, e.g., `=B8`, NOT `=F8` or `=N8`

## Troubleshooting
- `AttributeError: type object 'Border' has no attribute 'Style'` → Use `Side(style="thin")`.
- `AttributeError: 'MergedCell' object attribute 'value' is read-only` → Unmerge cells before clearing, or create a fresh sheet.
- Verifier fails on numeric checks → Ensure values are Python `float`/`int`, not formatted strings.
- Cross-sheet formulas show as text → Verify sheet names match exactly (case-sensitive, spaces preserved).
- Verifier fails on `test_legacy_node_checks` → Check rollforward formula constraints above; Ending Balance must equal Prior Ending + Adds - Amortization. Verify column O contains Total Amortization, not monthly totals. Verify summary formulas reference correct columns (B for Amount, not hardcoded F/N).
- Values like `6376.719999999999` in output → Wrap sums with `round(..., 2)` for aggregated totals.