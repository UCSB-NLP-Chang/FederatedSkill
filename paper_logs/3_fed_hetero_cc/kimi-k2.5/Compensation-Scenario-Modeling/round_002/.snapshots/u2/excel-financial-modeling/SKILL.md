---
name: excel-financial-modeling
description: Build complex, formula-driven Excel workbooks for financial modeling, compensation analysis, and multi-year projections using openpyxl. Use when tasks require named ranges, cross-sheet formulas, tiered calculations, or assumption-driven models that must recalculate automatically. Also use for multi-year Summary dashboards with year-over-year growth calculations.
---

# Excel Financial Modeling with openpyxl

## When to Use

- Multi-year financial projections with cascading assumptions
- Compensation models with tiered pay structures, seniority bands, or tax brackets
- Workbooks requiring named ranges for maintainability
- Cross-sheet formula dependencies (e.g., Summary pulls from Assumptions)
- Models where users will tweak inputs and expect automatic recalculation

## Core Workflow

### 1. Extract Test Expectations First

**Parse test files for exact expectations before building.** Do not guess layout:

```python
# Read test file to extract exact sheet names, order, row/column indices, label strings
# Look for: assert wb.sheetnames == [...], assert "Label" in ..., assert ... not in wb.sheetnames
```

Key test patterns to find:
- Exact sheet names and required order (`wb.sheetnames == [...]`)
- Required row labels (exact strings with punctuation)
- Named range count expectations
- Absence checks (`assert "Archive" not in wb.sheetnames`)

### 2. Structure Design

Design sheets in dependency order:
```
1. Summary      - Dashboard with formulas pointing to calculation sheets
2. Assumptions  - All input drivers (MWS, rates, thresholds) - ONE SOURCE OF TRUTH
3. Roster       - Entity list (employees, products, etc.) with attributes
4. Calculations - Per-entity detailed breakdowns (usually one sheet per scenario/year)
```

### 3. Named Ranges (Critical Pattern)

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

Naming convention for time-variant assumptions:
- `MWS_Current`, `MWS_Year_Plus_1`, `MWS_Year_Plus_2`
- `Seniority_5_9_Current`, `Seniority_5_9_Year_Plus_1`

### 4. Formula Construction

**Critical:** openpyxl formulas do NOT need leading `=`:

```python
# CORRECT: No equals sign prefix
ws['K107'] = 'SUM(K2:K104)'
ws['D2'] = 'IF(Roster!E6<>"",Roster!E6+1,"")'

# WRONG: Leading = causes Excel errors
# ws['K107'] = '=SUM(K2:K104)'
```

Cross-sheet references use `!` separator:
- `'Assumptions!C5'` - cell reference in named range definition
- `'Roster!E6'` - cell reference in formula

### 5. Multi-Year Projection Pattern

For Year+1, Year+2 scenarios:
1. Copy base calculation sheet structure
2. Increment year references in formulas: `+1`, `+2`
3. Point to same Assumptions columns (different years side-by-side)
4. Named ranges separate per year for flexibility

### 6. Multi-Year Summary Dashboard Pattern (Critical for Y/Y Growth)

When building Summary sheets with Y/Y growth calculations, use **dynamic row tracking**, not hardcoded offsets:

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
            # Compare current year's total vs prior year's total
            formula = f"IF({col_letter}{prior_year_total_row}=0,0,({col_letter}{current_year_total_row}-{col_letter}{prior_year_total_row})/{col_letter}{prior_year_total_row})"
            ws.cell(row=row, column=col, value=formula)
        row += 1

    # Save for next iteration
    prior_year_total_row = current_year_total_row
    row += 1  # Spacer
```

### 7. Tiered Calculation Pattern

For progressive tax brackets or seniority bands:
- Define tier thresholds and rates as named ranges
- Use nested `IF()` or `VLOOKUP()` in formulas
- Keep tier logic in EE Calcs sheets, not hardcoded in formulas

Example tier structure:
```
Tier 1: 0 to $160,200 @ 14.65%
Tier 2: $160,200 to $200,000 @ 7.65%
Tier 3: Above $200,000 @ 1.45%
```

### 8. Run Tests Incrementally

Execute `pytest` after each major structural change:
1. After sheet creation and ordering
2. After header/label placement
3. After formula injection
4. After named range definition

Do not rely solely on custom verification scripts.

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
- Sheet order must be exact: `wb.sheetnames` must match required list exactly (R0: all workers failed sheet-order tests)
- Row labels must match verbatim - no abbreviation, casing changes, or punctuation differences
- Named ranges: Use `wb.define_name()` exclusively, never `wb.defined_names` dict access
- Formulas: Never use leading `=` prefix in openpyxl formula assignment
- Row count: Must match source data exactly - check with `len(data_rows)` before writing
- Multi-year Summary: Use dynamic row tracking for Y/Y comparisons, never hardcoded offsets
- Legacy/Archive sheets: Tests frequently assert old sheets are explicitly removed. Delete them before saving.

## Validation Checklist

Run before declaring complete:

```python
import openpyxl

wb = openpyxl.load_workbook('model.xlsx', data_only=False)

# 1. Sheet count and order
print(f"Sheets: {wb.sheetnames}")

# 2. Named ranges defined
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

## Anti-Patterns to Avoid

| Anti-Pattern | Why It Fails | Correct Approach |
|-------------|--------------|------------------|
| `wb.defined_names['NAME'] = ...` | AttributeError, wrong API | `wb.define_name('NAME', 'Sheet!$A$1')` |
| Formulas with `=` prefix | Excel parse errors, #NAME? | Strip leading `=`, use `'SUM(A1:A10)'` |
| Hardcoded row offsets for Y/Y | Breaks when categories added/removed | Track `prior_year_total_row` dynamically |
| `row - 8` or similar magic numbers | Structure changes invalidate formulas | Store actual row numbers during construction |
| Hardcoded calculated values | Model doesn't update | All outputs as formulas referencing assumptions |
| Deep nested IFs (>3 levels) | Unmaintainable, error-prone | Named ranges + lookup tables on Assumptions sheet |
| Mixing data_only=True/False | Formulas lost on inadvertent save | Always use `data_only=False` when working with formulas |

## Troubleshooting

### Named ranges not appearing in Excel
- Verify using `wb.define_name()`, not direct dict access
- Check that workbook was saved AFTER all define_name calls
- Verify with: `list(wb.defined_names.definedName)`

### #REF! errors in Excel
- Sheet names with spaces need quoting in some contexts: `'EE Calcs'!A1`
- Named range definition uses `!`, not `.` separator
- Cross-sheet formulas must reference existing sheets

### Formulas showing as text
- Ensure no leading `=` in formula assignment
- Check cell number format is not set to '@' (text)
- Verify workbook opened with `data_only=False`

### Y/Y growth formulas show #DIV/0! or wrong values
- Verify `prior_year_total_row` tracks the actual Total Compensation row, not a fixed offset
- Check that prior year block exists before calculating growth
- Add IFERROR wrapper: `IFERROR((Current-Prior)/Prior,"N/A")`

### Excel opens with calculation errors but formulas look correct
- Check if workbook was opened with Excel's manual calculation mode
- Verify named ranges point to existing sheets (create sheets BEFORE defining ranges)

### Custom verification passes but tests fail
- Parse test file for exact row/col expectations
- Run actual test suite incrementally, not just custom checks
- Compare exact strings including punctuation/suffixes

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

wb = Workbook()

# Named range (CORRECT API)
wb.define_name('Rate', "='Assumptions'!$B$2")

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
```
