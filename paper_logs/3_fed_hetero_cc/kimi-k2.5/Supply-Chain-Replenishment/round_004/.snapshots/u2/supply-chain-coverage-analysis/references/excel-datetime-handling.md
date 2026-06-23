# Excel Datetime Handling Patterns

This reference file provides patterns for handling datetime values when extracting data from Excel workbooks using openpyxl.

## Key Issue: datetime.datetime vs datetime.date

openpyxl returns `datetime.datetime` objects for date cells, not `datetime.date` objects. Direct comparisons between these types cause `TypeError`.

## Normalization Pattern

Always normalize date values before comparisons:

```python
from datetime import datetime, date

def normalize_date(val):
    """Convert datetime or date to date. Returns None if invalid."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    return None
```

## Common Failure Patterns

### TypeError: comparison between str and int
**Cause**: Reading a header row or metadata row as data.
**Fix**: Identify actual header row by scanning for known column names.

```python
# Find header row by scanning
for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
    if 'SKU_Ref' in row or 'Cases_On_Rack' in row:
        header_row = row_idx
        break
```

### TypeError: comparison between datetime.datetime and datetime.date
**Cause**: openpyxl returns `datetime.datetime` objects for date cells.
**Fix**: Check type and convert explicitly using the normalization pattern above.

### Invalid date string in cell
**Cause**: Cell contains string like 'bad-date' instead of actual date.
**Fix**: Check `isinstance(val, datetime)` before treating as date; skip invalid rows.

```python
eta = row['eta']
if not isinstance(eta, datetime):
    continue  # Skip invalid dates
eta_date = eta.date()
```

## Debugging Pattern

When extraction fails, print types and values:

```python
for row in ws.iter_rows(min_row=1, max_row=5):
    for cell in row:
        print(f"{cell.coordinate}: value={cell.value}, type={type(cell.value)}")
```

## Anti-Patterns

- **Do not** assume headers are in row 1
- **Do not** compare cell values directly without type checking
- **Do not** use `str()` on datetime cells expecting a specific format
- **Do not** skip the structure inspection step when file format is unknown