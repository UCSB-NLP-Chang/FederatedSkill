---
name: excel-formula-construction
description: Construct Excel formulas programmatically using openpyxl for tasks requiring lookup-based data retrieval (VLOOKUP or INDEX/MATCH), calculated columns, statistics, and weighted aggregations. Use when populating formula cells in existing workbook templates based on a data source grid, especially for multi-year datasets with region/entity breakdowns. Critical triggers: always inspect Data sheet structure before writing formulas; verify formulas evaluate to correct values, not just exist; MATCH must reference header cells not hardcoded values.
---

# Excel Formula Construction

Build formulas in Excel workbooks using Python and openpyxl. Designed for structured data tasks with lookup tables, derived calculations, and statistical summaries.

## When to Use

- Populating formula cells in an existing `.xlsx` template
- Tasks with a "Data" source sheet and "Task" output sheet
- Multi-year columns requiring dynamic lookup
- Calculated columns based on looked-up values
- Statistical aggregations (MIN, MAX, MEDIAN, AVERAGE, PERCENTILE) across entities
- Weighted mean calculations using SUMPRODUCT

## Critical Pre-Flight: Inspect Data Sheet Structure

**Always inspect the Data sheet first.** Formula failures often stem from incorrect assumptions about column alignment and header positions.

```python
import openpyxl
wb = openpyxl.load_workbook('workbook.xlsx', data_only=False)
ws_data = wb['Data']

# CRITICAL: Check if year headers and data are in different rows
print("Year header candidates:")
for row in range(1, 25):
    vals = [ws_data.cell(row=row, column=c).value for c in range(1, 15)]
    if any(str(v).isdigit() and len(str(v)) == 4 for v in vals if v):
        print(f"  Row {row}: {vals}")

# Verify series codes in lookup column
print("\nSeries codes (sample):")
for row in range(21, 26):  # Adjust based on data start
    code = ws_data.cell(row=row, column=4).value  # Column D
    print(f"  Row {row}: {code}")
```

**Decision rule**: If year headers appear in row 4 but data starts in row 21, your MATCH for columns must target row 4, not the data row.

## Lookup Pattern Selection

### VLOOKUP + MATCH
Best when: lookup column is leftmost in data range, simple column indexing works.

```
=VLOOKUP(lookup_value, Data!$D$21:$L$38, MATCH(year_header, Data!$H$20:$L$20, 0)+OFFSET, FALSE)
```

See references/formula_patterns.md for offset calculation.

### INDEX + MATCH (Double MATCH)
Best when: data range is a grid, need row-by-series-code and column-by-year independently.

```
=INDEX(Data!$H$21:$L$38, MATCH($D12,Data!$D$21:$D$38,0), MATCH(H$10,Data!$H$4:$L$4,0))
```

**Critical**: Row MATCH uses series code column; Column MATCH uses year header row.

| Component | Purpose | Common Range |
|-----------|---------|--------------|
| array | Data grid | `Data!$H$21:$L$38` |
| row_num | Find series code | `MATCH($D12,Data!$D$21:$D$38,0)` |
| column_num | Find year | `MATCH(H$10,Data!$H$4:$L$4,0)` |

**Use absolute `$` for data ranges; mixed references (`H$10`, `$D12`) for lookups that fill across.**

## Core Workflow

### 1. Understand the Structure

```python
import openpyxl
wb = openpyxl.load_workbook('workbook.xlsx', data_only=False)
# Inspect:
# - Where year headers live (may differ from data rows)
# - Series code column and data start/end rows
# - Whether data grid is contiguous
```

### 2. Choose and Build Formula Pattern

See Lookup Pattern Selection above. Build formula strings with raw strings or f-strings.

**CRITICAL ANTI-PATTERN**: Hardcoding year values in MATCH
```python
# WRONG - 2020 is static, won't adjust when copied across columns
formula = f"=VLOOKUP($D12,Data!$D$21:$L$38,MATCH(2020,Data!$H$4:$L$4,0)+1,0)"

# RIGHT - H$10 references the year header cell, adjusts per column
formula = f"=VLOOKUP($D12,Data!$D$21:$L$38,MATCH(H$10,Data!$H$4:$L$4,0)+1,0)"
```

### 3. Write and Verify

```python
# Write formula
ws['H12'].value = "=INDEX(Data!$H$21:$L$38,MATCH($D12,Data!$D$21:$D$38,0),MATCH(H$10,Data!$H$4:$L$4,0))"

# CRITICAL: Verify formula exists and syntax is valid
assert ws['H12'].value is not None
assert ws['H12'].value.startswith('=')
assert 'Data!' in ws['H12'].value
```

### 4. Mandatory: Verify Formulas Evaluate to CORRECT Values

**Checking formula existence is NOT sufficient.** Tests check calculated values, not formula strings. Failed verifications often occur when formulas exist but return wrong values due to MATCH range errors.

```python
# Method 1: Cross-reference with expected data values (RECOMMENDED)
# Look up known value in Data sheet, verify formula produces it
wb_data = openpyxl.load_workbook('workbook.xlsx', data_only=True)
actual_value = wb_data['Task']['H12'].value
expected_value = wb_data['Data']['H21'].value  # ALP_LOAD_IN, 2019 = 302.5
assert actual_value == expected_value, f"Expected {expected_value}, got {actual_value}"

# Method 2: xlcalculator evaluation (if available)
from xlcalculator import ModelCompiler, Evaluator
compiler = ModelCompiler()
model = compiler.read_and_parse_archive('result.xlsx')
evaluator = Evaluator(model)

test_cell = 'Task!H35'
try:
    result = evaluator.evaluate(test_cell)
    print(f"{test_cell} = {result}")
    assert result is not None, "Formula evaluated to None"
    assert not isinstance(result, str) or not result.startswith('#'), f"Formula error: {result}"
except Exception as e:
    print(f"EVALUATION FAILED: {e}")
```

**CRITICAL VERIFICATION PATTERN**: Before saving, always:
1. Load with `data_only=True` to get calculated values
2. Spot-check 2-3 known data points against source Data sheet
3. Verify lookups match: series code + year should return exact Data sheet value

### 5. Statistical Functions

| Statistic | Function | Notes |
|-----------|----------|-------|
| Minimum | `MIN(range)` | |
| Maximum | `MAX(range)` | |
| Median | `MEDIAN(range)` | |
| Mean | `AVERAGE(range)` | |
| 25th percentile | `PERCENTILE.INC(range, 0.25)` | **NOT QUARTILE.INC** |
| 75th percentile | `PERCENTILE.INC(range, 0.75)` | **NOT QUARTILE.INC** |

**Anti-pattern**: `QUARTILE.INC(range, 1)` returns same value but test suites may specifically check for `PERCENTILE.INC` function name.

### 6. Calculated Columns and Weighted Mean

```python
# Calculated percentage
ws['H35'].value = "=(H12-H19)/H26*100"

# Weighted mean
ws['H50'].value = "=SUMPRODUCT(H35:H40,H26:H31)/SUM(H26:H31)"
```

## Critical Rules

| Rule | Why |
|------|-----|
| Inspect Data sheet before writing formulas | Year headers and data may be in different rows |
| **MATCH must reference cell, not hardcoded value** | `MATCH(H$10,...)` not `MATCH(2020,...)` - enables fill-across |
| Verify formulas evaluate to CORRECT values | Tests check values, not formula strings; MATCH errors produce wrong results silently |
| Spot-check known data points after writing | Catches MATCH range errors (header row vs data row) |
| Use PERCENTILE.INC, not QUARTILE.INC | Function name may be explicitly checked |
| Use `data_only=False` when loading | Otherwise formulas aren't readable/writable |
| Use absolute `$` for data ranges | Prevents reference drift when filling |
| Use mixed refs for lookup cells (`H$10`, `$D12`) | Allows filling across while anchoring appropriately |

## Common Mistakes

- **Hardcoding years in MATCH**: `MATCH(2020,...)` won't adjust per column; use `MATCH(H$10,...)`
- **Assuming year headers are in data rows**: Check row 4 vs row 21
- **Using QUARTILE.INC instead of PERCENTILE.INC**: Tests may specifically check function name
- **Only verifying formula existence**: Always test evaluation when possible
- **Wrong MATCH ranges**: Column MATCH must target header row, not data row
- **Forgetting `$` on data ranges**: Causes drift when filling formulas
- **Not spot-checking calculated values**: MATCH can succeed but return wrong row/col index

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `#N/A` in evaluated result | MATCH failed (wrong row/col, or missing data) | Verify series codes and year headers match exactly |
| `#REF!` in evaluated result | Invalid range reference | Check sheet names and absolute references |
| `None` from xlcalculator | Formula syntax error or circular reference | Check formula string manually |
| Wrong values despite formula present | Wrong MATCH range (e.g., targeting data row instead of header row) | Re-inspect Data sheet structure |
| Values don't change across columns | Hardcoded year in MATCH | Replace `MATCH(2020,...)` with `MATCH(H$10,...)` |
| Test fails on function name | Used QUARTILE instead of PERCENTILE | Replace with PERCENTILE.INC |
| Verifier fails with "wrong value" | Formula returns value from wrong row/column | Check MATCH ranges point to correct header/data rows |

## Verification Checklist

Before saving, confirm:
1. [ ] Data sheet inspected: year header row identified, data start row identified
2. [ ] MATCH references header cells (`H$10`), not hardcoded years
3. [ ] MATCH ranges correct: column MATCH uses header row, row MATCH uses series code column
4. [ ] Sample formula written and verified with `startswith('=')`
5. [ ] Sample formula EVALUATED and matches known data point
6. [ ] Spot-check: 2-3 cells cross-referenced against Data sheet values
7. [ ] Statistical functions use PERCENTILE.INC not QUARTILE.INC
8. [ ] All target cells populated, not just sampled

## References

- `references/formula_patterns.md` - Detailed VLOOKUP and INDEX/MATCH patterns, offset calculations, common data layout patterns
- `references/verification_patterns.md` - Deep dive on verification strategies, debugging formula evaluation failures
- `scripts/populate_vlookups.py` - Script template for batch formula population
- `scripts/verify_formulas.py` - Automated formula evaluation checker using xlcalculator or openpyxl data_only mode

## Fallback: Manual Verification

If automated evaluation unavailable:
1. Save workbook
2. Load with `data_only=True`
3. Print calculated values for spot-check cells
4. Manually compare against Data sheet source values
5. If mismatch: check MATCH range (header row vs data row is #1 culprit), then check for hardcoded values in MATCH
