---
name: excel-python-processing
description: Read, write, and manipulate Excel files in Python using openpyxl (pandas fallback). Use when processing .xlsx files, especially in environments where pandas may not be installed.
---

# Excel Processing in Python

## When to Use
- Reading or writing .xlsx files
- Pandas is not available or fails to import
- Need cell-level control over Excel output
- Creating structured reports or data exports

## Tool Selection

| Situation | Use | Reason |
|-----------|-----|--------|
| Pandas available, simple data | `pd.read_excel()`, `df.to_excel()` | Fastest for dataframes |
| Pandas unavailable | `openpyxl` | Always works, no dependencies beyond install |
| Need formatting, formulas | `openpyxl` | Full Excel feature support |
| Large files, performance critical | `openpyxl` read-only mode | Memory efficient |

## Common Patterns

### Reading Excel with openpyxl
```python
import openpyxl

wb = openpyxl.load_workbook('file.xlsx')
ws = wb['SheetName']

# Read all data rows
for row in ws.iter_rows(min_row=2, values_only=True):  # Skip header
    if row[0] is not None:  # Stop at empty rows
        # process row
        pass
```

### Writing Excel with openpyxl
```python
from openpyxl import Workbook

wb = Workbook()
ws = wb.active
ws.title = 'Plan'

# Write headers
headers = ['Col1', 'Col2', 'Col3']
ws.append(headers)

# Write data rows
for row_data in data_list:
    ws.append(row_data)

wb.save('output.xlsx')
```

## Critical Validation Steps

1. **Check for trailing empty rows** - `ws.append()` or iteration can include None rows. Always filter:
   ```python
   data = [row for row in ws.iter_rows(values_only=True) if row[0] is not None]
   ```

2. **Verify row count matches expectations**:
   ```python
   actual_rows = ws.max_row - 1  # minus header
   expected_rows = len(data_list)
   assert actual_rows == expected_rows, f'Expected {expected_rows}, got {actual_rows}'
   ```

3. **Validate numeric precision** - Excel may round displayed values. Check actual cell values:
   ```python
   cell_value = ws.cell(row=2, column=3).value  # Actual stored value
   ```

## Anti-Patterns to Avoid

- **Don't assume pandas is available** - Always have openpyxl as fallback
- **Don't ignore None rows** - Trailing empty rows cause test failures
- **Don't trust displayed Excel values** - Verify actual cell values programmatically
- **Don't skip verification** - Always read back and validate output structure

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: pandas` | Switch to openpyxl |
| Extra empty rows in output | Filter None rows before writing, verify max_row after save |
| Wrong sheet name | Check `wb.sheetnames` first |
| Numbers stored as text | Use `float(cell.value)` or format cells as numbers |

## Verification Checklist

Before submitting Excel outputs:
1. Read back the file and verify row count
2. Check first and last data rows are not None/empty
3. Confirm sheet name matches requirements
4. Validate column headers exactly match specification