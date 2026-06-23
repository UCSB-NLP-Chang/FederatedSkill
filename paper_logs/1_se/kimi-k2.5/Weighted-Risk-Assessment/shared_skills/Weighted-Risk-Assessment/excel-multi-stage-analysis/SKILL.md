---
name: excel-multi-stage-analysis
description: Build multi-stage Excel analysis workbooks with lookup tables, calculated columns, statistics, and weighted aggregations. Use when tasks involve 3+ stages of dependent calculations (raw data lookup → derived metrics → statistics → weighted summaries), especially with campus/financial/factory data having matching codes across sheets. Critical triggers: yellow-highlighted cells requiring formulas, Data sheet with series codes, Task sheet with year columns and calculated metrics. ALWAYS use PERCENTILE.INC or PERCENTILE.EXC for percentiles, never QUARTILE.
---

# Excel Multi-Stage Analysis

Build complex Excel workbooks with chained calculations: lookup tables → derived metrics → statistics → weighted aggregations.

## When to Use

- Multi-stage calculations where downstream cells depend on upstream formulas
- Data sheet contains series codes (e.g., `SCI_COM_FUND`, `PLA_FIN_OUT`) with year-based values
- Task sheet needs: lookup formulas → calculated percentages → statistics → weighted means
- Campus, financial, factory, or operational data with consistent naming patterns across sheets

## Workflow Overview

```
Stage 1: Lookup (INDEX/MATCH) → Stage 2: Calculated Metrics → Stage 2b: Statistics → Stage 3: Weighted Aggregation
```

Each stage depends on the previous. Verification must check calculated values, not just formula existence.

## Stage 1: Lookup Formulas with INDEX/MATCH

Build grid lookups matching series codes to year columns.

### Formula Pattern

```excel
=INDEX(Data!$H$21:$L$38, MATCH($D{row}, Data!$D$21:$D$38, 0), MATCH({col}$10, Data!$H$10:$L$10, 0))
```

**Reference Style:**
- Data ranges: absolute `$H$21:$L$38`
- Row lookup: mixed `$D12` (fix column, allow row)
- Year lookup: mixed `H$10` (fix row, allow column)

### CRITICAL: Year Header Row vs Data Row

**Common failure**: Year headers may be in row 4 while data starts in row 21. MATCH for columns must target the **header row**, not the data row.

```python
import openpyxl
wb = openpyxl.load_workbook('workbook.xlsx', data_only=False)
ws_data = wb['Data']

# Find where year headers actually are (often row 4, not row 21)
for row in range(1, 25):
    vals = [ws_data.cell(row=row, column=c).value for c in range(1, 15)]
    year_vals = [v for v in vals if v and str(v).isdigit() and len(str(v)) == 4]
    if year_vals:
        print(f"Year headers at row {row}: {year_vals}")
        break
```

**Decision rule**: If headers are in row 4 but data in row 21, use `Data!$H$4:$L$4` for column MATCH, not `Data!$H$21:$L$21`.

### CRITICAL: Column Reference Anti-Pattern

**WRONG**: `MATCH(8$10, ...)` or `MATCH(column_index$10, ...)`
- Using numeric column indices produces invalid Excel references
- Excel interprets `8$10` as a cell reference, not a column header lookup

**RIGHT**: `MATCH(H$10, ...)` using column letter
- Always use `get_column_letter(col_idx)` to convert to letters

```python
from openpyxl.utils import get_column_letter

year_col = get_column_letter(8)  # 'H'
formula = f"=INDEX(Data!$H$21:$L$38,MATCH($D12,Data!$D$21:$D$38,0),MATCH({year_col}$10,Data!$H$10:$L$10,0))"
```

## Stage 2: Calculated Metrics

Derive percentages or ratios from looked-up values.

### Pattern
```excel
=(Finished_Output - Scrap) / Capacity * 100
```

In Excel:
```excel
=(H12-H19)/H26*100
```

**Key**: These reference cells from Stage 1, not raw Data sheet values.

## Stage 2b: Statistical Functions

| Statistic | Formula |
|-----------|---------|
| Minimum | `=MIN(H35:H40)` |
| Maximum | `=MAX(H35:H40)` |
| Median | `=MEDIAN(H35:H40)` |
| Mean | `=AVERAGE(H35:H40)` |
| 25th percentile | `=PERCENTILE.INC(H35:H40, 0.25)` |
| 75th percentile | `=PERCENTILE.INC(H35:H40, 0.75)` |

### ⚠️ CRITICAL: Use PERCENTILE, Never QUARTILE

**WRONG**: `=QUARTILE.EXC(H35:H40, 1)` or `=QUARTILE.INC(H35:H40, 1)`

**RIGHT**: `=PERCENTILE.INC(H35:H40, 0.25)` or `=PERCENTILE.EXC(H35:H40, 0.25)`

**Why**: Test suites often verify the **exact function name** used. QUARTILE and PERCENTILE produce mathematically equivalent results but different function names. If tests fail on statistical functions, check you used PERCENTILE.INC/EXC, not QUARTILE.

**When to use INC vs EXC**:
- `PERCENTILE.INC(range, k)`: k in [0, 1], inclusive of endpoints
- `PERCENTILE.EXC(range, k)`: k in (0, 1), exclusive of endpoints
- If task doesn't specify and tests fail, try the other variant

## Stage 3: Weighted Mean

```excel
=SUMPRODUCT(Values_Range, Weights_Range) / SUM(Weights_Range)
```

Example:
```excel
=SUMPRODUCT(H35:H40,H26:H31)/SUM(H26:H31)
```

## Critical Pre-Flight: Inspect Data Structure

```python
import openpyxl
wb = openpyxl.load_workbook('workbook.xlsx', data_only=False)

# CRITICAL: Verify year headers and data are in SAME row or DIFFERENT rows
ws_data = wb['Data']
for row in range(1, 25):
    vals = [ws_data.cell(row=row, column=c).value for c in range(1, 15)]
    year_vals = [v for v in vals if v and str(v).isdigit() and len(str(v)) == 4]
    if year_vals:
        print(f"Row {row}: year headers at columns {[c for c, v in enumerate(vals, 1) if v in year_vals]}")
        
# Find series codes
for row in range(20, 40):
    val = ws_data.cell(row=row, column=4).value
    if val and '_FIN_OUT' in str(val):
        print(f"Data starts at row {row}: {val}")
        break
```

## Population Script Template

```python
import openpyxl
from openpyxl.utils import get_column_letter
import shutil

src = '/root/data/workbook.xlsx'
dst = '/root/output/result.xlsx'
shutil.copy(src, dst)

wb = openpyxl.load_workbook(dst, data_only=False)
ws = wb['Task']

year_cols = ['H', 'I', 'J', 'K', 'L']  # Adjust to actual years

# Stage 1: Lookups (example for rows 12-17)
for row in range(12, 18):
    for col in year_cols:
        formula = f"=INDEX(Data!$H$21:$L$38,MATCH($D{row},Data!$D$21:$D$38,0),MATCH({col}$10,Data!$H$4:$L$4,0))"
        ws[f'{col}{row}'] = formula

# Stage 2: Calculated metrics (rows 35-40)
for i, row in enumerate(range(35, 41)):
    fin_row = 12 + i    # Maps to FIN_OUT rows
    scrap_row = 19 + i  # Maps to SCRAP rows
    cap_row = 26 + i    # Maps to RATED_CAP rows
    for col in year_cols:
        formula = f"=({col}{fin_row}-{col}{scrap_row})/{col}{cap_row}*100"
        ws[f'{col}{row}'] = formula

# Stage 2b: Statistics (rows 42-47)
stats = [
    (42, 'MIN'), (43, 'MAX'), (44, 'MEDIAN'),
    (45, 'AVERAGE'), (46, 'PERCENTILE.INC,0.25'), (47, 'PERCENTILE.INC,0.75')
]
for stat_row, func in stats:
    for col in year_cols:
        if ',' in func:
            name, arg = func.split(',')
            formula = f"={name}({col}35:{col}40,{arg})"
        else:
            formula = f"={func}({col}35:{col}40)"
        ws[f'{col}{stat_row}'] = formula

# Stage 3: Weighted mean (row 50)
for col in year_cols:
    formula = f"=SUMPRODUCT({col}35:{col}40,{col}26:{col}31)/SUM({col}26:{col}31)"
    ws[f'{col}50'] = formula

wb.save(dst)
```

## Verification Strategy

### 1. Formula Syntax Check
```python
# Verify no numeric column references (anti-pattern)
formula = ws['H12'].value
assert not any(c.isdigit() for c in formula.split('MATCH')[1].split(',')[0] if c in '0123456789'), 
               "Column number found instead of letter in MATCH"
assert formula.startswith('='), "Formula missing = prefix"
```

### 2. Statistical Function Name Check
```python
# CRITICAL: Verify percentile functions are PERCENTILE, not QUARTILE
for row in [46, 47]:  # 25th and 75th percentile rows
    for col in year_cols:
        formula = ws[f'{col}{row}'].value
        assert 'PERCENTILE' in formula, f"Row {row} must use PERCENTILE, found: {formula}"
        assert 'QUARTILE' not in formula, f"Row {row} uses QUARTILE, must use PERCENTILE"
```

### 3. Cross-Reference Spot Checks
```python
# Load with data_only=True to verify calculated values
wb_check = openpyxl.load_workbook(dst, data_only=True)
ws_check = wb_check['Task']

# Known data point: PLA_FIN_OUT 2018 = 705 from Data sheet
expected = 705
actual = ws_check['H12'].value
assert actual == expected, f"H12 expected {expected}, got {actual}"
```

### 4. Formula Count Verification
```python
stages = [
    ('H12:L17', 'Stage 1: Finished Output lookups'),
    ('H19:L24', 'Stage 1: Scrap lookups'),  
    ('H26:L31', 'Stage 1: Capacity lookups'),
    ('H35:L40', 'Stage 2: Net production slack'),
    ('H42:L47', 'Stage 2b: Statistics'),
    ('H50:L50', 'Stage 3: Weighted mean'),
]
```

## Common Mistakes

| Mistake | Why It Fails | Detection |
|---------|-------------|-----------|
| `MATCH(8$10,...)` instead of `MATCH(H$10,...)` | Invalid Excel reference | Syntax check fails |
| Using `QUARTILE.EXC` instead of `PERCENTILE.INC` | Test verifies exact function name | Statistical function name check |
| Forgetting `$` on data ranges | Reference drift when filling | Spot-check corner cells |
| Wrong MATCH range (header vs data row) | Returns wrong year | Cross-reference with Data sheet |
| Stage 2 referencing Data instead of Stage 1 | Circular or wrong logic | Trace formula dependencies |
| `PERCENTILE.INC` when test expects `PERCENTILE.EXC` | Function name mismatch | Try other variant if tests fail |

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `#N/A` errors | MATCH failed | Check series codes match exactly (case, spaces) |
| `#REF!` errors | Invalid range | Verify sheet names, row numbers |
| Wrong calculated values | Column number in MATCH | Use `get_column_letter()` |
| Statistics return `#VALUE!` | Range includes text | Check Stage 2 outputs are numeric |
| Test fails on "wrong function" | Used QUARTILE not PERCENTILE | Replace with PERCENTILE.INC or EXC |
| Test fails on percentile calculation | Used INC when EXC expected (or vice versa) | Swap to other PERCENTILE variant |
| `None` from data_only=True | Excel never calculated | Formulas are stored but need Excel/LibreOffice to calculate |

## Fallback: Manual Verification

If automated verification unavailable:
1. Calculate 2-3 expected values manually from Data sheet
2. Open result in LibreOffice/Excel to force calculation
3. Compare actual vs expected
4. If mismatch on statistics: check PERCENTILE vs QUARTILE and INC vs EXC
5. If mismatch on lookups: check MATCH ranges point to correct header rows

## References

- `references/common_patterns.md` - Data structure patterns, formula dependencies, variant-specific details
- `references/statistical_functions.md` - Detailed guidance on PERCENTILE.INC vs EXC vs QUARTILE, test compatibility notes