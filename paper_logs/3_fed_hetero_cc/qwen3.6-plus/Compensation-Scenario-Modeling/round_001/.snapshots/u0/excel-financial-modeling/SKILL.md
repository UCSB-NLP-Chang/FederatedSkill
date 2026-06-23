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

1. **Read test file first** - Extract expected sheet names, order, and row labels from tests
2. **Parse source data** - Use openpyxl to inspect all sheets, dimensions, and data types
3. **Create sheets in exact order** - `wb.sheetnames` must match required list exactly. Use `wb.move_sheet()` if creation order differs.
4. **Populate static data** - Write headers, labels, and inputs exactly as specified. No abbreviations.
5. **Define named ranges** - Use `wb.define_name()` after cells exist
6. **Write formulas** - NO leading `=` prefix (openpyxl syntax)
7. **Verify before save** - Run test suite or verification script

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

### Principal Pay as Percentage of Base
```python
=IF(Title="Principal",MWS*0.20,IF(Title="Associate Principal",MWS*0.10,IF(Title="Assistant Principal",MWS*0.10,0)))
```

## Critical Rules

- **Exact String Matching**: Tests verify exact substrings for sheet names and row labels. Use `Calculations --->` not `Calculations`.
- **Sheet Order**: `wb.sheetnames` must match required list exactly.
- **Cross-Sheet Formulas**: Quote sheet names with spaces/special chars.
- **Data Integrity**: Row count must match source. No duplicates.
- **Named Ranges**: Define after cells exist. Verify count matches spec.

## Verification Checklist

- [ ] Sheet names and order match spec exactly
- [ ] All required row labels exist verbatim
- [ ] Cross-sheet formulas reference correct sheet names
- [ ] Totals rows contain `SUM` or equivalent formulas
- [ ] Named ranges count and targets match spec
- [ ] No dropped/duplicated rows in migrated data

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Named ranges not appearing | Wrong API used | Use `wb.define_name()`, not dict access |
| #NAME? errors in Excel | Formula has `=` prefix | Strip leading `=`, use `'SUM(A1:A10)'` |
| Test fails on sheet order | Creation order differs | Use `wb.move_sheet()` to reorder |
| Missing row labels | Casing/punctuation mismatch | Use exact strings, substring search |
| #REF! errors | Sheet name mismatch in formula | Quote names with spaces: `'EE Calcs'!A1` |

## Anti-Patterns to Avoid

| Anti-Pattern | Why It Fails | Correct Approach |
|-------------|--------------|------------------|
| `wb.defined_names['NAME'] = ...` | AttributeError, wrong API | `wb.define_name('NAME', 'Sheet!$A$1')` |
| Formulas with `=` prefix | Excel parse errors, #NAME? | Strip leading `=`, use `'SUM(A1:A10)'` |
| Hardcoded calculated values | Model doesn't update | All outputs as formulas referencing assumptions |
| Deep nested IFs (>3 levels) | Unmaintainable | Named ranges + lookup tables |

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
