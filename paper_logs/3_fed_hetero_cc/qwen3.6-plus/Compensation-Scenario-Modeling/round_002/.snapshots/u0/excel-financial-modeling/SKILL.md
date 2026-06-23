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

## Workflow

1. **Extract Test Expectations First** - Parse test files for exact sheet names, order, row/column indices, label strings, and absence checks (e.g., `assert "Archive" not in wb.sheetnames`). Do not guess layout.
2. **Parse Source Data** - Use openpyxl to inspect all sheets, dimensions, and data types.
3. **Create Sheets in Exact Order** - `wb.sheetnames` must match required list exactly. Use `wb.move_sheet()` if creation order differs.
4. **Populate Static Data** - Write headers, labels, and inputs exactly as specified. No abbreviations.
5. **Define Named Ranges** - Use `wb.define_name()` after cells exist.
6. **Write Formulas** - NO leading `=` prefix (openpyxl syntax).
7. **Track Rows Dynamically for Multi-Year** - Store actual row numbers during construction; never use hardcoded offsets like `row - 8`.
8. **Run Actual Tests Incrementally** - Execute `pytest` after each major structural change (sheet creation, header placement, formula injection). Do not rely solely on custom verification scripts.

## Named Ranges (Critical Pattern)

Use `wb.define_name()`, NOT `wb.defined_names` dict manipulation:

```python
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

## Multi-Year Summary Dashboard (Y/Y Growth)

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

## Common Calculation Patterns

### Tiered/Seniority Pay
```python
# Nested IF for tiered values
=IF(Years<5,0,IF(Years<10,50,IF(Years<15,60,IF(Years<20,70,IF(Years<25,80,90)))))
```

### Percentage-Based Payroll Tax with Thresholds
```python
# Multi-tier tax: different rates for income bands
=IF(Income<=7000,Income*0.1465,IF(Income<=119741,7000*0.1465+(Income-7000)*0.0765,7000*0.1465+112741*0.0765+(Income-119741)*0.0145))
```

## Exact String Matching (Critical for Tests)

Tests verify exact substrings; slight variations cause failures:

| Expected | Wrong | Issue |
|----------|-------|-------|
| `Calculations --->` | `Calculations` | Missing arrow suffix |
| `Y/Y` | `Year-over-Year` | Abbreviation vs expansion |
| `EE Calcs (Current)` | `EE Calcs Current` | Parentheses formatting |

## Critical Rules

- **Exact String Matching**: Tests verify exact substrings for sheet names and row labels.
- **Sheet Order**: `wb.sheetnames` must match required list exactly.
- **Cross-Sheet Formulas**: Quote sheet names with spaces/special chars.
- **Data Integrity**: Row count must match source. No duplicates.
- **Named Ranges**: Define after cells exist. Verify count matches spec.
- **Legacy/Archive Sheets**: Tests frequently assert old sheets are removed. Delete them before saving.
- **Y/Y Row References**: Use dynamic tracking; never hardcoded offsets like `row - 8`.

## Known invariants (by sub-task)

### excel-compensation-model
- Sheet order must be exact: `wb.sheetnames` must match required list exactly
- Row labels must match verbatim - no abbreviation, casing changes, or punctuation differences
- Named ranges: Use `wb.define_name()` exclusively, never `wb.defined_names` dict access
- Formulas: Never use leading `=` prefix in openpyxl formula assignment
- Row count: Must match source data exactly
- Multi-year Summary: Use dynamic row tracking for Y/Y comparisons, never hardcoded offsets

## Verification Checklist

- [ ] Sheet names and order match spec exactly
- [ ] All required row labels exist verbatim
- [ ] Cross-sheet formulas reference correct sheet names
- [ ] Totals rows contain `SUM` or equivalent formulas
- [ ] Named ranges count and targets match spec
- [ ] No dropped/duplicated rows in migrated data
- [ ] Actual test suite passes incrementally (not just custom checks)

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Named ranges not appearing | Wrong API used | Use `wb.define_name()`, not dict access |
| #NAME? errors in Excel | Formula has `=` prefix | Strip leading `=`, use `'SUM(A1:A10)'` |
| Test fails on sheet order | Creation order differs | Use `wb.move_sheet()` to reorder |
| Missing row labels | Casing/punctuation mismatch | Use exact strings, substring search |
| #REF! errors | Sheet name mismatch in formula | Quote names with spaces: `'EE Calcs'!A1` |
| Custom checks pass, tests fail | Mismatch in exact indices or hidden assertions | Run `pytest` after each structural change |
| Y/Y growth wrong values | Hardcoded row offset | Track `prior_year_total_row` dynamically |

## Anti-Patterns to Avoid

| Anti-Pattern | Why It Fails | Correct Approach |
|-------------|--------------|------------------|
| `wb.defined_names['NAME'] = ...` | AttributeError, wrong API | `wb.define_name('NAME', 'Sheet!$A$1')` |
| Formulas with `=` prefix | Excel parse errors, #NAME? | Strip leading `=`, use `'SUM(A1:A10)'` |
| Hardcoded calculated values | Model doesn't update | All outputs as formulas referencing assumptions |
| `row - 8` or hardcoded offsets | Breaks when structure changes | Track actual row numbers during construction |
| Deep nested IFs (>3 levels) | Unmaintainable | Named ranges + lookup tables |
| Relying on custom verification only | Misses exact test assertions | Run actual test suite incrementally |

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Extension: Complex Models

For large models (500+ rows, 10+ sheets):
- See `references/large-model-patterns.md` for memory optimization
- Use `scripts/verify_formulas.py` to audit formula consistency
- Use `scripts/verify_workbook.py` for structural checks

## Quick Reference

```python
from openpyxl import Workbook

wb = Workbook()

# Named range (CORRECT API)
wb.define_name('Rate', 'Assumptions!$B$2')

# Formula cell (no = prefix)
ws['C5'] = 'A1*B1'

# Cross-sheet formula
ws['C5'] = "IF('Roster'!A1>'Assumptions'!$B$3,'Roster'!A1,0)"

wb.save('model.xlsx')
```