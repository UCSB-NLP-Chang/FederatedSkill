---
name: excel-processing
description: Read, process, and write Excel files using Python. Use when tasks require extracting data from .xlsx files, performing calculations on tabular data, or generating Excel outputs. Covers both pandas (DataFrame operations) and openpyxl (cell-level control). Essential for data transformation, queue planning, capacity modeling, and any workflow involving structured spreadsheet data.
---

# Excel Processing

## Choosing the Right Library

| Use Case | Recommended Library | Why |
|----------|---------------------|-----|
| DataFrame operations, bulk transformations | pandas | Higher-level, vectorized operations |
| Cell-level control, specific row/column access | openpyxl | Precise cell indexing, formatting |
| Complex formatting (fonts, borders, styles) | openpyxl | Full style API |
| Integration with existing openpyxl scripts | openpyxl | Consistent with queue-capacity-planning |

## Environment Setup (PEP 668 Systems)

Modern Debian/Ubuntu systems block direct pip installs. Use the override flag:

```bash
pip install pandas openpyxl --break-system-packages -q
```

**Required packages:**
- `pandas` - Data manipulation
- `openpyxl` - Excel read/write engine (required by pandas for .xlsx)

## pandas Approach

### Quick Start
```python
import pandas as pd

# Read specific sheet
df = pd.read_excel('file.xlsx', sheet_name='SheetName')

# Write to Excel with specific sheet name
df.to_excel('output.xlsx', sheet_name='Plan', index=False)
```

### Reading Wide/Horizontal Data
Excel files often store time-series data horizontally (weeks as columns). Use `iloc` for row-based extraction:

```python
# Row 0: headers, Row 1: week numbers, Row 2: values
weeks = df.iloc[0, 1:].values  # Skip first column (label)
values = df.iloc[2, 1:].values
```

### Writing Multi-Column Output
```python
output_df = pd.DataFrame({
    'Week': range(1, 41),
    'Metric_A': calc_a,
    'Metric_B': calc_b
})
output_df.to_excel('output.xlsx', sheet_name='Plan', index=False)
```

## openpyxl Approach

### Quick Start
```python
import openpyxl
wb = openpyxl.load_workbook('file.xlsx')
ws = wb['SheetName']  # or wb.active
```

### Check Structure First
```python
# List all sheets
print(wb.sheetnames)

# Read first few rows to understand layout
for row in ws.iter_rows(min_row=1, max_row=5, values_only=True):
    print(row)
```

### Horizontal Data Layout (metrics as rows, time as columns)
```python
# Example: Row 2 has week numbers, Row 4 has values
weeks = [ws.cell(row=2, column=c).value for c in range(2, 42)]
values = [ws.cell(row=4, column=c).value for c in range(2, 42)]
```

### Vertical Data Layout (standard tabular)
```python
for row in ws.iter_rows(min_row=2, values_only=True):
    col_a, col_b, col_c = row[0], row[1], row[2]
```

### Writing Excel Files
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

## Validation

Use the helper script for quick verification:
```bash
python3 scripts/verify_excel.py <file.xlsx> [sheet_name]
```

Manual checklist:
- [ ] Verify pandas/openpyxl import successfully
- [ ] Confirm sheet names match exactly (case-sensitive)
- [ ] Check `df.shape` or `ws.max_row/max_column` matches expected dimensions
- [ ] Inspect columns for unexpected unnamed/empty entries
- [ ] Validate output file opens without errors
- [ ] Spot-check calculated values

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ModuleNotFoundError: No module named 'pandas'` | Package not installed | Run pip install with `--break-system-packages` |
| `externally-managed-environment` error | PEP 668 protection | Use `--break-system-packages` flag |
| `Unnamed: N` columns | Empty Excel cells interpreted as headers | Specify `header=None` or clean source file |
| Sheet not found | Wrong sheet name | List sheets: `pd.ExcelFile('file.xlsx').sheet_names` or `wb.sheetnames` |
| Data appears transposed | Wrong orientation | Check if data is row-major vs column-major |
| None values in cells | Empty Excel cells | Use `or 0` or `if value is not None` |
| Type errors | Mixed int/float/str | Validate/cast as needed |

## Anti-Patterns

- **Don't** assume default sheet name 'Sheet1' - always verify or specify
- **Don't** use `pip install` without `--break-system-packages` on modern Debian/Ubuntu
- **Don't** ignore `Unnamed:` columns - they indicate header misalignment
- **Don't** write to Excel without `index=False` (pandas) unless row indices are meaningful
- **Don't** round numeric outputs before writing - pass raw values