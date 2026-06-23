# Formula and Date Handling Patterns

## Date Handling in openpyxl

### datetime.datetime vs datetime.date
openpyxl stores dates as `datetime.datetime` internally, NOT `datetime.date`.

**Conversion Pattern**:
```python
from datetime import datetime, date

cell_val = ws.cell(row=r, column=2).value

# Always convert before comparison/lookup
if isinstance(cell_val, datetime):
    cell_date = cell_val.date()
elif isinstance(cell_val, date):
    cell_date = cell_val
else:
    # Handle string or None
    cell_date = parse_date(cell_val)

# Use for dictionary lookups
po_due = po_dict.get(cell_date, 0)
```

### Writing Date Series
- Row 4 (first data row): literal `datetime.date(2018, 1, 22)` object
- Row 5+: formula `=B4+1`, `=B5+1`, etc. (increments by 1 day)

```python
from datetime import date
ws['B4'] = date(2018, 1, 22)  # Literal
ws['B5'] = '=B4+1'            # Formula
```

---

## Cumulative Formula Patterns

### Running Balance (First Row)
```python
ws['E4'] = '=D4-C4'  # PO_due - Production
```

### Running Balance (Subsequent Rows)
```python
ws['E5'] = '=E4+D5-C5'  # Previous_cum + PO_due - Production
```

### Anchoring Pattern
- Always anchor to previous row: `=E{row-1}+D{row}-C{row}`
- Use `row` variable in loop: `ws[f'E{row}'] = f'=E{row-1}+D{row}-C{row}'`

---

## Column Type Rules

### Constant Columns (Numeric Values)
- Columns C, D, F, G, I: daily production, PO due amounts
- Write as integers: `ws[f'C{row}'] = 135`

### Formula Columns (Cumulative Calculations)
- Columns E, H, J: cumulative variance, running totals
- Write as formulas: `ws[f'E{row}'] = f'=E{row-1}+D{row}-C{row}'`

### Verification Check
```python
# Formula columns must have data_type 'f'
assert ws['E5'].data_type == 'f', "E5 should be formula"

# Constant columns must NOT have data_type 'f'
assert ws['C5'].data_type != 'f', "C5 should be value not formula"
```