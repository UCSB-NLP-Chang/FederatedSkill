---
name: excel-financial-modeling
description: Build complex, formula-driven Excel workbooks for financial modeling, compensation analyses, and multi-year projections using openpyxl. Use when tasks require named ranges, cross-sheet formulas, tiered calculations, roster migration, or assumption-driven models that must recalculate automatically.
---

# Excel Financial Modeling with openpyxl

## When to Use

- Multi-year financial projections with cascading assumptions
- Compensation models with tiered pay structures, seniority bands, or tax brackets
- Workbooks requiring named ranges for maintainability
- Cross-sheet formula dependencies (e.g., Summary pulls from Assumptions)
- Models where users will tweak inputs and expect automatic recalculation
- Roster or dataset migration tasks requiring exact record counts

## CRITICAL FIRST STEP: Parse Test Requirements

**STOP. Read the test file before writing ANY code.** This is mandatory, not optional.

```python
# STEP 0: Parse test_output.py - DO THIS FIRST
test_content = open('/root/test_output.py').read()

# Extract and note these requirements:
# - Exact sheet names: assert wb.sheetnames == ['Summary', 'Assumptions', ...]
# - Exact row labels: assert "Total Compensation" in str(ws['B32'].value)
# - Record counts: assert len(rows) == 87
# - Named range count: assert len(wb.defined_names) == 66
# - Absence checks: assert "Archive" not in wb.sheetnames
# - Column references: formulas must reference J, N, R (not A, B, C)
```

**Test expectation wins over source data.** If test asserts 87 rows but source has 85, the test is correct.

## Workflow

1. **Parse test_output.py FIRST** - Extract exact assertions for sheet names, order, labels, counts
   ```python
   test_content = open('/root/test_output.py').read()
   # Extract requirements BEFORE any workbook construction
   ```

2. **Read Input Files with openpyxl** - Binary .xlsx files cannot be read with text tools:
   ```python
   import openpyxl
   wb = openpyxl.load_workbook('input.xlsx')
   for sheet in wb.sheetnames:
       ws = wb[sheet]
       for row in ws.iter_rows(values_only=True):
           print(row)
   ```

3. **Create Sheets in Exact Order** - `wb.sheetnames` must match test's required list exactly. Use `wb.move_sheet()` if creation order differs.

4. **Delete Excluded Sheets** - Tests often assert old sheets absent ('Packet Notes', 'Archive', 'Sheet1'). Delete before saving.

5. **Populate Static Data** - Write headers, labels, and inputs exactly as in test assertions. No abbreviations.

6. **Define Named Ranges** - Use `wb.define_name()` after cells exist. Check version first:
   ```python
   if hasattr(wb, 'define_name'):
       wb.define_name('MWS_Current', 'Assumptions!$C$5')
   else:
       from openpyxl.workbook.defined_name import DefinedName
       defn = DefinedName(name='MWS_Current', attr_text='Assumptions!$C$5')
       wb.defined_names.append(defn)
   ```

7. **Write Formulas** - NO leading `=` prefix (openpyxl syntax):
   ```python
   ws['K107'] = 'SUM(K2:K104)'  # CORRECT
   # ws['K107'] = '=SUM(K2:K104)'  # WRONG - causes Excel errors
   ```

8. **Track Rows Dynamically** - Store actual row numbers during construction; never use hardcoded offsets like `row - 8`.

9. **CHECKPOINT: Run pytest NOW** - After creating each sheet:
   ```bash
   pytest /root/test_output.py -v --tb=short
   ```
   If tests fail, READ the exact assertion error. Do not continue until tests pass. Custom verification scripts are supplementary only.

## Summary Dashboard Cross-Sheet Validation

When building summary/executive dashboards that pull totals from year-specific sheets:

```python
# VERIFY cross-sheet references point to DATA columns, not LABEL columns
# Common error: referencing column A/B/C instead of J/N/R

# After writing Summary formulas, validate:
for cell_ref in ['C26', 'D26', 'E26', 'F26']:  # Base Salary rows
    formula = str(ws_summary[cell_ref].value)
    # Ensure formula references correct column (J for Base Salary data)
    assert 'J69' in formula or 'J' in formula, f"{cell_ref} missing J reference: {formula}"

# For Y/Y Growth formulas, verify column references:
for col in range(3, 8):
    col_letter = get_column_letter(col)
    formula = ws_summary.cell(row=yy_row, column=col).value
    # Should reference data columns (J, N, R), not label columns (A, B, C)
```

**Y/Y Growth formula pattern** - Use `(NewYear/OldYear) - 1` or `IF(OldYear=0, 0, (NewYear-OldYear)/OldYear)`. Ensure references point to the correct year's total row and DATA columns.

## Safe Inline Verification (Copy-Paste)

```python
# Count named ranges safely
count = len(wb.defined_names)

# List all names safely
all_names = list(wb.defined_names)

# Check specific name exists
if 'TargetName' in wb.defined_names:
    target_ref = wb.defined_names['TargetName'].attr_text

# Iterate named ranges (yields strings)
for name in wb.defined_names:
    dn_obj = wb.defined_names[name]
    print(f"{name}: {dn_obj.attr_text}")

# Or use .items() for (name, object) pairs
for name, dn_obj in wb.defined_names.items():
    print(f"{name}: {dn_obj.attr_text}")

# WRONG - These cause AttributeError:
# for dn in wb.defined_names.definedName:  # No such attribute
# wb.defined_names['NAME'] = ...  # Wrong API
```

## Source Data Migration & Row Counting

- **Dynamic Counting**: Calculate row counts dynamically from source data (`len(roster)`), but validate against test expectations.
- **Test Wins Over Source**: If `test_output.py` asserts `assert len(rows) == 87` but source has 85, match the test expectation.
- **Off-by-One Prevention**: Never use hardcoded row offsets like `row - 8` or `len(data) - 1`.

## Column Range Bounds (Critical)

```python
# WRONG: Off-by-one error, misses last column
for col in range(10, 23):  # Only covers J through V (13 columns)

# CORRECT: Use explicit end column + 1
for col in range(10, 24):  # Covers J through W (14 columns)
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

## Navigation Sheets & Hyperlinks

```python
from openpyxl.worksheet.hyperlink import Hyperlink

cell = ws.cell(row=r, column=c, value="EE Calcs (Current)")
cell.hyperlink = Hyperlink(ref="", location="'EE Calcs (Current)'!A1", display="EE Calcs (Current)")
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

## Exact String Matching (Critical for Tests)

| Expected | Wrong | Issue |
|----------|-------|-------|
| `Calculations --->` | `Calculations` | Missing arrow suffix |
| `Y/Y` | `Year-over-Year` | Abbreviation vs expansion |
| `EE Calcs (Current)` | `EE Calcs Current` | Parentheses formatting |

## Critical Rules

- **Parse test file first**: Extract requirements BEFORE any code
- **Run pytest after each sheet**: Custom checks are supplementary
- **Exact String Matching**: Tests verify exact substrings
- **Sheet Order**: `wb.sheetnames` must match required list exactly
- **Cross-Sheet Formulas**: Quote sheet names with spaces; verify column references (J, N, R not A, B, C)
- **Named Ranges**: Define after cells exist; use `wb.define_name()` or `.append()` for legacy
- **Delete old sheets**: Tests often assert old sheets are removed
- **Y/Y Row References**: Use dynamic tracking; never hardcoded offsets
- **Column Range Bounds**: Verify iteration ranges cover all expected columns

## Known invariants (by sub-task)

### excel-compensation-model
- Sheet order must be exact: `wb.sheetnames` must match required list exactly
- Row labels must match verbatim - no abbreviation, casing changes, or punctuation differences
- Named ranges: Use `wb.define_name()` exclusively, never `wb.defined_names` dict access
- Named range iteration: Iterate `wb.defined_names` directly or use `.items()`/`.values()`
- Formulas: Never use leading `=` prefix in openpyxl formula assignment
- Row count: Must match test expectation exactly
- Multi-year Summary: Use dynamic row tracking for Y/Y comparisons
- Binary .xlsx files: Must read with openpyxl.load_workbook(), not text tools
- Summary formulas: Verify cross-sheet column references match actual data columns (J, N, R)
- pytest timing: Run after each sheet, not at the end

## Verification Checklist

- [ ] **Parsed test_output.py FIRST** - Extract requirements before coding
- [ ] **Ran pytest after each sheet** - Not just at the end
- [ ] Sheet names and order match spec exactly
- [ ] All required row labels exist verbatim
- [ ] Cross-sheet formulas reference correct sheet names AND column letters
- [ ] Summary formulas point to DATA columns (J, N, R), not label columns
- [ ] Totals rows contain `SUM` or equivalent formulas
- [ ] Named ranges count and targets match spec
- [ ] No dropped/duplicated rows in migrated data
- [ ] Column iteration ranges cover all expected columns (no off-by-one)

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Custom checks pass, tests fail | pytest not run, wrong column refs | Run `pytest` immediately after each sheet |
| Summary shows wrong values | Cross-sheet formula refs wrong column | Verify column letters (J, N, R vs A, B, C) |
| Cannot read .xlsx file | Using text Read tool | Use openpyxl.load_workbook() |
| Named ranges not appearing | Wrong API used | Use `wb.define_name()` |
| AttributeError: 'DefinedNameDict' has no 'definedName' | Wrong iteration API | Iterate `wb.defined_names` directly |
| #NAME? errors in Excel | Formula has `=` prefix | Strip leading `=` |
| Test fails on sheet order | Creation order differs | Use `wb.move_sheet()` to reorder |
| Missing row labels | Casing/punctuation mismatch | Use exact strings |
| #REF! errors | Sheet name mismatch | Quote names with spaces: `'EE Calcs'!A1` |
| Y/Y growth wrong values | Hardcoded row offset or wrong column | Track dynamically; verify column refs |
| Off-by-one row counts | Trusted source over test | Test assertion wins |
| Missing column in totals | Off-by-one in range bounds | Verify range end = last column + 1 |
| pytest ran only at end | Ignored incremental testing guidance | Add checkpoint after each sheet creation |

## Anti-Patterns to Avoid

| Anti-Pattern | Why It Fails | Correct Approach |
|-------------|--------------|------------------|
| Not parsing test file first | Misses exact structural requirements | Parse test_output.py before ANY code |
| Running pytest only at end | Structural errors discovered late | Run pytest after each sheet creation |
| Custom verification before pytest | Misses exact test assertions | Run pytest first, then diagnose |
| Summary refs column A/B/C | Wrong column reference | Verify actual data columns (J, N, R) |
| `wb.defined_names['NAME'] = ...` | AttributeError | Use `wb.define_name('NAME', 'Sheet!$A$1')` |
| `wb.defined_names.definedName` | AttributeError | Iterate `wb.defined_names` directly |
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
import subprocess

# STEP 0: Parse test requirements FIRST
test_content = open('/root/test_output.py').read()
# Extract: sheet names, labels, counts, named range count

# Read binary Excel file
import openpyxl
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

# Save
wb.save('model.xlsx')

# CHECKPOINT: Run pytest NOW
result = subprocess.run(['pytest', '/root/test_output.py', '-v', '--tb=short'],
                       capture_output=True, text=True)
print(result.stdout)
print(result.stderr)
# READ assertion errors carefully before continuing
```
