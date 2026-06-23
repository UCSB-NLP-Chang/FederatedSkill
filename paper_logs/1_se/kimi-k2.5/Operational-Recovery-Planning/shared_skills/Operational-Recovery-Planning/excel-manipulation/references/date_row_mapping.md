# Date-to-Row Mapping for Excel Date Columns

Use when placing data at specific calendar dates in a date-sequenced column.

## Formula

For a date column starting at row `start_row` with date `start_date`:

```python
row_offset = (target_date - start_date).days
row_number = start_row + row_offset
```

## Example: Place PO Due Dates at Correct Rows

```python
from datetime import datetime

# Date column B starts at B4 with 2018-01-22
start_date = datetime(2018, 1, 22)
start_row = 4

po_dates = {
    datetime(2018, 1, 22): (1065, 855),
    datetime(2018, 2, 1): (855, 555),
    datetime(2018, 2, 12): (900, 900),
    datetime(2018, 2, 26): (900, 575),
    datetime(2018, 3, 31): (900, 575),
    datetime(2018, 5, 1): (900, 575),
}

for po_date, (wheat_po, canola_po) in po_dates.items():
    row = start_row + (po_date - start_date).days
    ws.cell(row=row, column=4, value=wheat_po)   # D: Wheat PO
    ws.cell(row=row, column=7, value=canola_po)  # G: Canola PO
    print(f"Row {row}: {po_date.date()} -> Wheat={wheat_po}, Canola={canola_po}")
```

## Verification After Writing

Always verify the mapping was applied correctly:

```python
for po_date, (expected_wheat, _) in po_dates.items():
    row = start_row + (po_date - start_date).days
    actual = ws.cell(row=row, column=4).value
    assert actual == expected_wheat, f"Row {row}: expected {expected_wheat}, got {actual}"
```

## Common Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Off-by-one on start_row | PO dates shifted by N rows | Verify start_row matches first date cell |
| Timezone-aware vs naive dates | TypeError in subtraction | Use `datetime()` without tzinfo |
| Partial date (date object) | AttributeError | Convert: `datetime.combine(d, datetime.min.time())` |
