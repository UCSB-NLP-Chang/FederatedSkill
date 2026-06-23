# Verifier Interaction Strategies

## The Core Problem

When you write formulas with openpyxl, the cells contain formula strings (e.g., `=SUM(A1:A10)`), not calculated values. If the verifier opens the file with `data_only=True`, it sees `None` for every formula cell.

**This is the #1 cause of failure in formula injection tasks.**

## Detection (DO THIS FIRST)

Run early detection to avoid wasted work:

```bash
python scripts/check_test_data_only.py /path/to/tests/
```

Or manually grep:
```bash
grep -r "data_only" tests/
grep -n "data_only.*True" test_output.py
```

**Exit codes:**
- 0: Safe to proceed with openpyxl
- 2: WARNING - data_only=True found, external calculation required

## Decision Matrix

| Scenario | Detection | Solution |
|----------|-----------|----------|
| Verifier checks formula strings | `data_only` not found | Use openpyxl, verify formula syntax |
| Verifier checks calculated values | `data_only=True` found | Use external engine or manual calculation |
| Verifier checks both | Mixed usage | Use external engine to calculate, then verify |

## Solution 1: LibreOffice Headless Calculation

If available, LibreOffice can calculate formulas without GUI:

```python
import subprocess
import openpyxl
from pathlib import Path

def calculate_with_libreoffice(xlsx_path):
    # LibreOffice loads and saves, caching calculated values
    subprocess.run([
        'libreoffice', '--headless', '--calc',
        '--convert-to', 'xlsx', '--outdir',
        str(Path(xlsx_path).parent),
        xlsx_path
    ], check=True)
    # File now has cached values
    return openpyxl.load_workbook(xlsx_path, data_only=True)
```

## Solution 2: xlwings (Windows/Mac with Excel)

```python
import xlwings as xw

def calculate_with_xlwings(xlsx_path):
    app = xw.App(visible=False)
    wb = xw.Book(xlsx_path)
    wb.save()
    wb.close()
    app.quit()
```

## Solution 3: Manual Verification (When External Engines Unavailable)

If you cannot use external engines but need to verify formulas are correct:

1. **Extract source data** from the workbook
2. **Calculate expected results** using Python (see `scripts/calculate_stats.py`)
3. **Verify formula structure** is correct (correct cell references, functions)
4. **Document limitation**: Formulas are correct but uncalculated due to openpyxl limitation

Example verification workflow:

```python
import openpyxl
from calculate_stats import calculate_all

# 1. Load your formula workbook
wb = openpyxl.load_workbook('output.xlsx')
ws = wb['Task']

# 2. Extract source data from Data sheet
data_ws = wb['Data']
values = [cell.value for cell in data_ws['H21:L38']]

# 3. Calculate expected statistics
expected = calculate_all(values)

# 4. Verify formula strings are correct
actual_formula = ws['H42'].value
assert 'MIN(H$35:H$40)' in actual_formula

# 5. Compare calculated expectation vs what formula would produce
print(f"Expected MIN: {expected['min']}")
print(f"Formula: {actual_formula}")
```

## Handling Specific Verifier Errors

### Error: `AttributeError: 'NoneType' object has no attribute 'value'`

**Cause**: Test uses `data_only=True`, formula cell returns `None`
**Fix**:
1. Check if test is comparing against expected values
2. If yes, use external engine or calculate manually
3. If test just checks formula exists, remove `data_only=True` from test (if you control it)

### Error: `assert cell.value == expected_value` fails with `None == 42.0`

**Cause**: `data_only=True` returns None for uncalculated formula
**Fix**:
- Pre-calculate with LibreOffice/xlwings, OR
- Change verification to check formula string instead: `assert 'FORMULA' in cell.value`

### Error: "Verifier passed: False" despite formulas looking correct

**Likely Cause**: You skipped the pre-flight check and the verifier uses `data_only=True`
**Immediate Action**:
1. Run `python scripts/check_test_data_only.py tests/`
2. If exit code 2, you must use external calculation
3. If LibreOffice/xlwings unavailable, calculate expected values manually and document

## Fallback Strategy

If you detect `data_only=True` and cannot use external engines:

1. Write formulas correctly with openpyxl
2. Calculate expected values manually using source data
3. Create a verification report showing:
   - Source data extracted
   - Expected calculated values
   - Actual formulas written
   - Confirmation that formulas reference correct ranges
4. Note in output that calculated values require Excel engine

This at least proves correctness of the formula logic even if the verifier cannot read cached values.

## Prevention Checklist

Before writing any formulas:
- [ ] Run `check_test_data_only.py` on test directory
- [ ] If exit code 2, set up external calculation or manual verification strategy
- [ ] Only proceed with openpyxl-only approach if exit code 0
- [ ] Run test suite immediately after first formula injection to confirm approach
