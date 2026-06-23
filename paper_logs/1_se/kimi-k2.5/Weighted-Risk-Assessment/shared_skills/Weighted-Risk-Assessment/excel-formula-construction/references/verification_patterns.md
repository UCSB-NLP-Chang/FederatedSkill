# Formula Verification Patterns

## Why Verification Fails Despite Correct-Looking Formulas

The most common silent failure: MATCH returns a valid index but for the **wrong row/column** because the range points to data rows instead of header rows (or vice versa).

### Example Failure Mode

```
Data sheet structure:
  Row 4:  [empty][empty][empty][2020][2021][2022]  <- year headers
  Row 20: [empty][empty][empty][2020][2021][2022]  <- duplicate labels in data
  Row 21: [code1][...][...][10][20][30]            <- actual data

Wrong: MATCH(H$10, Data!$H$21:$L$21, 0)  # targets data row with duplicate labels
Right: MATCH(H$10, Data!$H$4:$L$4, 0)    # targets actual header row
```

The wrong formula still evaluates to a number, but returns values from the wrong year.

## Recommended Verification Strategy

### Step 1: Identify Ground Truth

Before writing any formulas, identify 2-3 "known good" lookups:

```python
# Example: AUT_BGT_PRES for 2020 should equal 418.2
known_checks = [
    ('Task!H12', 'Data!H21'),   # AUT_BGT_PRES, 2020
    ('Task!I14', 'Data!I25'),   # SRC_BGT_PRES, 2021
    ('Task!L31', 'Data!L38'),   # NTF_REQ_CAP, 2024
]
```

### Step 2: Spot-Check After Writing

```python
import openpyxl

# Load to see calculated values
wb = openpyxl.load_workbook('result.xlsx', data_only=True)

for task_ref, data_ref in known_checks:
    task_sheet, task_coord = task_ref.split('!')
    data_sheet, data_coord = data_ref.split('!')
    
    actual = wb[task_sheet][task_coord].value
    expected = wb[data_sheet][data_coord].value
    
    if actual != expected:
        print(f"MISMATCH: {task_ref} = {actual}, expected {expected} from {data_ref}")
        # Indicates MATCH range error - check header row vs data row
```

### Step 3: Use xlcalculator for Complex Validation

```python
from xlcalculator import ModelCompiler, Evaluator

compiler = ModelCompiler()
model = compiler.read_and_parse_archive('result.xlsx')
evaluator = Evaluator(model)

# Verify no #N/A or #REF! errors
for row in range(12, 18):
    for col in ['H', 'I', 'J', 'K', 'L']:
        cell = f'Task!{col}{row}'
        try:
            result = evaluator.evaluate(cell)
            if isinstance(result, str) and result.startswith('#'):
                print(f"Formula error in {cell}: {result}")
        except Exception as e:
            print(f"Evaluation failed for {cell}: {e}")
```

## Common Verification Patterns by Task Type

### Multi-Year Grid Lookup

| Check Type | Example | Purpose |
|------------|---------|---------|
| Corner cell | Task!H12 = Data!H21 | First series, first year |
| Opposite corner | Task!L17 = Data!L26 | Last series, last year |
| Middle | Task!J14 = Data!J23 | Interior sanity check |

### Calculated Columns

Verify the calculation logic separately from lookup:

```python
# For formula: =(H12-H19)/H26*100
# Verify: (preserved - consumed) / capacity * 100

preserved = wb_data['Data']['H21'].value  # AUT_BGT_PRES
consumed = wb_data['Data']['H22'].value   # AUT_BGT_USE
capacity = wb_data['Data']['H23'].value   # AUT_REQ_CAP

expected = (preserved - consumed) / capacity * 100
actual = wb_task['Task']['H35'].value

assert abs(actual - expected) < 0.01, f"Expected {expected}, got {actual}"
```

### Statistical Functions

```python
# Verify MIN/MAX/MEDIAN against known data
values = [wb_data['Data'][f'H{row}'].value for row in range(35, 41)]
expected_min = min(values)
actual_min = wb_task['Task']['H42'].value

assert actual_min == expected_min
```

## Debugging Formula Evaluation Failures

### Symptom: `None` from data_only=True load

Cause: Excel never calculated the formula (file saved without calculation).

Fix: Use xlcalculator, or open in Excel and re-save.

### Symptom: `#N/A` in results

Cause: MATCH failed - check:
1. Series codes match exactly (case-sensitive, no extra spaces)
2. Year values match exactly (int vs string)
3. MATCH ranges point to correct rows/columns

### Symptom: `#REF!` in results

Cause: Invalid range reference - check:
1. Sheet names exist and match exactly
2. Column letters are valid
3. Row numbers are within bounds

### Symptom: Wrong numeric values (no error)

Cause: MATCH targeting wrong row/column - this is the **most insidious bug**.

Check:
1. Column MATCH uses header row (with year labels), not data row
2. Row MATCH uses series code column in data rows, not header
3. No off-by-one in range boundaries

## Automated Verification Script

See `scripts/verify_formulas.py` for command-line verification.

Example usage:
```bash
python3 scripts/verify_formulas.py result.xlsx \
  --checks "Task!H12=Data!H21" \
  --checks "Task!L17=Data!L26" \
  --checks "Task!H35=manual:2.42" \
  --method openpyxl
```
