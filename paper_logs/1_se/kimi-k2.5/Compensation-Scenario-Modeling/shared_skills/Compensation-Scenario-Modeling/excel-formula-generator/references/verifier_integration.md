# Integrating with Test Verifiers

## The Critical Distinction

**openpyxl stores formulas as text strings.** It does NOT evaluate them. A workbook can have:
- Perfectly structured formulas that reference the right cells
- Named ranges that resolve correctly
- Valid Excel syntax

Yet still fail verification because the formulas calculate the wrong values.

## Always Run the Real Verifier

### When a test file exists:
```bash
# Find test files
ls test*.py *_test.py

# Run with verbose output
python3 -m pytest test_output.py -v --tb=short

# Run specific test
python3 -m pytest test_output.py::test_workbook -v
```

### When no test file exists:
Use `scripts/quick_verifier.py` for structural checks, then:
1. Open the file in Excel/LibreOffice Calc
2. Check that formulas evaluate (not just display)
3. Compare calculated values against expected

## Common Verifier Failure Patterns

### 1. Formula Structure vs Formula Evaluation
```python
# openpyxl shows this is "correct"
cell.value = "=A1/A2"

# But if A2=0, Excel shows #DIV/0!
# openpyxl won't catch this - only the verifier will
```

### 2. Floating Point Precision
```python
# Python calculates: 0.1 + 0.2 = 0.30000000000000004
# Excel may show: 0.3 or 0.300000000000000
# Verifiers often check exact string or decimal match
```

### 3. Implicit Intersection vs Array Formulas
Modern Excel handles arrays differently than older versions. A formula that works in Excel 365 may fail in older verifiers.

### 4. Named Range Resolution Timing
```python
# This order matters in openpyxl
wb.defined_names.add(DefinedName('RATE', attr_text='0.05'))
ws['A1'].value = "=RATE*100"  # Works

# This fails silently in Excel (but openpyxl won't warn)
ws['A1'].value = "=RATE*100"
wb.defined_names.add(DefinedName('RATE', attr_text='0.05'))  # Added after!
```

## Debugging Verifier Failures

### Step 1: Get exact failure message
```bash
python3 -m pytest test_output.py -v --tb=long
```

### Step 2: Inspect the test source
```python
# Read the test file to understand exact assertions
def test_something():
    wb = openpyxl.load_workbook('output.xlsx', data_only=True)
    # data_only=True returns CALCULATED values (if available)
    # data_only=False returns formula strings
```

### Step 3: Compare formula vs value
```python
wb_formula = openpyxl.load_workbook('output.xlsx', data_only=False)
wb_values = openpyxl.load_workbook('output.xlsx', data_only=True)

print("Formula:", wb_formula['Sheet1']['A1'].value)
print("Value:", wb_values['Sheet1']['A1'].value)  # None if never opened in Excel
```

### Step 4: Check for evaluation gaps
If `data_only=True` returns `None`, the workbook was never calculated by Excel. The verifier may be:
- Opening the file in Excel programmatically
- Using a different calculation engine
- Expecting cached values from a template

## Pre-Submission Checklist

Before claiming task complete:

1. **Locate test file**: `find . -name "*test*.py" -o -name "test_*"`
2. **Run tests**: `python3 -m pytest -v` or `python3 test_file.py`
3. **If tests import your output**: ensure file path matches test expectations
4. **If tests use data_only=True**: you may need to pre-calculate values in Python
5. **Check for hardcoded expectations**: row numbers, column letters, cell references

## When Verifier Is Unavailable

If you cannot run the verifier:

1. Generate known-good values in Python
2. Write formulas that match those known-good calculations
3. Structure formulas for easy manual verification
4. Document any assumptions in comments

Example - calculating tiered tax:
```python
# Python reference calculation (the "truth")
def calc_tax(income):
    if income <= 10000:
        return income * 0.10
    return 1000 + (income - 10000) * 0.20

# Matching Excel formula
formula = f"=IF({income_cell}<=10000,{income_cell}*0.1,1000+({income_cell}-10000)*0.2)"

# Verify: test edge cases in Python, match in Excel
```
