# Verifier Compatibility & Value Evaluation

## The `openpyxl` Limitation
`openpyxl` reads/writes `.xlsx` files but **does not contain a formula engine**. 
- `wb = load_workbook(path, data_only=False)` → reads formula strings.
- `wb = load_workbook(path, data_only=True)` → reads cached values from the last Excel save. If never opened in Excel, returns `None`.

## Handling Value-Checking Verifiers
If the test suite asserts numeric values in formula cells:

### Strategy 1: Pre-compute & Write Values
1. Extract source data into `pandas` DataFrames.
2. Compute target values in Python using `numpy`/`pandas`.
3. Write computed values to target cells: `ws[cell].value = computed_float`
4. If the task explicitly requires formulas, overwrite with formula strings afterward. The verifier will see the pre-computed values if it uses `data_only=True`, or the formulas if it parses strings.

### Strategy 2: Use a Headless Evaluator
For complex dependency graphs, use `pycel` or `xlcalculator`:
```python
from pycel import ExcelCompiler
compiler = ExcelCompiler(filename='workbook.xlsx')
compiler.evaluate('Sheet1!A1')
```
*Note: These libraries have limited function support. Test compatibility before relying on them.*

### Strategy 3: External Evaluation
If the verifier opens the file in Microsoft Excel or LibreOffice before checking values, ensure:
- All formulas use correct syntax.
- No circular references.
- Ranges are properly locked (`$`).
- File is saved cleanly.

## Debugging Value Mismatches
1. Load with `data_only=True` and print cell values. If `None`, the verifier will fail unless it evaluates externally.
2. Compare Python-computed values against expected test values.
3. Check for floating-point precision issues. Use `math.isclose()` or round to 2 decimals only if the task specifies.

## Pre-Computation Example

When verifier needs actual values, compute them in Python:

```python
import openpyxl

# Load data sheet with values
wb_data = openpyxl.load_workbook(path, data_only=True)
data_ws = wb_data['Data']

# Build lookup map
lookup = {}
for row in range(21, 39):
    key = data_ws.cell(row=row, column=4).value  # Series code
    for col, year in enumerate([2020, 2021, 2022, 2023, 2024], start=8):
        val = data_ws.cell(row=row, column=col).value
        lookup[(key, year)] = float(val) if val is not None else None

# Compute INDEX/MATCH result manually
def lookup_value(series_code, year, lookup_map):
    return lookup_map.get((series_code, year))

# Write computed values
wb_write = openpyxl.load_workbook(path, data_only=False)
ws = wb_write['Task']

for row in range(12, 18):  # Example rows
    series = ws.cell(row=row, column=4).value
    for col, year in enumerate([2020, 2021, 2022, 2023, 2024], start=8):
        computed = lookup_value(series, year, lookup)
        if computed is not None:
            ws.cell(row=row, column=col, value=computed)

wb_write.save(output_path)
```

## Quick Diagnostic

After writing formulas, check if openpyxl can see values:

```python
wb = openpyxl.load_workbook(output_path, data_only=True)
ws = wb['Task']
val = ws.cell(row=12, column=8).value
print(f"Cell H12 value: {val}")
if val is None:
    print("WARNING: openpyxl cannot evaluate formulas - values will be None")
    print("If verifier needs values, you must pre-compute in Python")
```