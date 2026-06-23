# openpyxl Row Offset Handling

## The Problem

When writing data with `ws.cell(row=r, column=c, value=...)`, row numbering starts at 1, not 0:
- **Headers go in row 1**. Data rows must start at **row 2**.
- If iterating source rows with `for r in range(2, max_row+1)`, write to `ws.cell(row=r, ...)` — **not** `row=r-1`. Using `r-1` overwrites the header row with the first data row.

## Safer Alternative: `ws.append()`

Use `ws.append([...])` which auto-advances the row cursor:

```python
# Write headers first
ws.append(headers)

# Then write each data row
for row_data in data_rows:
    ws.append(row_data)
```

This eliminates row offset errors entirely — no manual row tracking needed.

## Common Failure Mode

If the first data row appears as headers in the output:
- Check your row offset logic
- Data should start at row 2, not row 1
- The header row should be written **once** before any data rows

## Verification

Check that row 1 contains headers, not data:

```python
from openpyxl import load_workbook
wb = load_workbook('output.xlsx')
ws = wb['Formatted Data']
headers = [ws.cell(1, c).value for c in range(1, ws.max_column+1)]
print('Row 1 (headers):', headers)
print('Row 2 (first data):', [ws.cell(2, c).value for c in range(1, ws.max_column+1)])
```

Row 1 should match your expected header names; Row 2 should contain the first data row values.