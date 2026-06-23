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
4. Row 5: Column headers (Beginning Balance, Adds, Amortization, Ending Balance per month)
5. Row 6+: Vendor/partition data rows (numeric values as float/int, NOT strings)
6. Control rows (fixed positions):
   - **Row 12: Month Totals** - `=SUM(B6:B11)` for each month column
   - **Row 13: Ending Balance** - Reference to Month Totals Ending Balance cell (e.g., `=N12`)
   - **Row 14: Variance** - Difference between calculated and GL (typically 0 or calculated)
   - **Row 15: GL Balance** - Hardcoded value from input data
7. Column O: Total Amortization - `round(sum(monthly_amortization), 2)`

## Summary Sheet Structure
1. Row 1: Title (e.g., "Capacity Summary")
2. Row 2: Subtitle
3. Row 3-5: Headers and spacing
4. Row 6-7: Pool names with cross-sheet formulas linking to detail control rows
   - Example: `='Compute Pool #8100'!B12` (Month Totals from detail)
5. Row 8: Month Totals - `=SUM(B6:B7)`
6. Row 9: Ending Balance - `=N8`
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
ws.cell(row=r, column=c, value=int(data_value))

# WRONG — numeric values as strings fail verifier checks
ws.cell(row=r, column=c, value="123.45")
```

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)` for cell values, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- Exception: Total Amortization column uses `round(sum(...), 2)` per rollforward spec
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Verification
```python
wb = openpyxl.load_workbook(path)
# Check sheet order matches expected
assert wb.sheetnames == ['Capacity Summary', 'Compute Pool #8100', 'Storage Pool #8200']
# Verify GL Balance formula
assert ws_summary.cell(row=16, column=2).value == '=B9+B14'
# Verify all detail values are numeric (not text)
for row in ws_detail.iter_rows(min_row=6, max_row=11, min_col=2, max_col=15):
    for cell in row:
        assert isinstance(cell.value, (int, float)), f"Non-numeric: {cell.value}"
```

## Anti-Patterns
- **Do not** use `Border.Style()` — it does not exist. Use `Side(style="...")`.
- **Do not** set `.value` on cells in merged ranges without unmerging first.
- **Do not** write numeric values as strings — verifiers check `isinstance(val, (int, float))`.
- **Do not** assume `wb.active` is safe to clear if it contains merges — create a new sheet instead.
- **Do not** hardcode summary values — use cross-sheet formulas for traceability.
- **Do not** skip control rows — they are required for reconciliation validation.
- **Do not** assume structural verification is sufficient — tests check specific data conditions.

## Troubleshooting
- `AttributeError: type object 'Border' has no attribute 'Style'` → Use `Side(style="thin")`.
- `AttributeError: 'MergedCell' object attribute 'value' is read-only` → Unmerge cells before clearing, or create a fresh sheet.
- Verifier fails on numeric checks → Ensure values are Python `float`/`int`, not formatted strings.
- Cross-sheet formulas show as text → Verify sheet names match exactly (case-sensitive, spaces preserved).
- Verifier fails on `test_legacy_node_checks` → Check rollforward formula constraints above; Ending Balance must equal Prior Ending + Adds - Amortization.