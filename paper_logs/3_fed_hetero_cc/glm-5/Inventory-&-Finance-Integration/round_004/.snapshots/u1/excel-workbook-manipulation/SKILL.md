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
ws['B7'] = "='Compute Pool #8100'!N12"

# Reference with row iteration
for i, row in enumerate(range(12, 18), start=7):
    ws[f'B{i}'] = f"='Detail Sheet'!N{row}"
```

**Important**: Sheet names with spaces or special characters must be enclosed in single quotes in formulas: `'Sheet Name'!A1` not `Sheet Name!A1`.

## Financial Reconciliation Workbooks (Harbor Format)

### Detail Sheet Layout (per pool/account)
```
Row 6:     Headers [Vendor, Jan Ending Balance, Feb..., Mar..., Apr..., Total Amortization, GL Balance]
Rows 7-12: Vendor line items with formulas in Total Amortization column
Row 13:    Month Totals    (formula: =SUM(N7:N12) for April, =SUM(O7:O12) for total)
Row 14:    Ending Balance  (formula: =N13, =O13)
Row 15:    Variance        (formula: =N14, =O14)
Row 16:    GL Balance      (static value in column O only)
```

### Summary Sheet Layout
```
Row 7:  Month Totals     (links to detail sheets column N - April)
Row 12: (blank label)    (links to column N row 13)
Row 13: (blank label)    (links to column O row 13 - detail totals)
Row 14: (blank label)    (links to column O row 16 - GL balance)
Row 16: Net Position     (=B7+B13+B14)
```

### Control Row Pattern

For accounting rollforward schedules (beginning balance + adds - amortization = ending balance):

```python
# Control rows after line items
control_rows = ['Month Totals', 'Ending Balance', 'Variance', 'GL Balance']

# Calculate totals row
for col in range(2, 15):  # B through N
    ws.cell(row=totals_row, column=col, value=f"=SUM({get_column_letter(col)}6:{get_column_letter(col)}{totals_row-1})")

# Variance row: GL Balance - Ending Balance
ws.cell(row=variance_row, column=col, value=f"={gl_cell}-{ending_cell}")
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

For formula validation, use both modes:
```python
# Verify formulas written correctly
wb = openpyxl.load_workbook(path, data_only=False)
# Check formula strings exist

# Verify calculations work
wb_calc = openpyxl.load_workbook(path, data_only=True)
# Check numeric values, not None
```

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
ws_summary.title = "Capacity Summary"
ws_compute = wb.create_sheet("Compute Pool #8100")
ws_storage = wb.create_sheet("Storage Pool #8200")
```

## Known Invariants (by sub-task)

### Harbor financial reconciliation
- **Column N**: April period values (Month Totals, Ending Balance)
- **Column O**: Total/Grand Total values, GL Balance in row 16
- **Control rows**: Month Totals (row 13), Ending Balance (row 14), Variance (row 15), GL Balance (row 16)
- **GL Balance**: Static value, not formula; goes in column O row 16 only
- Summary sheet must reference detail sheet control rows, not data rows

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Anti-Patterns & Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Summary formulas overwrite data | Wrote formulas into data row columns | Use control rows for summaries, reference them from summary sheet |
| `ws2` referenced but undefined | Copied code with wrong variable name | Use consistent variable naming or pass worksheet explicitly |
| Cross-sheet formula syntax error | Missing quotes around sheet name with spaces | Use `="'Sheet Name'!A1"` format (single quotes around sheet name) |
| GL balance written as string | JSON value not cast to float | Use `float(ledger['gl_balance'])` |
| SUM formula references wrong range | Off-by-one in row indices | Verify: `SUM(C6:C11)` for 6 line items starting at row 6 |
| Wrong column refs in formulas | Used E/H/K instead of N/O | Harbor format uses N for April, O for totals/GL |
| Calculated values are None | Formula references broken sheet names | Verify sheet names match exactly (including spaces and #) |
| PEP 668 pip rejection | Running pip without venv on managed system | Use `python3 -m venv /tmp/venv` first |
| `date + int` TypeError | Adding int to date object | Use `timedelta(days=n)` for date arithmetic |
| Boolean fields rejected | Wrote string `"True"` instead of Python `True` | Pass raw bool values to `ws.cell()` |
