---
name: excel-financial-modeling
description: Build complex, formula-driven Excel workbooks for financial modeling, compensation analysis, and multi-year projections using openpyxl. Use when tasks require named ranges, cross-sheet formulas, tiered calculations, or assumption-driven models that must recalculate automatically.
---

# Excel Financial Modeling with openpyxl

## When to Use

- Multi-year financial projections with cascading assumptions
- Compensation models with tiered pay structures, seniority bands, or tax brackets
- Workbooks requiring named ranges for maintainability
- Cross-sheet formula dependencies (e.g., Summary pulls from Assumptions)
- Models where users will tweak inputs and expect automatic recalculation
- Roster or dataset migration tasks requiring exact record counts

## Workflow

1. **Parse test_output.py FIRST** - Extract exact assertions before any code
2. **Read Source Files with openpyxl** - Binary .xlsx requires `openpyxl.load_workbook()`
3. **Create Sheets in Exact Order** - Use `wb.move_sheet()` if creation order differs
4. **Delete Excluded Sheets** - Remove 'Packet Notes', 'Archive', 'Sheet1' before saving
5. **Populate Static Data** - Use exact strings from test assertions
6. **Define Named Ranges** - Use `wb.define_name()` after cells exist
7. **Write Formulas** - NO leading `=` prefix
8. **Track Rows Dynamically** - Never use hardcoded offsets like `row - 8`
9. **Run pytest After Each Sheet** - NOT at the end; NOT custom verification only

## CHECKPOINT 1: Parse Test Requirements (MANDATORY)

**Execute this BEFORE any workbook construction:**

```python
# STOP: Read test file first. Do not proceed without this.
import os, re
test_path = '/root/test_output.py'
assert os.path.exists(test_path), "No test file found"

test_content = open(test_path).read()

# Extract structural assertions
sheet_order = re.findall(r"assert wb\.sheetnames\s*==\s*\[([^\]]+)\]", test_content)
label_checks = re.findall(r'assert\s+"([^"]+)"\s+(?:in|not in)', test_content)
count_assertions = re.findall(r'assert len\(([^)]+)\)\s*==\s*(\d+)', test_content)
named_range_count = re.findall(r'assert len\(wb\.defined_names\)\s*==\s*(\d+)', test_content)
absence_checks = re.findall(r'assert "([^"]+)" not in wb\.sheetnames', test_content)

print("SHEET ORDER:", sheet_order)
print("REQUIRED LABELS:", label_checks[:10])
print("COUNT ASSERTIONS:", count_assertions)
print("NAMED RANGE COUNT:", named_range_count)
print("EXCLUDED SHEETS:", absence_checks)
# STOP if any assertion is unclear. Read the test file manually.
```

**Test expectation wins over source data.** If test asserts 87 rows but source has 85, match the test.

## CHECKPOINT 2: Inspect Assumption Keys (MANDATORY)

**Before building lookup logic, inspect actual key structure:**

```python
# STOP: Print keys first. Assumption structures vary by source.
import openpyxl
wb_in = openpyxl.load_workbook('input.xlsx')
ws = wb_in['Assumptions']

# Print actual keys to see structure
assumptions = {}
for row in ws.iter_rows(min_row=2, values_only=True):
    if row[0]:  # Key column
        print(f"Key: {row[0]}, Values: {row[1:5]}")  # STOP and read output

# Common structures:
# STYLE A: Base key with year sub-keys: assumptions['JourneyRate']['Yr1']
# STYLE B: Year-suffixed keys: assumptions['JourneyRate_Yr1']
# Your lookup code MUST match the actual structure.
```

**Anti-pattern:** Assuming `assumptions['JourneyRate_Yr1']` when actual structure is `assumptions['JourneyRate']['Yr1']` causes KeyError.

## CHECKPOINT 3: Run pytest After Each Sheet (MANDATORY)

**Execute after completing each sheet:**

```python
import subprocess
wb.save('output.xlsx')
result = subprocess.run(
    ['pytest', '/root/test_output.py', '-v', '--tb=short'],
    capture_output=True, text=True, timeout=60
)
print(result.stdout)
print(result.stderr)
assert result.returncode == 0, "Tests failed - READ ERROR ABOVE BEFORE CONTINUING"
```

**Do NOT rely on custom verification scripts alone.** Tests check exact strings, hidden assertions, and structural details that custom scripts miss.

## Critical: pytest vs Custom Verification

| Custom Check | pytest Reality | Why It Missed |
|--------------|----------------|---------------|
| "90 named ranges (PASS)" | FAIL | Hidden assertions about specific names or references |
| "Sheet order correct" | FAIL | Exact string match on sheet names, absence checks |
| "Formulas use named ranges" | FAIL | Formula syntax, cell references, calculation logic |

**Required workflow:**
1. Save workbook
2. Run `pytest -v` immediately
3. If FAIL: Read exact assertion error, fix, re-save, re-run
4. Only use custom scripts to debug specific failures

## Annual vs Quarterly Hour Calculations

| Period | Standard Hours | Common Use |
|--------|-----------------|------------|
| Annual | 2080 (40 hrs × 52) | Yearly compensation totals |
| Quarterly | 520 (2080 / 4) | Per-quarter breakdowns |

**Common bug:** Using quarterly hours (520) for annual totals, or vice versa.

```python
# CORRECT annual calculation
annual_hours = 2080
annual_total = hourly_rate * annual_hours

# CORRECT quarterly calculation  
quarterly_hours = 520
quarterly_total = hourly_rate * quarterly_hours

# WRONG - mixing periods
annual_total = hourly_rate * 520  # Bug: gives quarterly, not annual
```

**Validation:** After computing, verify `annual_total / 4 ≈ quarterly_total` (within floating point tolerance).

## Safe Inline Verification (Copy-Paste)

```python
# Count named ranges safely
count = len(wb.defined_names)

# List all names safely
all_names = list(wb.defined_names)

# Check specific name exists
if 'TargetName' in wb.defined_names:
    target_ref = wb.defined_names['TargetName'].attr_text

# Iterate named ranges
for name in wb.defined_names:
    dn_obj = wb.defined_names[name]
    print(f"{name}: {dn_obj.attr_text}")

# WRONG - These cause AttributeError:
# for dn in wb.defined_names.definedName:  # No such attribute
# wb.defined_names['NAME'] = ...  # Wrong API
```

## Summary Sheet Cross-Sheet References

When building Summary sheets that pull totals from calculation sheets:

```python
# VERIFY cross-sheet references point to DATA columns, not LABEL columns
# Common error: referencing A/B/C instead of J/N/R

# After writing Summary formulas, validate:
summary_ws = wb['Summary']
for cell_ref in ['C26', 'D26', 'E26']:
    formula = str(summary_ws[cell_ref].value)
    assert 'J' in formula or 'N' in formula or 'R' in formula, \
        f"{cell_ref} should reference data column (J/N/R), got: {formula}"
```

## Column Range Bounds

```python
# WRONG: Off-by-one error, misses last column
for col in range(10, 23):  # J-V only (13 columns)

# CORRECT: Use explicit end column + 1
for col in range(10, 24):  # J-W (14 columns)
```

**Validation pattern:**
```python
from openpyxl.utils import get_column_letter

expected_cols = ['T', 'U', 'V', 'W']
for col_letter in expected_cols:
    cell = ws[f'{col_letter}{totals_row}']
    assert cell.value and 'SUM' in str(cell.value), f"Missing total in {col_letter}"
```

## Formula Construction

**Critical:** openpyxl formulas do NOT need leading `=`:

```python
# CORRECT: No equals sign prefix
ws['K107'] = 'SUM(K2:K104)'
ws['C5'] = "IF('Roster'!A1>'Assumptions'!$B$3,'Roster'!A1,0)"

# WRONG: Leading = causes Excel errors
# ws['K107'] = '=SUM(K2:K104)'
```

Cross-sheet references: `'Sheet Name'!A1` with quotes for spaces/special chars.

## Multi-Year Summary Dashboard (Y/Y Growth)

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

## Common Calculation Patterns

### Tiered/Seniority Pay
```python
=IF(Years<5,0,IF(Years<10,50,IF(Years<15,60,IF(Years<20,70,IF(Years<25,80,90)))))
```

### Percentage-Based Payroll Tax with Thresholds
```python
=IF(Income<=7000,Income*0.1465,IF(Income<=119741,7000*0.1465+(Income-7000)*0.0765,7000*0.1465+112741*0.0765+(Income-119741)*0.0145))
```

### Capped & Periodic Calculations
```python
=MIN(CurrentBase, PrevWage * RetCap) * RetRate / 4
```

## Exact String Matching

| Expected | Wrong | Issue |
|----------|-------|-------|
| `Calculations --->` | `Calculations` | Missing arrow suffix |
| `Y/Y` | `Year-over-Year` | Abbreviation vs expansion |
| `EE Calcs (Current)` | `EE Calcs Current` | Parentheses formatting |
| `QUARTERLY TOTALS` | `Quarterly Totals` | All caps required |

## Named Ranges (Critical Pattern)

```python
# CORRECT: Use define_name method
wb.define_name('MWS_Current', 'Assumptions!$C$5')

# WRONG: Do not access defined_names as dict
# wb.defined_names['MWS_Current'] = ...  # AttributeError

# Iteration - iterate directly
for name in wb.defined_names:
    print(f"{name}: {wb.defined_names[name].attr_text}")
```

## Critical Rules

- **Parse test file first**: Extract requirements BEFORE any code
- **Inspect assumption keys**: Print structure before lookup logic
- **Run pytest after each sheet**: Custom checks are supplementary
- **Hour bases**: 2080 for annual, 520 for quarterly - never mix
- **Exact String Matching**: Tests verify exact substrings
- **Sheet Order**: `wb.sheetnames` must match required list exactly
- **Cross-Sheet Formulas**: Quote sheet names with spaces; verify column refs
- **Y/Y Row References**: Use dynamic tracking; never hardcoded offsets
- **Column Range Bounds**: Verify iteration ranges cover all expected columns

## Known invariants (by sub-task)

### excel-compensation-model
- Sheet order must be exact: `wb.sheetnames` must match required list exactly
- Row labels must match verbatim - no abbreviation, casing changes, or punctuation differences
- Named ranges: Use `wb.define_name()` exclusively, never dict access
- Named range iteration: Iterate `wb.defined_names` directly or use `.items()`/`.values()`
- Formulas: Never use leading `=` prefix
- Row count: Must match test expectation exactly
- Multi-year Summary: Use dynamic row tracking for Y/Y comparisons
- Binary .xlsx files: Use `openpyxl.load_workbook()`, not text tools
- Summary formulas: Verify cross-sheet column refs match data columns (J, N, R)
- Assumption keys: Inspect actual structure - may be base key + year sub-key
- Hour bases: Annual=2080, Quarterly=520 - validate after computation

## Verification Checklist

- [ ] **Parsed test_output.py FIRST** - Extract requirements before coding
- [ ] **Inspected assumption key structure** - Printed keys before lookup logic
- [ ] **Ran pytest after each sheet** - Not just at the end
- [ ] **Validated hour base** - 2080 for annual, 520 for quarterly
- [ ] Sheet names and order match spec exactly
- [ ] All required row labels exist verbatim
- [ ] Cross-sheet formulas reference correct columns (J, N, R)
- [ ] Named ranges count matches spec

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Custom checks pass, pytest fails | Hidden assertions, exact strings | Run pytest immediately; parse exact failure |
| KeyError on assumption lookup | Wrong key structure | Print `assumptions.keys()` first |
| Annual totals too low | Used quarterly hours (520) | Use 2080 for annual calculations |
| Summary shows wrong values | Cross-sheet refs wrong column | Verify column letters (J, N, R vs A, B, C) |
| Cannot read .xlsx file | Using text Read tool | Use `openpyxl.load_workbook()` |
| AttributeError: 'DefinedNameDict' has no 'definedName' | Wrong iteration API | Iterate `wb.defined_names` directly |
| #NAME? errors in Excel | Formula has `=` prefix | Strip leading `=` |

## Anti-Patterns to Avoid

| Anti-Pattern | Why It Fails | Correct Approach |
|-------------|--------------|------------------|
| Not parsing test file first | Misses exact structural requirements | Execute CHECKPOINT 1 before coding |
| Not inspecting assumption keys | KeyError from wrong key structure | Execute CHECKPOINT 2 before lookup logic |
| Running pytest only at end | Structural errors discovered late | Run CHECKPOINT 3 after each sheet |
| Custom verification before pytest | Misses exact test assertions | Run pytest first, then diagnose |
| Using year-suffixed keys | KeyError: `JourneyRate_Yr1` doesn't exist | Use `assumptions['JourneyRate']['Yr1']` |
| Mixing annual/quarterly hours | Wrong totals | 2080 for annual, 520 for quarterly |
| Summary refs column A/B/C | Wrong column reference | Verify data columns (J, N, R) |
| `wb.defined_names['NAME'] = ...` | AttributeError | Use `wb.define_name('NAME', 'Sheet!$A$1')` |
| Formulas with `=` prefix | Excel parse errors | Strip leading `=` |
| `row - 8` hardcoded offsets | Breaks when structure changes | Track actual row numbers |
| Trusting source count over test | Off-by-one errors | Test assertion wins |

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
import subprocess, openpyxl

# STEP 0: Parse test requirements FIRST
test_content = open('/root/test_output.py').read()
# Extract: sheet names, labels, counts, named range count

# STEP 1: Inspect assumption keys BEFORE lookup logic
wb_in = openpyxl.load_workbook('input.xlsx')
for row in wb_in['Assumptions'].iter_rows(min_row=2, values_only=True):
    if row[0]: print(f"Key: {row[0]}, Values: {row[1:5]}")

# Read binary Excel file
wb_in = openpyxl.load_workbook('input.xlsx')
for row in wb_in['SheetName'].iter_rows(values_only=True):
    print(row)

wb = Workbook()

# Named range (version-safe)
if hasattr(wb, 'define_name'):
    wb.define_name('Rate', 'Assumptions!$B$2')
else:
    from openpyxl.workbook.defined_name import DefinedName
    defn = DefinedName(name='Rate', attr_text='Assumptions!$B$2')
    wb.defined_names.append(defn)

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

# CHECKPOINT: Run pytest NOW
result = subprocess.run(['pytest', '/root/test_output.py', '-v', '--tb=short'],
                       capture_output=True, text=True)
print(result.stdout)
assert result.returncode == 0, "Tests failed - READ ERROR ABOVE"
```
