---
name: excel-python-operations
description: Read and write Excel files using Python's openpyxl library. Use when tasks involve extracting data from Excel reference files, creating Excel reports, or transforming spreadsheet data.
---

# Excel Operations with Python

## When to Use
- Reading reference data from Excel files (.xlsx)
- Creating structured Excel output reports
- Extracting specific rows, columns, or cells from spreadsheets
- Writing multi-column data with headers

## Reading Excel Files

```python
import openpyxl

# Load existing workbook
wb = openpyxl.load_workbook('/path/to/file.xlsx')

# List sheet names
print(wb.sheetnames)

# Access a sheet
ws = wb['SheetName']  # by name
ws = wb.active        # first sheet

# Iterate rows with values only (recommended)
for row in ws.iter_rows(values_only=True):
    print(row)  # tuple of cell values

# Read specific cell
value = ws['A1'].value
value = ws.cell(row=1, column=1).value
```

## Writing Excel Files

```python
import openpyxl
from openpyxl.styles import Font

# Create new workbook
wb = openpyxl.Workbook()
ws = wb.active
ws.title = 'SheetName'

# Write headers (bold)
headers = ['Column1', 'Column2', 'Column3']
ws.append(headers)
for col in range(1, len(headers) + 1):
    ws.cell(row=1, column=col).font = Font(bold=True)

# Write data rows
for row_data in data_rows:
    ws.append(row_data)

# Save
wb.save('/path/to/output.xlsx')
```

## Common Patterns

### Extract row data by label
```python
for row in ws.iter_rows(values_only=True):
    if row[0] == 'Target Label':
        values = row[1:]  # skip label column
        break
```

### Transpose horizontal data to vertical
```python
# If data is in row format: ('Label', val1, val2, val3, ...)
label_row = next(ws.iter_rows(min_row=3, max_row=3, values_only=True))
values = label_row[1:]  # skip the label in first column
```

## Troubleshooting
- **Empty cells return `None`**: Check for `None` before processing
- **Numeric precision**: Excel stores floats; use `round()` for display
- **File locked**: Ensure file is closed in other applications before writing
- **Sheet not found**: Use `wb.sheetnames` to verify available sheets