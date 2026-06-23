# Formula Evaluation with openpyxl

## The Problem

openpyxl writes formulas as strings in the XML. It does NOT have a formula calculation engine. When you read a file:

```python
from openpyxl import load_workbook
wb = load_workbook('file.xlsx')
ws = wb['Sheet']
print(ws['A1'].value)  # Returns '=SUM(B1:B10)' or None, never 42
```

## Options for Getting Calculated Values

### Option 1: data_only Mode (Limited)

```python
# Only works if file was saved by Excel with calculated values
wb = load_workbook('file.xlsx', data_only=True)
print(ws['A1'].value)  # May return cached value or None
```

**Limitation:** Only works if the file was previously opened and saved in Excel. Files created purely with openpyxl have no cached values.

### Option 2: xlwings (Requires Excel)

```python
import xlwings as xw
wb = xw.Book('file.xlsx')
print(wb.sheets['Sheet'].range('A1').value)  # Actual calculated value
wb.close()
```

**Requirements:** Microsoft Excel installed, Windows or macOS.

### Option 3: pycel / formulas (Pure Python)

```python
# Evaluate formulas using Python implementation
from formulas import ExcelModel
xl_model = ExcelModel().loads('file.xlsx').finish()
calc_value = xl_model.calculate()['Sheet!A1']
```

**Limitation:** Incomplete Excel function support, may fail on complex formulas.

### Option 4: Calculate in Python (Recommended for Tests)

Instead of relying on Excel calculation, compute expected values from source data:

```python
# Verify GL Balance formula: Period Totals - Ending Balance
period_totals = sum(billing_values)  # From source data
ending_balance = sum(recognition_values)  # From source data
expected_gl_balance = period_totals - ending_balance
assert gl_balance_source == expected_gl_balance
```

## Verifier-Aware Strategy

If the verifier checks calculated values:

1. Create file with openpyxl
2. Open in Excel (via xlwings or manual step)
3. Save to populate cached values
4. Re-read with `data_only=True`

Or: Implement calculation logic in Python to verify formulas are correct without Excel dependency.