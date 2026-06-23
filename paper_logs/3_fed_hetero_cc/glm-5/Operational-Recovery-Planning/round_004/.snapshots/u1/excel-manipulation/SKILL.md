---
name: excel-manipulation
description: Read, write, and manipulate Excel files using openpyxl. Use when tasks involve Excel input/output, data transformation between Excel and other formats, or creating formatted spreadsheet reports.
---

# Excel Manipulation with openpyxl

## Quick Start

```python
import openpyxl
wb = openpyxl.load_workbook('file.xlsx')
ws = wb['SheetName']  # or wb.active
```

## Reading Excel Files

### Check Structure First
Always inspect the file layout before processing:
```python
# List all sheets
print(wb.sheetnames)

# Read first few rows to understand layout
for row in ws.iter_rows(min_row=1, max_row=5, values_only=True):
    print(row)
```

### Horizontal Data Layout
When data is organized with metrics as rows and time periods/categories as columns:
```python
# Example: Row 2 has week numbers, Row 4 has values
weeks = [ws.cell(row=2, column=c).value for c in range(2, 42)]
values = [ws.cell(row=4, column=c).value for c in range(2, 42)]
```

### Vertical Data Layout
When data is in standard tabular format (headers in row 1, data below):
```python
for row in ws.iter_rows(min_row=2, values_only=True):
    col_a, col_b, col_c = row[0], row[1], row[2]
```

## Writing Excel Files

### Create New Workbook
```python
wb = openpyxl.Workbook()
ws = wb.active
ws.title = 'Plan'

# Write headers
headers = ['Week', 'Value', 'Status']
for col, header in enumerate(headers, 1):
    ws.cell(row=1, column=col, value=header)

# Write data rows
for row_idx, data in enumerate(data_list, 2):
    for col_idx, value in enumerate(data, 1):
        ws.cell(row=row_idx, column=col_idx, value=value)

wb.save('output.xlsx')
```

### Basic Formatting
```python
from openpyxl.styles import Font, Alignment, Border, Side

# Bold headers
for col in range(1, num_cols + 1):
    ws.cell(row=1, column=col).font = Font(bold=True)

# Column width
ws.column_dimensions['A'].width = 15
```

## Common Patterns

### Read Reference File, Write Output
1. Load reference file to get input data
2. Process data with business logic
3. Create new workbook for output (never modify input in place)
4. Save with descriptive filename

### Verify Output
Always verify written files:
```python
wb_check = openpyxl.load_workbook('output.xlsx')
ws_check = wb_check['SheetName']
print(f'Rows: {ws_check.max_row}, Columns: {ws_check.max_column}')
print('Headers:', [ws_check.cell(row=1, column=c).value for c in range(1, ws_check.max_column + 1)])
```

## Troubleshooting

- **File not found**: Check path is absolute or relative to working directory
- **KeyError on sheet name**: Use `wb.sheetnames` to list available sheets
- **None values**: Check for empty cells; use `or 0` or `if value is not None`
- **Type errors**: Excel may return int, float, or str; validate/cast as needed