# Excel Data Layouts for Capacity Planning

Common input layouts and how to detect/extract data.

## Layout Detection Strategy

1. **First**: Load with `openpyxl` and scan for week numbers (values 1-53)
2. **If weeks in rows** (standard): Column A = Week, Column B = Demand
3. **If weeks in columns** (transposed): Row labels in Column A, week data in columns 1-N

## Standard Layout (weeks in rows)

```
| Week | Demand |
|    4 |    100 |
|    5 |     80 |
```

**Extract**:
```python
rows = list(ws.iter_rows(min_row=2, values_only=True))
weeks = [r[0] for r in rows]
demands = [r[1] for r in rows]
```

## Transposed Layout (weeks in columns)

```
| Label          |  4  |  5  |  6  | ...
| MIG Demand     | 100 |  80 | 120 | ...
```

**Extract**:
```python
# Find header row with week numbers
for r_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=10), 1):
    for c_idx, cell in enumerate(row, 1):
        if isinstance(cell.value, (int, float)) and 1 <= cell.value <= 53:
            header_row = r_idx
            week_col_start = c_idx
            break

# Find demand row by label
for r_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=20), 1):
    if row[0].value and "demand" in str(row[0].value).lower():
        demand_row = r_idx
        break
```

## Common Gotchas

- **Merged cells**: Use `data_only=True` and check for `None`
- **String week numbers**: Cast via `float()` then `int()` for "4.0" → 4
- **Total column**: Often contains "Total" in last column — exclude it