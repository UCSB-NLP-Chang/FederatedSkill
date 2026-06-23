---
name: excel-financial-modeling
description: Build complex, formula-driven Excel workbooks for financial modeling, compensation analysis, and multi-year projections using openpyxl. Use when tasks require named ranges, cross-sheet formulas, tiered calculations, or assumption-driven models that must recalculate automatically. Also use for multi-year Summary dashboards with year-over-year growth calculations. CRITICAL: Always parse test files first before building; never rely solely on custom verification.
---

# Excel Financial Modeling with openpyxl

## When to Use

- Multi-year financial projections with cascading assumptions
- Compensation models with tiered pay structures, seniority bands, or tax brackets
- Workbooks requiring named ranges for maintainability
- Cross-sheet formula dependencies (e.g., Summary pulls from Assumptions)
- Models where users will tweak inputs and expect automatic recalculation

## Critical First Step: Parse Test Expectations

**Before writing any code, read the test file to extract exact expectations.**

```python
# Read test_output.py first - do not guess layout
with open('test_output.py') as f:
    test_content = f.read()

# Extract exact assertions to match:
# - wb.sheetnames == [...]  (exact order matters)
# - "Exact Label" in [...]  (verbatim strings with punctuation)
# - assert ... not in wb.sheetnames  (sheets that must NOT exist)
# - Specific cell values and formulas
```

Common test patterns that cause failures if missed:
| Pattern | Example | Why It Matters |
|---------|---------|----------------|
| Exact sheet order | `['Summary', 'Assumptions', ...]` | `wb.sheetnames` must match exactly |
| Verbatim labels | `'Y/Y Growth'` not `'Year-over-Year'` | Tests check substring or equality |
| Arrow suffix | `'Calculations --->'` | Missing ` --->` fails |
| Parentheses | `'EE Calcs (Current)'` | Format must match exactly |
| Absence checks | `assert 'Archive' not in wb.sheetnames` | Legacy sheets must be deleted |

**Anti-pattern:** Building based on task description summary, then verifying with custom scripts. This creates false confidence.

## Workflow

### 1. Read Input Files with openpyxl

Binary .xlsx files cannot be read with text tools. Use openpyxl directly:

```python
import openpyxl
wb = openpyxl.load_workbook('input.xlsx')
for sheet in wb.sheetnames:
    ws = wb[sheet]
    for row in ws.iter_rows(values_only=True):
        print(row)
```

### 2. Extract Test Expectations First

Parse test files for exact expectations before building. Do not guess layout:

```python
# Read test file to extract exact sheet names, order, row/column indices, label strings
# Look for: assert wb.sheetnames == [...], assert "Label" in ..., assert ... not in wb.sheetnames
```

Key test patterns to find:
- Exact sheet names and required order (`wb.sheetnames == [...]`)
- Required row labels (exact strings with punctuation)
- Named range count expectations
- Absence checks (`assert "Archive" not in wb.sheetnames`)

### 3. Create Sheets in Exact Order

`wb.sheetnames` must match required list exactly. Use `wb.move_sheet()` if creation order differs.

### 4. Populate Static Data

Write headers, labels, and inputs exactly as specified. No abbreviations.

### 5. Define Named Ranges (Critical Pattern)

Use `wb.define_name()`, NOT `wb.defined_names` dict manipulation:

```python
from openpyxl import Workbook

wb = Workbook()

# CORRECT: Use define_name method
wb.define_name('MWS_Current', 'Assumptions!$C$5')
wb.define_name('Payroll_Tax_Tier1_Rate', 'Assumptions!$D$19')

# WRONG: Do not access defined_names as dict
# wb.defined_names['MWS_Current'] = ...  # AttributeError or silent failures
```

**Iterating named ranges** - Use `wb.defined_names.definedName` (capital D), not lowercase:

```python
# CORRECT: Iterate with .definedName (capital D)
for name in wb.defined_names.definedName:
    print(f"{name.name}: {name.attr_text}")

# WRONG: lowercase causes AttributeError
# for name in wb.defined_names.definedname:  # AttributeError
```

Naming convention for time-variant assumptions:
- `MWS_Current`, `MWS_Year_Plus_1`, `MWS_Year_Plus_2`
- `Seniority_5_9_Current`, `Seniority_5_9_Year_Plus_1`

### 6. Write Formulas

**Critical:** openpyxl formulas do NOT need leading `=`:

```python
# CORRECT: No equals sign prefix
ws['K107'] = 'SUM(K2:K104)'
ws['D2'] = 'IF(Roster!E6<>"",Roster!E6+1,"")'

# WRONG: Leading = causes Excel errors
# ws['K107'] = '=SUM(K2:K104)'
```

Cross-sheet references: `'Sheet Name'!A1` with quotes for spaces/special chars.

### 7. Multi-Year Summary Dashboard (Y/Y Growth)

Use **dynamic row tracking**, not hardcoded offsets:

```python
# ANTI-PATTERN: Hardcoded offset breaks when structure changes
prev_year_row = row - 8  # Brittle!

# CORRECT: Track actual total rows as you build
prior_year_total_row = None

for year_idx, (year, sheet_name) in enumerate(years):
    # ... write category rows ...

    # Store this year's Total Compensation row
    current_year_total_row = row - 1

    # Y/Y Growth row (skip for first year)
    if year_idx > 0 and prior_year_total_row is not None:
        ws.cell(row=row, column=2, value='Y/Y Growth %')
        for col in range(3, 8):
            col_letter = get_column_letter(col)
            formula = f"IF({col_letter}{prior_year_total_row}=0,0,({col_letter}{current_year_total_row}-{col_letter}{prior_year_total_row})/{col_letter}{prior_year_total_row})"
            ws.cell(row=row, column=col, value=formula)
        row += 1

    # Save for next iteration
    prior_year_total_row = current_year_total_row
    row += 1  # Spacer
```

### 8. Navigation Sheets & Hyperlinks

For internal navigation sheets linking to calculation tabs:

```python
from openpyxl.worksheet.hyperlink import Hyperlink

# Create hyperlink cell
cell = ws.cell(row=r, column=c, value="EE Calcs (Current)")
cell.hyperlink = Hyperlink(ref="", location="'EE Calcs (Current)'!A1", display="EE Calcs (Current)")
# Ensure target sheet name matches exactly, including spaces/parentheses.
```

### 9. Run Tests Incrementally

**Execute `pytest` after each major structural change.** Do not rely solely on custom verification scripts.

```bash
# Run after each major step, not just at the end
pytest test_output.py -v

# If tests fail, read the specific assertion that failed
pytest test_output.py -v --tb=short
```

**Critical distinction:**
- Custom verification scripts check that YOUR understanding is satisfied
- `pytest` checks that THE TEST AUTHOR's expectations are met
- These often diverge; only pytest matters for pass/fail

Incremental pytest checkpoints:
1. After sheet creation and ordering
2. After header/label placement
3. After formula injection
4. After named range definition

## Common Calculation Patterns

### Tiered/Seniority Pay

```python
# Nested IF for tiered values (5-9y: $50, 10-14y: $60, etc.)
=IF(Years<5,0,IF(Years<10,50,IF(Years<15,60,IF(Years<20,70,IF(Years<25,80,90)))))
```

### Percentage-Based Payroll Tax with Thresholds

```python
# Multi-tier: 14.65% up to $7,000, 7.65% $7,001-$119,741, 1.45% above
=IF(Income<=7000,Income*0.1465,IF(Income<=119741,7000*0.1465+(Income-7000)*0.0765,7000*0.1465+112741*0.0765+(Income-119741)*0.0145))
```

### Principal Pay as Percentage of Base

```python
=IF(Title="Principal",MWS*0.20,IF(Title="Associate Principal",MWS*0.10,IF(Title="Assistant Principal",MWS*0.10,0)))
```

### Capped & Periodic Calculations

Common in benefits (retirement match, health caps, quarterly breakdowns):

```python
# Capped percentage: MIN(base, cap * multiplier) * rate / periods
# Example: Retirement match capped at previous year wage * RetCap, paid quarterly
=MIN(CurrentBase, PrevWage * RetCap) * RetRate / 4

# Quarterly breakdown of annual value
=AnnualValue / 4
```

## Exact String Matching (Critical for Tests)

Tests verify exact substrings or full strings for sheet names and row labels. Slight variations cause failures:

| Expected | Wrong | Issue |
|----------|-------|-------|
| `Calculations --->` | `Calculations` | Missing arrow suffix |
| `Y/Y` | `Year-over-Year` | Abbreviation vs expansion |
| `EE Calcs (Current)` | `EE Calcs Current` | Parentheses formatting |
| `Y/Y Change` | `YoY Change` | Exact casing/punctuation |

**Before finalizing, compare your output against expected structure:**

```python
# Read test expectations first if available
expected_sheets = ['Summary', 'Assumptions', 'Roster', 'Calculations --->']
assert wb.sheetnames == expected_sheets, f"Got {wb.sheetnames}"

# Verify exact row labels
expected_labels = ['Total Pay', 'Y/Y Change', 'Payroll Tax']
found_labels = [row[0] for row in ws.iter_rows(min_col=1, max_col=1, values_only=True) if row[0]]
for lbl in expected_labels:
    assert lbl in found_labels, f"Missing '{lbl}'"
```

See `references/verification-patterns.md` for common test assertions.

## Known invariants (by sub-task)

### excel-compensation-model
- Sheet order must be exact: `wb.sheetnames` must match required list exactly
- Row labels must match verbatim - no abbreviation, casing changes, or punctuation differences
- Named ranges: Use `wb.define_name()` exclusively, never `wb.defined_names` dict access
- Formulas: Never use leading `=` prefix in openpyxl formula assignment
- Row count: Must match source data exactly - check with `len(data_rows)` before writing
- Multi-year Summary: Use dynamic row tracking for Y/Y comparisons, never hardcoded offsets
- Legacy/Archive sheets: Tests frequently assert old sheets are explicitly removed. Delete them before saving.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Validation Checklist

Run before declaring complete:

```python
import openpyxl

wb = openpyxl.load_workbook('model.xlsx', data_only=False)

# 1. Sheet count and order
print(f"Sheets: {wb.sheetnames}")

# 2. Named ranges defined (use capital D in definedName)
for name in wb.defined_names.definedName:
    print(f"  {name.name}: {name.attr_text}")

# 3. Formula preservation (not calculated values)
ws = wb['EE Calcs (Current)']
print(f"Sample formula: {ws['K107'].value}")  # Should show formula string

# 4. Cross-sheet references intact
print(f"Cross-ref: {ws['D2'].value}")  # Should show 'Roster!E6' reference

# 5. Multi-year Summary Y/Y formulas point to correct rows
ws_sum = wb['Summary']
print(f"Y/Y formula: {ws_sum['C43'].value}")  # Should reference prior year total row
```

**Final step: Run the actual test suite**

```bash
pytest test_output.py -v
```

## Anti-Patterns to Avoid

| Anti-Pattern | Why It Fails | Correct Approach |
|-------------|--------------|------------------|
| Custom verification only | Passes custom checks, fails official tests | Run `pytest` incrementally |
| Not reading test file first | Misses exact string requirements | Parse test_output.py before building |
| Reading .xlsx with text tools | Binary file error | Use openpyxl.load_workbook() |
| `wb.defined_names['NAME'] = ...` | AttributeError, wrong API | `wb.define_name('NAME', 'Sheet!$A$1')` |
| `wb.defined_names.definedname` (lowercase) | AttributeError | `wb.defined_names.definedName` (capital D) |
| Formulas with `=` prefix | Excel parse errors, #NAME? | Strip leading `=`, use `'SUM(A1:A10)'` |
| Hardcoded row offsets for Y/Y | Breaks when categories added/removed | Track `prior_year_total_row` dynamically |
| `row - 8` or similar magic numbers | Structure changes invalidate formulas | Store actual row numbers during construction |
| Hardcoded calculated values | Model doesn't update | All outputs as formulas referencing assumptions |
| Deep nested IFs (>3 levels) | Unmaintainable, error-prone | Named ranges + lookup tables on Assumptions sheet |
| Mixing data_only=True/False | Formulas lost on inadvertent save | Always use `data_only=False` when working with formulas |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Cannot read .xlsx file | Using text Read tool | Use openpyxl.load_workbook() |
| Named ranges not appearing | Wrong API used | Use `wb.define_name()`, not dict access |
| AttributeError iterating named ranges | Wrong casing | Use `wb.defined_names.definedName` (capital D) |
| #NAME? errors in Excel | Formula has `=` prefix | Strip leading `=`, use `'SUM(A1:A10)'` |
| Test fails on sheet order | Creation order differs | Use `wb.move_sheet()` to reorder |
| Missing row labels | Casing/punctuation mismatch | Use exact strings, substring search |
| #REF! errors | Sheet name mismatch in formula | Quote names with spaces: `'EE Calcs'!A1` |
| Y/Y growth formulas show #DIV/0! | `prior_year_total_row` incorrect | Track actual Total Compensation row, not fixed offset |
| Custom checks pass, tests fail | Mismatch in exact indices or hidden assertions | Run `pytest` immediately after structural changes |
| Legacy sheets still present | Not explicitly deleted | Delete old sheets: `del wb['Archive Notes']` |
| Hyperlinks broken or missing | Incorrect location syntax | Use `Hyperlink(location="'Sheet'!A1")` with exact sheet name |

## Extension: Complex Models

For very large models (500+ rows, 10+ sheets):
- See `references/large-model-patterns.md` for memory optimization
- Use `scripts/verify_formulas.py` to audit formula consistency across year sheets
- Use `scripts/verify_workbook.py` for quick structural verification
- Consider `write_only=True` workbook mode for generation speed

## Quick Reference

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

# Read binary Excel file
import openpyxl
wb_in = openpyxl.load_workbook('input.xlsx')
ws = wb_in['SheetName']
for row in ws.iter_rows(values_only=True):
    print(row)

wb = Workbook()

# Named range (CORRECT API)
wb.define_name('Rate', 'Assumptions!$B$2')

# Iterate named ranges (capital D)
for name in wb.defined_names.definedName:
    print(f"{name.name}: {name.attr_text}")

# Formula cell (no = prefix)
ws['C5'] = 'A1*B1'

# Cross-sheet formula
ws['C5'] = "IF('Roster'!A1>'Assumptions'!$B$3,'Roster'!A1,0)"

# Multi-year Summary with dynamic row tracking
prior_total = None
for year_idx, year in enumerate(['Current', 'Year+1']):
    # ... build year block ...
    current_total = row - 1
    if prior_total:
        for col in range(3, 8):
            cl = get_column_letter(col)
            ws.cell(row=row, column=col,
                   value=f"IF({cl}{prior_total}=0,0,({cl}{current_total}-{cl}{prior_total})/{cl}{prior_total})")
    prior_total = current_total

wb.save('model.xlsx')

# FINAL STEP: Run official tests
# pytest test_output.py -v
```