# Formula Pattern Reference

## Pre-Flight Data Inspection

Always run this before writing formulas:

```python
import openpyxl
from openpyxl.utils import get_column_letter

wb = openpyxl.load_workbook('workbook.xlsx', data_only=False)
ws_data = wb['Data']

# Find year header row (commonly row 1, 4, 10, or 20)
for row in range(1, 25):
    vals = [ws_data.cell(row=row, column=c).value for c in range(1, 15)]
    year_vals = [v for v in vals if v and str(v).isdigit() and len(str(v)) == 4]
    if year_vals:
        print(f"Year headers at row {row}: {vals}")
        header_row = row
        break

# Find data start row (commonly row 21)
for row in range(header_row + 1, 50):
    val = ws_data.cell(row=row, column=4).value  # Column D
    if val and isinstance(val, str) and '_REN_GEN' in val:
        print(f"Data starts at row {row}")
        data_start_row = row
        break

# Verify series codes
print("\nSeries codes (first 5):")
for row in range(data_start_row, data_start_row + 5):
    code = ws_data.cell(row=row, column=4).value
    print(f"  Row {row}: {code}")
```

## INDEX + MATCH Pattern (Recommended for Grid Data)

When data is a grid with series codes in column D and years in header row:

```
=INDEX(data_grid, MATCH(series_code, series_code_column, 0), MATCH(year, year_header_row, 0))
```

**Template:**
```python
# Parameters
data_grid = "Data!$H$21:$L$38"      # The data values
series_col = "Data!$D$21:$D$38"    # Where series codes live
header_row = "Data!$H$4:$L$4"      # Where year headers live (may differ from data!)

# For cell in Task sheet, row 12, column H
# - $D12: series code for this row (absolute col, relative row)
# - H$10: year for this column (relative col, absolute row)
formula = f"=INDEX({data_grid},MATCH($D12,{series_col},0),MATCH(H$10,{header_row},0))"
```

**Reference Style Guide:**

| Component | Style | Example | Why |
|-----------|-------|---------|-----|
| Data ranges | Absolute `$` | `$H$21:$L$38` | Never drift |
| Lookup value (row) | Mixed `$D12` | `$D12` | Fix column D, allow row change |
| Lookup value (col) | Mixed `H$10` | `H$10` | Fix row 10, allow column change |

**CRITICAL**: Never hardcode year values:

```python
# WRONG - 2020 is static
formula = f"=INDEX({data_grid},MATCH($D12,{series_col},0),MATCH(2020,{header_row},0))"

# RIGHT - H$10 references the year header cell
formula = f"=INDEX({data_grid},MATCH($D12,{series_col},0),MATCH(H$10,{header_row},0))"
```

## VLOOKUP + MATCH Pattern

Use when lookup column is leftmost and simple column indexing works.

```
=VLOOKUP(lookup_value, table_array, MATCH(year_header, header_range, 0)+OFFSET, FALSE)
```

**OFFSET Calculation:**

| table_array starts | header_range starts | OFFSET | Calculation |
|-------------------|---------------------|--------|-------------|
| D (col 4) | H (col 8) | +4 | `8 - 4 = 4` |
| H (col 8) | H (col 8) | 0 | `8 - 8 = 0` |

```python
from openpyxl.utils import column_index_from_string

offset = column_index_from_string('H') - column_index_from_string('D')  # = 4

# CRITICAL: Use H$10 not hardcoded year
formula = f"=VLOOKUP($D12,Data!$D$21:$L$38,MATCH(H$10,Data!$H$4:$L$4,0)+{offset},FALSE)"
```

## Statistical Functions

| Function | Excel | Notes |
|----------|-------|-------|
| 25th percentile | `PERCENTILE.INC(range, 0.25)` | Preferred over QUARTILE |
| 75th percentile | `PERCENTILE.INC(range, 0.75)` | Preferred over QUARTILE |
| Quartile (alt) | `QUARTILE.INC(range, 1)` | Same result, different function |

**Important**: Some test suites verify the exact function name used. Prefer `PERCENTILE.INC` unless task explicitly specifies `QUARTILE`.

## Calculated Percentage

```
=(RenewableGen - GridConsumption) / Baseline * 100
```

## Weighted Mean

```
=SUMPRODUCT(values_range, weights_range) / SUM(weights_range)
```

## Verification Formula

Test your understanding:

```python
# Given:
# - Data sheet: series codes in D21:D38, year headers in H4:L4, data in H21:L38
# - Task sheet: series codes in D12:D17, year headers in H10:L10
# - Need: populate H12 with lookup for D12 series, H10 year

# Solution using INDEX+MATCH:
# =INDEX(Data!$H$21:$L$38,MATCH($D12,Data!$D$21:$D$38,0),MATCH(H$10,Data!$H$4:$L$4,0))

# Why this works:
# - INDEX grid is H21:L38 (the data values)
# - First MATCH finds which row in D21:D38 matches series code in $D12
# - Second MATCH finds which column in H4:L4 matches year in H$10
```

## Common Range Patterns

| Task Pattern | Data Structure | Formula Pattern |
|--------------|---------------|-----------------|
| Multi-year grid lookup | Series in col, years in row | INDEX + double MATCH |
| Simple column lookup | Single year, series in first col | VLOOKUP |
| Cross-sheet reference | Same structure, different sheet | Match pattern + sheet prefix |
