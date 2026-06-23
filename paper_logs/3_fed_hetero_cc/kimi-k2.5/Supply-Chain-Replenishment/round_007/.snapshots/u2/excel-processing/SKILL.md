---
name: excel-processing
description: Read, process, and write Excel (.xlsx) workbooks using Python/openpyxl. Use when working with binary Excel files, multi-sheet workbooks, or data transformation tasks involving spreadsheets.
---

# Excel Processing with openpyxl

## When to Use
- Reading or writing .xlsx files (binary format)
- Multi-sheet workbook operations
- Data transformation requiring Excel input/output
- Tasks involving formulas, formatting, or structured spreadsheet data

## Anti-Pattern: Read Tool on Binary Excel
The Read tool cannot read binary .xlsx files. Attempting to use it will fail with:
```
This tool cannot read binary files. The file appears to be a binary .xlsx file.
```

**Always use Python with openpyxl for Excel files.**

## Basic Workflow

### 1. Check/Install openpyxl
```bash
python3 -c "import openpyxl; print('openpyxl available')" 2>/dev/null || pip install openpyxl
```

### 2. Read Excel Files
```python
import openpyxl

wb = openpyxl.load_workbook('/path/to/file.xlsx', data_only=True)
sheet = wb['SheetName']

# Iterate rows
for row in sheet.iter_rows(values_only=True):
    print(row)
```

### 3. Create Output Workbook
```python
from openpyxl import Workbook
from openpyxl.utils import get_column_letter

wb = Workbook()
ws = wb.active
ws.title = 'SheetName'

# Write headers and data
ws.append(['Column1', 'Column2', 'Column3'])
ws.append(['Value1', 'Value2', 'Value3'])

# Save
wb.save('/path/to/output.xlsx')
```

## Common Patterns

### Inspect Workbook Structure
```python
wb = openpyxl.load_workbook('/path/to/file.xlsx', data_only=True)
print(f"Sheets: {wb.sheetnames}")
for sheet_name in wb.sheetnames:
    sheet = wb[sheet_name]
    print(f"\n=== {sheet_name} ===")
    for i, row in enumerate(sheet.iter_rows(values_only=True)):
        if i < 10:  # First 10 rows
            print(f"Row {i+1}: {row}")
```

### Handle Dates in Excel
Excel stores dates as datetime objects. Use `data_only=True` to get resolved values:
```python
from datetime import datetime, date

# Dates come through as datetime objects
for row in sheet.iter_rows(values_only=True):
    eta = row[5]  # May be datetime or string
    if isinstance(eta, datetime):
        eta_date = eta.date()
    elif isinstance(eta, str):
        # Handle string dates or invalid values
        try:
            eta_date = datetime.strptime(eta, '%Y-%m-%d').date()
        except ValueError:
            continue  # Skip invalid dates
```

### Multi-Sheet Output with Metadata
```python
wb = Workbook()

# Sheet 1: Metadata + Data
ws1 = wb.active
ws1.title = 'Zone_Coverage'
ws1['A1'] = 'Field'
ws1['B1'] = 'Value'
ws1['A2'] = 'AsOfDate'
ws1['B2'] = '2026-02-02'
# ... add data rows starting at row 6

# Sheet 2: Summary/Gap list
ws2 = wb.create_sheet('Dispatch_Gap_List')
ws2.append(['Zone', 'SKU', 'Required_Date', 'Pallets'])
# ... add filtered rows

wb.save('/path/to/output.xlsx')
```

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Verification Step
Always verify output by reading back:
```python
wb_check = openpyxl.load_workbook('/path/to/output.xlsx', data_only=True)
for sheet_name in wb_check.sheetnames:
    print(f"=== {sheet_name} ===")
    for row in wb_check[sheet_name].iter_rows(values_only=True):
        print(row)
```

## Troubleshooting
- **Empty cells**: Return `None` with `values_only=True`
- **Date handling**: Check `isinstance(value, datetime)` before date operations
- **Numeric precision**: Excel may show rounded values; actual values have full precision
- **Missing sheets**: Use `sheet_name in wb.sheetnames` before accessing
- **Corrupted files**: Try `openpyxl.load_workbook(path, read_only=True)` for recovery
