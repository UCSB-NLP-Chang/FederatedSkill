# Template Workbook Preservation Pattern

## When to Use
When the task provides a template Excel file containing sheets (e.g., `Overview`) that must appear unchanged in the final output workbook alongside your generated data sheets.

## Pattern

```python
from openpyxl import Workbook, load_workbook

template_wb = load_workbook('Audit_Template.xlsx')
out_wb = Workbook()

# CRITICAL: Remove the default 'Sheet' created by Workbook()
default_sheet = out_wb.active
out_wb.remove(default_sheet)

# Copy template sheet(s) cell-by-cell
for src_name in ['Overview']:  # Add other template sheet names as needed
    src_ws = template_wb[src_name]
    dst_ws = out_wb.create_sheet(src_name)
    for row in src_ws.iter_rows(min_row=1, max_row=src_ws.max_row, max_col=src_ws.max_column, values_only=False):
        for cell in row:
            dst_ws.cell(row=cell.row, column=cell.column, value=cell.value)

# Now add your data sheets
ws_raw = out_wb.create_sheet('RawData')
ws_raw.append(headers)
for r in data_rows:
    ws_raw.append(r)

# ... add Formatted Data, Summary ...

out_wb.save('output.xlsx')
```

## Why Cell-by-Cell Copy?
- Preserves cell values without carrying over hidden metadata, merged cells, or conditional formatting that might interfere with verification.
- Avoids issues with `shutil.copy` or `copy_worksheet` which can carry over references to external files or broken named ranges.
- Simple, deterministic, and works across openpyxl versions.

## Verification
After saving, verify the template sheet is intact:

```python
wb = load_workbook('output.xlsx')
assert 'Overview' in wb.sheetnames
ws = wb['Overview']
# Check first few cells match expected template content
assert ws.cell(1, 1).value == 'Expected Title'
```

## Common Pitfalls
1. **Forgetting to remove default sheet**: `Workbook()` always creates a sheet named `'Sheet'`. If not removed, the output will have an extra sheet that may cause verifier failures.
2. **Using `copy_worksheet`**: This method can carry over broken references. Prefer cell-by-cell copy for template sheets.
3. **Copying after data sheets**: Copy template sheets first so they appear in the expected order (Overview before RawData).
