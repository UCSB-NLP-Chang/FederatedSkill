---
name: excel-workbook-manipulation
description: Create, read, and modify Excel workbooks using Python. Use when tasks require reading source Excel files, performing calculations, generating new workbooks with multiple sheets, or transforming Excel data. Handles openpyxl/pandas installation, date handling, and output verification.
---

# Excel Workbook Manipulation

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

## Anti-Patterns

- **Never** run `pip install` without a venv on externally-managed systems - it will fail with PEP 668 error
- **Never** add integers directly to date objects - use `timedelta(days=n)`
- **Never** assume Excel dates are strings - check for `datetime` and `date` types
- **Never** skip verification after writing - openpyxl may silently accept invalid data