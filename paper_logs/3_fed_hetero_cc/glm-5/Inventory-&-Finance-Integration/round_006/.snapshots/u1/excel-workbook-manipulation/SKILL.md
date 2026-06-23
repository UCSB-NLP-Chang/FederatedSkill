---
name: excel-workbook-manipulation
description: Create, read, and modify Excel workbooks using Python. Use when tasks require reading source Excel files, performing calculations, generating new workbooks with multiple sheets, or transforming Excel data. Handles openpyxl/pandas installation, date handling, output verification, and financial reconciliation workbooks with cross-sheet formula references.
---

# Excel Workbook Manipulation

## CRITICAL ANTI-PATTERN: Never Overwrite Data Cells with Formulas

**The most common failure in multi-sheet reconciliation workbooks**: Writing summary formulas into columns that hold data values in line-item rows.

- **WRONG**: Writing `=SUM(...)` into column O of rows 6-11 when column O holds `amortization_months` for those rows
- **CORRECT**: Write summary values/formulas only into control rows (e.g., rows 12-16), then have the summary sheet reference those control row cells

**Rule**: Data rows and control rows must use disjoint column sets for their respective purposes. If a column holds data in rows 6-11, do not write formulas there—use a different column or different rows.

## CRITICAL: Control Rows Must Have Complete Rollforward Formulas

**Second most common failure**: Incomplete control row formulas in rollforward schedules.

For accounting rollforward schedules (beginning balance + adds - amortization = ending balance):

- **WRONG**: Control rows with formulas only in totals column (O), leaving month columns (B-N) empty
  ```
  Row 14 (Ending Balance): [empty, empty, ..., empty, =N11]  # WRONG!
  ```

- **CORRECT**: Control rows with formulas across ALL month columns
  ```
  Row 13 (Month Totals): [=SUM(B6:B11), =SUM(C6:C11), ..., =SUM(N6:N11), =SUM(N6:N11)]
  Row 14 (Ending Balance): [=B13, =C13+C7-C8, ..., =N13, =N13]  # Each month's ending
  Row 15 (Variance): [=B14-B13, ..., =N14-N13, =O14-O13]  # Or GL - Ending
  Row 16 (GL Balance): [empty, empty, ..., empty, static_value]  # Only in totals column
  ```

**Rule**: Every control row formula must exist in each month column where it makes sense, not just the totals column.

## CRITICAL: Dynamic Control Row Positions

**Common structural failure**: Assuming control rows are always at rows 13-16.

**Rule**: Control row positions are **dynamic**, determined by data row count:

```python
first_data_row = 6  # or wherever data starts
num_data_rows = len(items)  # count of line items
last_data_row = first_data_row + num_data_rows - 1

month_totals_row = last_data_row + 1
ending_balance_row = last_data_row + 2
variance_row = last_data_row + 3
gl_balance_row = last_data_row + 4
```

**Harbor format** happens to use 6 data rows (6-11), so control rows land at 12-15. **Other workbooks may have different data row counts.** Always compute positions from the data, never hardcode.

## CRITICAL ANTI-PATTERN: MergedCell Read-Only Error

**Symptom**: `AttributeError: 'MergedCell' object attribute 'value' is read-only`

**Cause**: In openpyxl, merging a range (e.g., `ws.merge_cells('A1:E1')`) converts cells A2:E1 into `MergedCell` objects that are **read-only**. Any subsequent `ws.cell(row, col, value=...)` call targeting those cells will fail.

**Decision Rule**: Choose ONE of these approaches:

| Approach | When to use | How |
|----------|-------------|-----|
| **No merges (recommended)** | Most tasks; avoids all merge-related bugs | Skip `merge_cells()` entirely. Use styling (borders, fills, alignment) to visually group cells. Write values normally. |
| **Write-then-merge** | When merges are explicitly required by the spec | 1. Write ALL values and formulas to the worksheet first. 2. Call `merge_cells()` as the **very last step** before saving. |
| **Top-left only** | When you must merge but also write | Write only to the top-left cell of the merge range. Secondary cells will display the same value automatically. |

**WRONG ordering** (causes read-only error):
```python
ws.merge_cells('A1:E1')
ws.cell(row=1, column=3, value='Title')  # FAILS: C1 is now a MergedCell
```

**CORRECT ordering** (write first, merge last):
```python
ws.cell(row=1, column=1, value='Title')
# ... write all other values ...
ws.merge_cells('A1:E1')  # Do this LAST, after all writes
```

**Safest approach** (no merges at all):
```python
# Skip merge_cells() entirely. Use styling for visual grouping.
from openpyxl.styles import Alignment
ws.cell(row=1, column=1, value='Title').alignment = Alignment(horizontal='center')
# Apply borders/fills to create visual sections without merge complexity
```

## CRITICAL: Formula Verification Strategy

**openpyxl CANNOT evaluate formulas**. Formulas are stored as strings and only calculate when opened in Excel.

### DO NOT Verify with data_only=True

```python
# WRONG - This returns None for all formula cells!
wb_calc = openpyxl.load_workbook(path, data_only=True)
val = wb_calc['Detail'].cell(row=13, column=15).value  # Always None!
```

### CORRECT: Verify Formula Strings Exist

```python
import openpyxl
from openpyxl.utils import get_column_letter

wb = openpyxl.load_workbook(path, data_only=False)  # Default, reads formulas

# 1. Check control rows have formulas in ALL columns
for row in [13, 14, 15]:  # Month Totals, Ending Balance, Variance
    for col in range(2, 16):  # B through O
        val = wb['Detail'].cell(row=row, column=col).value
        assert val is not None and '=' in str(val), f"Missing formula at {get_column_letter(col)}{row}"

# 2. Check GL Balance is only in O16 (static float, not formula)
assert wb['Detail'].cell(row=16, column=14).value is None, "GL Balance should NOT be in column N"
assert isinstance(wb['Detail'].cell(row=16, column=15).value, (int, float)), "GL Balance missing in O16"
```

**Rule**: Verify formula strings are correct. Do NOT verify calculated values—they don't exist until Excel opens the file.

## STOP/WARN: Mandatory Pre-Save Verification

**Before saving ANY rollforward workbook**, you MUST run verification:

```bash
/tmp/venv/bin/python3 scripts/verify_rollforward.py /path/to/output.xlsx
```

If verification fails:
1. **STOP** - Do not submit the workbook
2. Check which control rows are incomplete
3. Add missing formulas across ALL month columns (B-N)
4. Re-run verification
5. Only save after verification passes

## Quick Start

1. **Create a virtual environment first** - System Python on modern Debian/Ubuntu will reject `pip install`:
   ```bash
   python3 -m venv /tmp/venv
   /tmp/venv/bin/pip install openpyxl pandas -q
   ```

2. **Run all Python scripts through the venv**:
   ```bash
   /tmp/venv/bin/python3 << 'PYEOF'
   # your code here
   PYEOF
   ```

## Reading Excel Files

```python
import openpyxl
wb = openpyxl.load_workbook('/path/to/file.xlsx')
print(wb.sheetnames)

for sheet_name in wb.sheetnames:
    ws = wb[sheet_name]
    print(f"\n=== {sheet_name} ===")
    print(f"Dimensions: {ws.dimensions}")
    for row in ws.iter_rows(max_row=20, values_only=True):
        print(row)
```

## Date Handling

Excel cells may contain `datetime.datetime` or `datetime.date` objects, or ISO strings like `'2025-07-04'`. Handle all cases:

```python
from datetime import datetime, date, timedelta

def parse_excel_date(val):
    if isinstance(val, datetime):
        return val.date()
    elif isinstance(val, date):
        return val
    elif isinstance(val, str):
        return datetime.strptime(val, '%Y-%m-%d').date()
    return None

# Date arithmetic requires timedelta, not int
future_date = parsed_date + timedelta(days=10)  # Correct
future_date = parsed_date + 10  # TypeError!
```

## Writing Excel Files

```python
from openpyxl import Workbook
from openpyxl.utils import get_column_letter

wb = Workbook()
ws = wb.active
ws.title = "Sheet1"

# Write headers
headers = ['Col1', 'Col2', 'Col3']
ws.append(headers)

# Write data rows
for row_data in data:
    ws.append(row_data)

# Adjust column widths
for col_idx, header in enumerate(headers, 1):
    ws.column_dimensions[get_column_letter(col_idx)].width = max(15, len(header) + 2)

wb.save('/path/to/output.xlsx')
```

## Cross-Sheet Formula References

When creating summary sheets that link to detail sheets:

```python
# Reference another sheet's cell
ws['B7'] = "='Bus Program #4310'!O14"

# Reference with row iteration
for i, row in enumerate(range(12, 18), start=7):
    ws[f'B{i}'] = f"='Detail Sheet'!N{row}"
```

**Important**: Sheet names with spaces or special characters must be enclosed in single quotes in formulas: `'Sheet Name'!A1` not `Sheet Name!A1`.

## Financial Reconciliation Workbooks (Rollforward Format)

### Detail Sheet Layout (per pool/account)
```
Row 1:     Title (e.g., "Bus Program #4310")
Rows 2-4:  Empty
Row 5:     Headers [Vendor, Beginning Balance, Jan Adds, Jan Amort, Jan Ending, ..., Apr Ending, Amort Months, Comments, Account]
Rows 6-N:  Vendor line items with data values (N = last_data_row)
Row N+1:   Empty separator
Row N+2:   Month Totals    (formulas: =SUM(B6:B{N}) for each month column)
Row N+3:   Ending Balance  (formulas: month totals or rollforward calc per column)
Row N+4:   Variance        (formulas: GL Balance - Ending Balance per column)
Row N+5:   GL Balance      (static value in totals column O only)
```

### Control Row Pattern

For accounting rollforward schedules (beginning balance + adds - amortization = ending balance):

```python
from openpyxl.utils import get_column_letter

# Compute positions dynamically
first_data = 6
num_items = len(items)
last_data = first_data + num_items - 1
mt_row = last_data + 1   # Month Totals
eb_row = last_data + 2  # Ending Balance
var_row = last_data + 3 # Variance
gl_row = last_data + 4  # GL Balance

# Month columns: B=Jan Beginning, C=Jan Adds, D=Jan Amort, E=Jan Ending
#                F=Feb Adds, G=Feb Amort, H=Feb Ending, ..., N=Apr Ending, O=Total

# Row mt_row: Month Totals - sum line items for each column
for col in range(2, 15):  # B through N
    ws.cell(row=mt_row, column=col, value=f"=SUM({get_column_letter(col)}{first_data}:{get_column_letter(col)}{last_data})")
ws.cell(row=mt_row, column=15, value=f"=SUM(N{first_data}:N{last_data})")  # O

# Row eb_row: Ending Balance - carry forward from month totals
for col in range(2, 16):
    ws.cell(row=eb_row, column=col, value=f"={get_column_letter(col)}{mt_row}")

# Row var_row: Variance - difference (GL - Ending or Ending - Beginning)
for col in range(2, 16):
    ws.cell(row=var_row, column=col, value=f"={get_column_letter(col)}{eb_row}-{get_column_letter(col)}{mt_row}")

# Row gl_row: GL Balance - static value, only in column O
ws.cell(row=gl_row, column=15, value=float(gl_balance))
```

### Summary Sheet Layout
```
Row 1:     Title
Row 5:     Section header (e.g., "Bus Program #4310")
Row 7:     Ending Balance  (link to detail sheet O{eb_row})
Row 8:     Variance        (link to detail sheet O{var_row})
Row 9:     GL Balance      (link to detail sheet O{gl_row})
Row 11:    Section header (e.g., "Rail Program #4320")
Row 12:    Ending Balance  (link to detail sheet O{eb_row})
Row 13:    Variance        (link to detail sheet O{var_row})
Row 14:    GL Balance      (link to detail sheet O{gl_row})
Row 16:    Total Combined GL Balance (=B9+B14)
```

## Verification

Always verify output after writing:

```python
wb_check = openpyxl.load_workbook('/path/to/output.xlsx')
for sheet in wb_check.sheetnames:
    ws = wb_check[sheet]
    print(f"\n=== {sheet} ===")
    for row in ws.iter_rows(max_row=5, values_only=True):
        print(row)
```

**For rollforward schedules, run the verification script**:
```bash
/tmp/venv/bin/python3 scripts/verify_rollforward.py /path/to/output.xlsx
```

This catches incomplete control rows (formulas only in totals column) before submission.

## Common Patterns

### Metadata Block at Top of Sheet

```python
ws['A1'] = 'Field'
ws['B1'] = 'Value'
ws['A2'] = 'AsOfDate'
ws['B2'] = '2025-07-04'
ws['A3'] = 'PlanningHorizonEnd'
ws['B3'] = '2025-07-31'
# Data starts at row 5 or 6
```

### Multiple Sheets

```python
ws1 = wb.active
ws1.title = "Results"
ws2 = wb.create_sheet("Summary")
```

### Sheet Order Matters

Create sheets in desired order. The first sheet created is the default active sheet:

```python
wb = Workbook()
ws_summary = wb.active
ws_summary.title = "Transit Summary"
ws_bus = wb.create_sheet("Bus Program #4310")
ws_rail = wb.create_sheet("Rail Program #4320")
```

## Known Invariants (by sub-task)

### Harbor financial reconciliation
- **Column N**: April period values (Month Totals, Ending Balance)
- **Column O**: Total/Grand Total values, GL Balance in row 16
- **Control rows**: Month Totals (row 13), Ending Balance (row 14), Variance (row 15), GL Balance (row 16)
- **GL Balance**: Static value, not formula; goes in column O row 16 only
- Summary sheet must reference detail sheet control rows, not data rows

### Transit subsidy rollforward
- Same pattern as Harbor but with different account names
- Control rows must have formulas across all month columns (B-N), not just totals (O)
- Each month column follows: Beginning + Adds - Amortization = Ending

### Media rights rollforward
- Same pattern as Harbor/Transit
- Film Rights #2710, Music Rights #2720 as detail sheets
- Rights Summary as summary sheet with cross-sheet links
- Control rows 13-16 with complete formulas across B-N
- **Variable data row counts** per detail sheet - compute control row positions dynamically

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Anti-Patterns & Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Summary formulas overwrite data | Wrote formulas into data row columns | Use control rows for summaries, reference them from summary sheet |
| Control rows incomplete | Formulas only in totals column | Write formulas across ALL month columns for each control row |
| `ws2` referenced but undefined | Copied code with wrong variable name | Use consistent variable naming or pass worksheet explicitly |
| Cross-sheet formula syntax error | Missing quotes around sheet name with spaces | Use `="'Sheet Name'!A1"` format (single quotes around sheet name) |
| GL balance written as string | JSON value not cast to float | Use `float(ledger['gl_balance'])` |
| SUM formula references wrong range | Off-by-one in row indices | Verify: `SUM(C6:C11)` for 6 line items starting at row 6 |
| Wrong column refs in formulas | Used E/H/K instead of N/O | Harbor format uses N for April, O for totals/GL |
| Calculated values are None | Formula references broken sheet names | Verify sheet names match exactly (including spaces and #) |
| PEP 668 pip rejection | Running pip without venv on managed system | Use `python3 -m venv /tmp/venv` first |
| `date + int` TypeError | Adding int to date object | Use `timedelta(days=n)` for date arithmetic |
| Boolean fields rejected | Wrote string `"True"` instead of Python `True` | Pass raw bool values to `ws.cell()` |
| Duplicate sheets in output | Created sheet without naming active sheet first | Set `wb.active.title` before creating additional sheets |
| `MergedCell` read-only error | Wrote to a cell after it was merged | Write all values first, merge last; or skip merges entirely |
| **Wrong control row positions** | Hardcoded rows 13-16 instead of computing from data | Compute: `last_data + 1, +2, +3, +4` |
| **Different sheets, different control rows** | Assumed all detail sheets share same control row numbers | Compute per-sheet based on that sheet's data row count |
| Verification returns None | Using data_only=True to check formulas | Use data_only=False; verify formula strings, not values |
