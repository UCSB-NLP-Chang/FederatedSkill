---
name: excel-manipulation
description: Read, write, and transform Excel workbooks in Python using openpyxl. Use when working with .xlsx files, multi-sheet workbooks, inventory data, cross-sheet formulas, control/summary rows, or when pip install fails with externally-managed-environment error.
---

# Excel Manipulation with openpyxl

## Quick Start Pattern

When openpyxl is not installed, modern systems (Debian 12+, Ubuntu 23.04+) block system-wide pip installs:

```bash
# Create venv and install openpyxl
python3 -m venv /tmp/venv
/tmp/venv/bin/pip install openpyxl -q

# Run Python scripts using the venv interpreter
/tmp/venv/bin/python3 your_script.py
```

**Important**: The venv path `/tmp/venv` may not persist between sessions. Always verify the venv exists before using it, or recreate it if needed:
```bash
# Check if venv exists, create if missing
[ -x /tmp/venv/bin/python3 ] || (python3 -m venv /tmp/venv && /tmp/venv/bin/pip install openpyxl -q)
```

## Reading Workbooks

```python
import openpyxl
from datetime import datetime

wb = openpyxl.load_workbook('/path/to/file.xlsx')

# List sheets
print(wb.sheetnames)

# Access a sheet
ws = wb['Sheet Name']

# Read cell value
value = ws['A1'].value

# Iterate rows (skip header with min_row=2)
for row in ws.iter_rows(min_row=2, values_only=True):
    print(row)
```

## Iterating Data Rows Safely

When processing data, always skip header rows to avoid type errors:

```python
# CORRECT: Skip header row
for row in ws.iter_rows(min_row=2, values_only=True):
    part_code, units, consumption = row
    if units > 0:  # Safe numeric comparison
        process(part_code, units)

# WRONG: Includes header row - causes TypeError when comparing strings to numbers
for row in ws.iter_rows(values_only=True):
    units = row[1]  # First row has 'Current_Units' string, not a number
    if units > 0:  # TypeError: '>' not supported between 'str' and 'int'
        process(row)
```

**Type-check before numeric operations:**

```python
for row in ws.iter_rows(min_row=2, values_only=True):
    if row[0] is None:  # Skip empty rows
        continue
    units = row[1]
    if isinstance(units, (int, float)):
        doh = units / daily_consumption
```

## Handling Date Formats

Excel dates may appear as `datetime` objects OR strings. Always handle both:

```python
from datetime import datetime

def parse_excel_date(val):
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        return datetime.strptime(val, '%Y-%m-%d').date()
    return None
```

## Formulas vs Values

`load_workbook()` returns formula strings by default. For calculated values:

```python
# Option 1: Read with data_only=True (requires file was saved with Excel)
wb = openpyxl.load_workbook('/path/to/file.xlsx', data_only=True)

# Option 2: Evaluate simple formulas manually
# Formula like '=80*C2' needs manual calculation
```

## Writing Workbooks

```python
from openpyxl import Workbook
from openpyxl.styles import Font

wb = Workbook()
ws = wb.active
ws.title = 'Results'

# Write headers
headers = ['SKU', 'Quantity', 'Date']
ws.append(headers)

# Make headers bold
for cell in ws[1]:
    cell.font = Font(bold=True)

# Write data rows
ws.append(['PRD-001', 100, datetime(2025, 7, 4)])

# Save
wb.save('/path/to/output.xlsx')
```

### Multi-Sheet Workbooks

```python
from openpyxl import Workbook

wb = Workbook()

# First sheet (rename the default active sheet)
ws1 = wb.active
ws1.title = 'Summary'
ws1.append(['Metric', 'Value'])

# Add additional sheets
ws2 = wb.create_sheet('Details')
ws2.append(['ID', 'Name', 'Amount'])

ws3 = wb.create_sheet('Calculations')
ws3.append(['Formula', 'Result'])

wb.save('/path/to/multi_sheet_output.xlsx')
```

### Cross-Sheet Formulas

When creating formulas that reference other sheets, use the sheet name in single quotes if it contains spaces:

```python
from openpyxl import Workbook

wb = Workbook()
ws_summary = wb.active
ws_summary.title = 'Summary'
ws_data = wb.create_sheet('Data')

# Add data to Data sheet
ws_data['A1'] = 'Total'
ws_data['B1'] = 1000

# Reference Data sheet from Summary (note: single quotes for sheet names with spaces)
ws_summary['A1'] = 'Linked Total'
ws_summary['B1'] = "='Data'!B1"  # Simple reference

# For sheet names with spaces or special characters:
ws_bus = wb.create_sheet('Bus Program #4310')
ws_bus['O12'] = 5000
ws_summary['B7'] = "='Bus Program #4310'!O12"  # Single quotes required
```

### Control Rows and Summary Formulas

For financial schedules with control rows (totals, balances, variances):

```python
from openpyxl import Workbook
from openpyxl.styles import Font

wb = Workbook()
ws = wb.active
ws.title = 'Schedule'

# Header row
headers = ['Account', 'Vendor', 'Jan', 'Feb', 'Mar', 'Total']
ws.append(headers)

# Data rows (rows 2-7)
for vendor in vendors:
    ws.append([vendor['account'], vendor['name'], vendor['jan'], vendor['feb'], vendor['mar']])

# Control rows at specific positions
row = ws.max_row + 1
ws[f'A{row}'] = 'Month Totals'
ws[f'F{row}'] = f'=SUM(F2:F{row-1})'  # Sum of data rows

row += 1
ws[f'A{row}'] = 'Ending Balance'
ws[f'F{row}'] = f'=F{row-1}'  # Reference to totals

row += 1
ws[f'A{row}'] = 'Variance'
ws[f'F{row}'] = f'=F{row-2}-F{row-1}'  # Calculation

row += 1
ws[f'A{row}'] = 'GL Balance'
ws[f'F{row}'] = gl_balance_value  # Hard-coded value from source

# Make control rows bold
for r in range(ws.max_row - 3, ws.max_row + 1):
    ws[f'A{r}'].font = Font(bold=True)
```

## Verification Pattern

After creating a workbook, verify structure matches requirements:

```python
wb = openpyxl.load_workbook('/path/to/output.xlsx')
print(f"Sheets: {wb.sheetnames}")
for sheet in wb.sheetnames:
    ws = wb[sheet]
    print(f"\n=== {sheet} ===")
    print(f"Dimensions: {ws.dimensions}")
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i < 5:  # First 5 rows
            print(row)
```

**Critical**: Verify both data AND structure. A workbook can have correct data values but wrong row/column positions, sheet names, or formula references. Check:
1. Sheet names and order match requirements exactly
2. Data starts at the correct row (e.g., row 6 vs row 1)
3. Control/summary rows are at expected positions
4. Formulas reference correct cells
5. Cross-sheet formulas use correct sheet names (with single quotes for names with spaces)
6. **Column count and alignment** - Verify all expected columns are present; print all column indices during verification to catch gaps

### Deep Verification for Complex Workbooks

For workbooks with formulas and cross-sheet references, verify calculations:

```python
import openpyxl

wb = openpyxl.load_workbook('/path/to/output.xlsx')

# Check cross-sheet formulas are correct
ws_summary = wb['Summary']
formula = ws_summary['B7'].value
print(f"Formula in B7: {formula}")  # Should be like ='Bus Program #4310'!O12

# Verify sheet names in formulas match actual sheet names
for sheet in wb.sheetnames:
    ws = wb[sheet]
    for row in ws.iter_rows():
        for cell in row:
            if cell.value and isinstance(cell.value, str) and cell.value.startswith('='):
                print(f"{sheet}!{cell.coordinate}: {cell.value}")

# Check that all required data is present
ws_data = wb['Data Sheet']
expected_rows = 10
actual_rows = ws_data.max_row
print(f"Expected {expected_rows} rows, got {actual_rows}")

# Verify ALL columns are present (not just sample columns)
expected_cols = 17
actual_cols = ws_data.max_column
print(f"Expected {expected_cols} columns, got {actual_cols}")
for col_idx in range(1, actual_cols + 1):
    col_letter = openpyxl.utils.get_column_letter(col_idx)
    header = ws_data[f'{col_letter}1'].value
    print(f"Col {col_idx} ({col_letter}): {header}")
```

## Run Tests Before Claiming Success

**Mandatory step**: If test files exist in the workspace (e.g., `test_output.py`), run them BEFORE claiming the task is complete:

```bash
# Check for test files
ls test_*.py 2>/dev/null && pytest test_*.py -v

# Or with specific test runner
python -m pytest test_output.py -v
```

Agent verification scripts may miss edge cases that tests catch. A failed test means the output is incorrect, even if your manual verification looks correct.

## Common Pitfalls

1. **externally-managed-environment error**: Always use a venv, never try `--break-system-packages`
2. **venv not found**: The venv at `/tmp/venv` may not persist. Verify existence before use or recreate.
3. **Header row in data**: Use `min_row=2` in `iter_rows()` to skip headers; TypeError on numeric comparison usually means header included
4. **Mixed date formats**: Check `isinstance(val, datetime)` before processing
5. **Formula strings**: `data_only=True` only works if Excel saved the file; otherwise parse manually
6. **Empty rows**: Check for `None` values when iterating
7. **Column widths**: Not auto-adjusted; set explicitly if needed
8. **Read tool line numbers**: When using Read tool on CSV/text files, the output includes line number prefixes (e.g., `1\tvendor,beginning_balance...`). These are NOT part of the file content. The actual file content starts after the tab character.
9. **Cross-sheet formula syntax**: Sheet names with spaces or special characters MUST be wrapped in single quotes: `='Bus Program #4310'!O12`, not `=Bus Program #4310!O12`
10. **Verification depth**: Don't just check structure - verify formulas, cross-references, and that calculated values match expected totals from source data
11. **Column alignment**: When writing from CSV to Excel, verify all columns are present and in correct order. Print all column indices during verification, not just sample columns, to catch skipped or misaligned data.
