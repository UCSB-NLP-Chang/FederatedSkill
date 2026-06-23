# Multi-Stage Analysis Patterns

## Campus Budget Pattern (from trace)

### Data Sheet Structure
```
Row 10: Year headers (2019, 2020, 2021, 2022, 2023) in columns H-L
Row 21-38: Data rows with series codes in column D
```

### Task Sheet Structure
```
Rows 12-17: Series codes (_COM_FUND suffix)
Rows 19-24: Series codes (_OPEX suffix)  
Rows 26-31: Series codes (_BGT_BASE suffix)
Rows 35-40: Calculated net budget buffer
Rows 42-47: Statistics on buffer values
Row 50: Weighted mean
```

### Formula Dependencies
```
H35 (buffer) depends on H12 (funding), H19 (opex), H26 (base)
H42 (stats) depends on H35:H40 (buffer range)
H50 (weighted) depends on H35:H40 and H26:H31
```

## Reference Style Guide

| Component | Style | Example |
|-----------|-------|---------|
| Data grid | Absolute | `Data!$H$21:$L$38` |
| Series code column | Absolute | `Data!$D$21:$D$38` |
| Year header row | Absolute | `Data!$H$10:$L$10` |
| Row lookup value | Mixed | `$D12` (fix col D) |
| Year lookup value | Mixed | `H$10` (fix row 10) |

## Year Column Iteration

```python
from openpyxl.utils import get_column_letter

start_col = 8  # H
col_count = 5  # H through L

for col_idx in range(start_col, start_col + col_count):
    col_letter = get_column_letter(col_idx)
    # Use col_letter in formulas
```

## Statistical Function Equivalents

| Excel Function | LibreOffice | Notes |
|---------------|-------------|-------|
| `PERCENTILE.INC` | `PERCENTILE.INC` | Use for 25th/75th |
| `QUARTILE.INC(range,1)` | `QUARTILE.INC` | Same result, different name |
| `MEDIAN` | `MEDIAN` | Identical |

## Weighted Mean Variants

### Simple (values and weights in same rows)
```excel
=SUMPRODUCT(H35:H40,H26:H31)/SUM(H26:H31)
```

### With offset mapping
When value row N maps to weight row N-9:
Calculate explicitly per cell, not as range.

## Verification by Hand

For `H35 = (H12-H19)/H26*100`:
1. Look up `Data!H21` for `SCI_COM_FUND` 2019 → 155.4
2. Look up `Data!H22` for `SCI_OPEX` 2019 → 159.7
3. Look up `Data!H23` for `SCI_BGT_BASE` 2019 → 210
4. Calculate: (155.4 - 159.7) / 210 * 100 = -2.0476...
5. Expected: approximately -2.05