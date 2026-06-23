# NaN vs "None" Handling in Excel Reports

## The Problem

When using pandas to write Excel files, `NaN` (Not a Number) values become empty cells in Excel, not the string `"None"`. However, when reading Excel back with pandas, empty cells are interpreted as `NaN`, which displays as `NaN` or empty in output.

This creates confusion when requirements specify the string `"None"` should appear in cells.

## Solutions

### Option 1: Explicit String Assignment (Recommended)

Assign the string `"None"` explicitly before writing:

```python
# Create boolean mask for rows with errors
has_errors = df['Total Errors'] > 0

# Build error text only for rows with errors
error_parts = []
if 'Qty Variance' in df.columns:
    error_parts.append(df['Qty Variance'].map({1: 'Qty Variance', 0: ''}))
if 'Cold Chain Error' in df.columns:
    error_parts.append(df['Cold Chain Error'].map({1: 'Cold Chain Error', 0: ''}))

if error_parts:
    combined = error_parts[0]
    for part in error_parts[1:]:
        combined = combined + ', ' + part
    combined = combined.str.replace(', $', '', regex=True)
    combined = combined.str.replace('^, ', '', regex=True)
    df['Error Summary'] = combined.where(has_errors, 'None')
else:
    df['Error Summary'] = 'None'
```

### Option 2: Fill NaN After Calculation

If you must use NaN during processing:

```python
df['Error Summary'] = df['Error Summary'].fillna('None')
# But this only works if you actually had NaN, not if you never set the column
```

### Option 3: Post-Process with openpyxl

After writing with pandas, open and fix specific cells:

```python
from openpyxl import load_workbook

wb = load_workbook('output.xlsx')
ws = wb['Formatted Data']

# Find Error Summary column
header = [cell.value for cell in ws[1]]
col_idx = header.index('Error Summary') + 1

for row in range(2, ws.max_row + 1):
    cell = ws.cell(row=row, column=col_idx)
    if cell.value is None or str(cell.value) in ['nan', 'NaN']:
        cell.value = 'None'

wb.save('output.xlsx')
```

## Verification

Always verify with openpyxl, not pandas:

```python
# Wrong - pandas may show NaN for the string "None" if it decides to type-cast
import pandas as pd
df_check = pd.read_excel('file.xlsx')
print(df_check['Error Summary'].tolist())  # May show NaN!

# Right - check actual cell values
from openpyxl import load_workbook
wb = load_workbook('file.xlsx')
ws = wb['Formatted Data']
for row in ws.iter_rows(min_row=2, max_row=4, values_only=True):
    print(repr(row[-1]))  # Shows actual string value
```

## Common Anti-Patterns

1. **Assuming `None` in Python becomes `"None"` in Excel**: It becomes an empty cell.
2. **Trusting pandas readback**: Pandas type inference may convert your strings back to NaN on read.
3. **Using `dropna()` or `fillna()` on the final output**: This modifies the data, not the Excel representation.

## Decision Rule

If the requirement says: "Write 'None' in cells without errors"
→ Explicitly assign the string `"None"` in Python before writing, or post-process with openpyxl.
