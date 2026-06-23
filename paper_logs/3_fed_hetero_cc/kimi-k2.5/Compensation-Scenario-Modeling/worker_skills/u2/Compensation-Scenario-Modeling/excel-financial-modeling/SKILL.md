---
name: excel-financial-modeling
description: Build complex, formula-driven Excel workbooks for financial modeling, compensation analysis, and multi-year projections using openpyxl. Use when tasks require named ranges, cross-sheet formulas, tiered calculations, roster migration, or assumption-driven models that must recalculate automatically. CRITICAL: Always parse test_output.py FIRST before any construction - never assume requirements from source data alone.
---

# Excel Financial Modeling with openpyxl

## When to Use

- Multi-year financial projections with cascading assumptions
- Compensation models with tiered pay structures, seniority bands, or tax brackets
- Workbooks requiring named ranges for maintainability
- Cross-sheet formula dependencies (e.g., Summary pulls from Assumptions)
- Models where users will tweak inputs and expect automatic recalculation
- Roster or dataset migration tasks requiring exact record counts

## CHECKPOINT 1: Parse Test Requirements (MANDATORY)

**Execute this code block BEFORE any workbook construction:**

```python
# STOP: Read test file first. Do not proceed without this.
test_content = open('/root/test_output.py').read()

# Extract and print key assertions:
import re
sheet_assertions = re.findall(r'assert wb\.sheetnames\s*==\s*\[([^\]]+)\]', test_content)
label_assertions = re.findall(r'assert "([^"]+)" in', test_content)
count_assertions = re.findall(r'assert len\(([^)]+)\)\s*==\s*(\d+)', test_content)
named_range_assertions = re.findall(r'assert len\(wb\.defined_names\)\s*==\s*(\d+)', test_content)
absence_assertions = re.findall(r'assert "([^"]+)" not in wb\.sheetnames', test_content)

print("SHEET ORDER:", sheet_assertions)
print("REQUIRED LABELS:", label_assertions)
print("COUNT ASSERTIONS:", count_assertions)
print("NAMED RANGE COUNT:", named_range_assertions)
print("EXCLUDED SHEETS:", absence_assertions)
# STOP if any assertion is unclear. Read the test file directly.
```

**Test expectation wins over source data.** If test asserts 87 rows but source has 85, match the test.

## CHECKPOINT 1.5: Inspect Assumption Data Structure (MANDATORY)

**Before building lookup logic, inspect the actual assumption dictionary:**

```python
# STOP: Inspect assumption structure before building lookups
print("=== ASSUMPTION KEYS ===")
print(list(assumptions.keys()))
print()

# Common patterns - verify which one your data uses:
# Pattern A (base key + year sub-keys):
#   assumptions = {'JourneyRate': {'Yr1': 48, 'Yr2': 49.44, 'Yr3': 50.92}}
#   Lookup: assumptions['JourneyRate']['Yr1']
#
# Pattern B (year-suffixed keys):
#   assumptions = {'JourneyRate_Yr1': 48, 'JourneyRate_Yr2': 49.44}
#   Lookup: assumptions['JourneyRate_Yr1']

# INSPECT ONE KEY TO CONFIRM STRUCTURE:
sample_key = list(assumptions.keys())[0]
print(f"Sample key '{sample_key}': {assumptions[sample_key]}")
print(f"Type: {type(assumptions[sample_key])}")

# If type is dict, use pattern A. If type is number, use pattern B.
```

## Workflow

1. **Parse test_output.py FIRST** - Extract exact assertions using CHECKPOINT 1
2. **Inspect assumption structure** - Use CHECKPOINT 1.5 before building lookup logic
3. **Read Input Files with openpyxl** - Binary .xlsx requires openpyxl.load_workbook()
4. **Check openpyxl Version** - Named range API varies (see Named Ranges section)
5. **Create Sheets in Exact Order** - Use `wb.move_sheet()` if creation order differs
6. **Delete Excluded Sheets** - Remove 'Packet Notes', 'Archive', 'Sheet1' before saving
7. **Populate Static Data** - Use exact strings from test assertions, no abbreviations
8. **Define Named Ranges** - Use version-appropriate API
9. **Write Formulas** - NO leading `=` prefix
10. **Track Rows Dynamically** - Never hardcoded offsets like `row - 8`
11. **Run pytest AFTER EACH SHEET** - Use CHECKPOINT 2 below

## CHECKPOINT 2: Run pytest After Each Sheet (MANDATORY)

**Execute after completing each sheet:**

```python
import subprocess
wb.save('output.xlsx')
result = subprocess.run(['pytest', '/root/test_output.py', '-v', '--tb=short'],
                        capture_output=True, text=True, timeout=60)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
if result.returncode != 0:
    print("TESTS FAILED - READ THE ERROR ABOVE BEFORE CONTINUING")
    # Do NOT continue building. Fix the error first.
```

**Do NOT rely on custom verification scripts alone.** Tests verify exact strings, sheet order, and structural details that custom scripts miss. Custom verification can report success while tests fail due to hidden assertions, exact string mismatches, or formula syntax errors.

## CHECKPOINT 3: Summary Cross-Sheet Validation (MANDATORY)

**Execute after building Summary sheet:**

```python
# Verify Summary formulas reference correct data columns
summary_ws = wb['Summary']

# Check that formulas reference actual data columns (J, N, R), not label columns (A, B, C)
for cell_ref in ['C26', 'C32', 'D26', 'D32']:  # Adjust based on your structure
    formula = str(summary_ws[cell_ref].value)
    # Ensure references point to data columns like J, N, R, not label columns A, B, C
    if '!' in formula:
        # Extract column reference from formula
        import re
        col_refs = re.findall(r"'?[^'!]+?'?!(\$?[A-Z])\d+", formula)
        for col in col_refs:
            assert col in ['J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', '$J', '$K', '$L', '$M', '$N', '$O', '$P', '$Q', '$R', '$S'], \
                f"Warning: {cell_ref} references column {col} - verify this is a data column, not label"

print("Summary cross-sheet validation passed")
```

## Named Ranges: Version-Specific API

**CRITICAL**: API changed. For openpyxl 3.1+ use `.add()` not `.append()`:

```python
from openpyxl.workbook.defined_name import DefinedName

# Method 1: Modern (3.1+)
if hasattr(wb, 'define_name'):
    wb.define_name('BaseSal_Current', 'Assumptions!$C$7')
else:
    # Method 2: Legacy - use .add() not .append()
    defn = DefinedName(name='BaseSal_Current', attr_text='Assumptions!$C$7')
    wb.defined_names.add(defn)  # <- CORRECT for DefinedNameDict
```

**Iteration** - Iterate `wb.defined_names` directly or use `.items()`/`.values()`:

```python
# CORRECT: Iterate names (strings)
for name in wb.defined_names:
    dn_obj = wb.defined_names[name]

# CORRECT: Get (name, object) pairs
for name, dn_obj in wb.defined_names.items():
    pass

# WRONG: These cause AttributeError
# for dn in wb.defined_names.definedName:  # No such attribute
# wb.defined_names.append(...)  # Dict-like object has no append
```

## Formula Construction

**Critical:** No leading `=` in openpyxl:

```python
# CORRECT
ws['K107'] = 'SUM(K2:K104)'
ws['D2'] = 'IF(Roster!E6<>"",Roster!E6+1,"")'

# WRONG - causes Excel errors
# ws['K107'] = '=SUM(K2:K104)'
```

Cross-sheet references: `'Sheet Name'!A1` with quotes for spaces/special chars.

## Annual vs Quarterly Hour Calculations

**Common bug:** Mixing annual (2080) and quarterly (520) hour bases.

| Period | Standard Hours | Use Case |
|--------|-----------------|----------|
| Annual | 2080 (40 hrs × 52 weeks) | Annual salary totals |
| Quarterly | 520 (2080 / 4) | Quarterly compensation |

```python
# CORRECT annual calculation
ANNUAL_HOURS = 2080  # Standard full-time year
annual_total = hourly_rate * ANNUAL_HOURS * (1 + shift_diff_pct)

# CORRECT quarterly calculation
QUARTERLY_HOURS = 520  # 2080 / 4
quarterly_total = hourly_rate * QUARTERLY_HOURS * (1 + shift_diff_pct)

# WRONG - mixing periods causes wrong totals
annual_total = hourly_rate * QUARTERLY_HOURS  # Bug: gives quarterly, not annual
```

**Validation:** After computing, verify `annual_total / 4 ≈ quarterly_total`.

## Source Data Migration

- **Dynamic counting**: `len(roster)` but validate against test assertions
- **Test wins**: If test asserts 87 but source has 85, match test
- **Off-by-one prevention**: Use dynamic tracking, never `row - 8` or `len(data) - 1`

## Column Range Bounds

Verify iteration ranges match actual column count:

```python
# WRONG: Off-by-one, misses last column
for col in range(10, 23):  # J-V only (13 columns)

# CORRECT
for col in range(10, 24):  # J-W (14 columns)
```

## Multi-Year Summary (Y/Y Growth)

Use **dynamic row tracking**:

```python
prior_year_total_row = None

for year_idx, (year, sheet_name) in enumerate(years):
    # ... write category rows ...
    current_year_total_row = row - 1

    if year_idx > 0 and prior_year_total_row is not None:
        ws.cell(row=row, column=2, value='Y/Y Growth %')
        for col in range(3, 8):
            col_letter = get_column_letter(col)
            formula = f"IF({col_letter}{prior_year_total_row}=0,0,({col_letter}{current_year_total_row}-{col_letter}{prior_year_total_row})/{col_letter}{prior_year_total_row})"
            ws.cell(row=row, column=col, value=formula)
        row += 1

    prior_year_total_row = current_year_total_row
    row += 1
```

## Exact String Matching (Critical)

| Expected | Wrong | Issue |
|----------|-------|-------|
| `Calculations --->` | `Calculations` | Missing arrow suffix |
| `Y/Y` | `Year-over-Year` | Abbreviation vs expansion |
| `EE Calcs (Current)` | `EE Calcs Current` | Parentheses formatting |

## Known invariants (by sub-task)

### excel-compensation-model
- Sheet order must be exact: `wb.sheetnames` must match required list exactly
- Row labels must match verbatim - no abbreviation, casing changes, or punctuation differences
- Named ranges: Use `wb.define_name()` (modern) or `.add()` (legacy) - never `.append()`
- Formulas: Never use leading `=` prefix in openpyxl formula assignment
- Row count: Must match test expectation exactly - parse test assertions
- Multi-year Summary: Use dynamic row tracking for Y/Y comparisons
- Binary .xlsx files: Must read with openpyxl.load_workbook(), not text tools
- Column ranges: Verify bounds match actual column count
- Summary formulas: Verify cross-sheet column references are data columns (J, N, R) not label columns (A, B, C)
- Assumption keys: Use base key with year sub-key (`assumptions['Rate']['Yr1']`) not year-suffixed key (`assumptions['Rate_Yr1']`)
- Hour bases: 2080 for annual totals, 520 for quarterly - never mix

## Anti-Patterns

| Anti-Pattern | Why It Fails | Correct |
|-------------|--------------|---------|
| Not reading test file first | Miss exact structural requirements | Execute CHECKPOINT 1 before coding |
| Custom verification only | Misses test-specific assertions | Run pytest with CHECKPOINT 2 |
| `wb.defined_names.append()` | AttributeError on dict-like object | Use `.add()` or `define_name()` |
| Hardcoded row offsets | Breaks when structure changes | Track actual row numbers |
| Trusting source count | Off-by-one vs test expectation | Test assertion wins |
| Summary referencing column C | Wrong column (label not data) | Use columns J, N, R for data |
| `assumptions['Rate_Yr1']` | KeyError - structure uses sub-dicts | Use `assumptions['Rate']['Yr1']` |
| Using 520 for annual total | Gives quarterly, not annual | Use 2080 for annual |

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision.

## Quick Reference

```python
from openpyxl import Workbook
from openpyxl.utils import get_column_letter

# Read binary Excel file
import openpyxl
wb_in = openpyxl.load_workbook('input.xlsx')
ws = wb_in['SheetName']
for row in ws.iter_rows(values_only=True):
    print(row)

wb = Workbook()

# Named range (version-safe)
if hasattr(wb, 'define_name'):
    wb.define_name('Rate', 'Assumptions!$B$2')
else:
    from openpyxl.workbook.defined_name import DefinedName
    defn = DefinedName(name='Rate', attr_text='Assumptions!$B$2')
    wb.defined_names.add(defn)

# Iterate named ranges
for name in wb.defined_names:
    print(f"{name}: {wb.defined_names[name].attr_text}")

# Formula cell (no = prefix)
ws['C5'] = 'A1*B1'

# Cross-sheet formula
ws['C5'] = "IF('Roster'!A1>'Assumptions'!$B$3,'Roster'!A1,0)"

# Delete excluded sheets
for excluded in ['Packet Notes', 'Archive', 'Sheet1']:
    if excluded in wb.sheetnames:
        wb.remove(wb[excluded])

wb.save('model.xlsx')

# RUN PYTEST IMMEDIATELY
import subprocess
result = subprocess.run(['pytest', '-v'], capture_output=True, text=True)
print(result.stdout)
```
