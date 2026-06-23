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