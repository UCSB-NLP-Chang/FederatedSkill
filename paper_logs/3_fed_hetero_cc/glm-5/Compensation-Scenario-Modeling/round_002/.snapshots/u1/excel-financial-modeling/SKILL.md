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

## Workflow

1. **Extract Test Expectations First** - Parse test files for exact sheet names, order, row/column indices, label strings, and absence checks (e.g., `assert "Archive" not in wb.sheetnames`). Do not guess layout.
2. **Parse Source Data** - Use openpyxl to inspect all sheets, dimensions, and data types.
3. **Create Sheets in Exact Order** - `wb.sheetnames` must match required list exactly. Use `wb.move_sheet()` if creation order differs.
4. **Populate Static Data** - Write headers, labels, and inputs exactly as specified. No abbreviations.
5. **Define Named Ranges** - Use `wb.define_name()` after cells exist.
6. **Write Formulas** - NO leading `=` prefix (openpyxl syntax). Use exact sheet names with quotes for spaces/special chars.
7. **Run Actual Tests Incrementally** - Execute `pytest` after each major structural change. Do not rely solely on custom verification scripts.

## Named Ranges (Critical Pattern)

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

## Formula Construction

**Critical:** openpyxl formulas do NOT need leading `=`:

```python
# CORRECT: No equals sign prefix
ws['K107'] = 'SUM(K2:K104)'
ws['D2'] = 'IF(Roster!E6<>"",Roster!E6+1,"")'

# WRONG: Leading = causes Excel errors
# ws['K107'] = '=SUM(K2:K104)'
```

Cross-sheet references: `'Sheet Name'!A1` with quotes for spaces/special chars.

## Multi-Year Summary Dashboard Pattern

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
            formula = f"IF({col_letter}{prior_year_total_row}=0,0,({col_letter}{current_year_total_row}-{col_letter}{prior_year_total_row})/{col_letter}{prior_year_total_row})"
            ws.cell(row=row, column=col, value=formula)
        row += 1

    # Save for next iteration
    prior_year_total_row = current_year_total_row
    row += 1  # Spacer
```

## Exact String Matching (Critical for Tests)

Tests verify exact substrings or full strings for sheet names and row labels. Slight variations cause failures:

| Expected | Wrong | Issue |
|----------|-------|-------|
| `Calculations --->` | `Calculations` | Missing arrow suffix |
| `Y/Y` | `Year-over-Year` | Abbreviation vs expansion |
| `EE Calcs (Current)` | `EE Calcs Current` | Parentheses formatting |
| `Y/Y Change` | `YoY Change` | Exact casing/punctuation |

Before finalizing, compare your output against expected structure:
```python
expected_sheets = ['Summary', 'Assumptions', 'Roster', 'Calculations --->']
assert wb.sheetnames == expected_sheets, f"Got {wb.sheetnames}"

expected_labels = ['Total Pay', 'Y/Y Change', 'Payroll Tax']
found_labels = [row[0] for row in ws.iter_rows(min_col=1, max_col=1, values_only=True) if row[0]]
for lbl in expected_labels:
    assert lbl in found_labels, f"Missing '{lbl}'"
```

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

## Known invariants (by sub-task)

### excel-compensation-model
- Sheet order must be exact: `wb.sheetnames` must match required list exactly
- Row labels must match verbatim - no abbreviation, casing changes, or punctuation differences
- Named ranges: Use `wb.define_name()` exclusively, never `wb.defined_names` dict access
- Formulas: Never use leading `=` prefix in openpyxl formula assignment
- Row count: Must match source data exactly - check with `len(data_rows)` before writing
- Multi-year Summary: Use dynamic row tracking for Y/Y comparisons, never hardcoded offsets
- Legacy/Archive sheets: Tests frequently assert that old sheets (e.g., `Archive Notes`, `Legacy Data`) are explicitly removed. Delete them before saving.

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
| Hardcoded calculated values | Model doesn't update | All outputs as formulas referencing assumptions |
| Hardcoded row offsets for Y/Y | Breaks when categories added/removed | Track `prior_year_total_row` dynamically |
| `row - 8` or similar magic numbers | Structure changes invalidate formulas | Store actual row numbers during construction |
| Abbreviated labels | Exact string match fails | Copy labels verbatim from spec/source |
| Deep nested IFs (>3 levels) | Unmaintainable, error-prone | Named ranges + lookup tables on Assumptions sheet |
| Relying on custom verification only | Misses exact test assertions | Run actual test suite incrementally |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Named ranges not appearing | Wrong API used | Use `wb.define_name()`, not dict access |
| #NAME? errors in Excel | Formula has `=` prefix | Strip leading `=`, use `'SUM(A1:A10)'` |
| Test fails on sheet order | Creation order differs | Use `wb.move_sheet()` to reorder |
| Missing row labels | Casing/punctuation mismatch | Use exact strings, substring search |
| #REF! errors | Sheet name mismatch in formula | Quote names with spaces: `'EE Calcs'!A1` |
| Y/Y growth formulas show #DIV/0! | `prior_year_total_row` incorrect | Track actual Total Compensation row, not fixed offset |
| Custom checks pass, tests fail | Mismatch in exact indices or hidden assertions | Run `pytest` immediately after structural changes |
| Legacy sheets still present | Not explicitly deleted | Delete old sheets: `del wb['Archive Notes']` |

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

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