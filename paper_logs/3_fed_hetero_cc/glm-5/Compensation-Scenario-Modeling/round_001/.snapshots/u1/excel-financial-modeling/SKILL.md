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

1. **Parse Requirements**: Extract exact sheet names, order, row labels, formula types, and named ranges. Note special characters (e.g., `--->`, parentheses, arrows).
2. **Initialize & Order**: Create sheets in the exact required order. If creation order differs, use `wb.move_sheet()` immediately.
3. **Populate Static Data**: Write headers, preserved source text, and inputs exactly as specified. Do not abbreviate or rephrase labels.
4. **Define Named Ranges**: Use `wb.define_name('Name', 'Sheet!$A$1')` after populating cells.
5. **Build Formulas**: Write formulas WITHOUT leading `=` prefix. Use exact sheet names in cross-sheet references.
6. **Verify Early**: Run structural checks before finalizing. Use `scripts/verify_formulas.py` or inline checks.
7. **Run Tests**: Execute test suite before declaring success.

## Critical Rules

### Named Ranges (Most Common Failure)

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

### Formula Syntax (Second Most Common Failure)

openpyxl formulas do NOT need leading `=`:

```python
# CORRECT: No equals sign prefix
ws['K107'] = 'SUM(K2:K104)'
ws['D2'] = 'IF(Roster!E6<>"",Roster!E6+1,"")'

# WRONG: Leading = causes Excel errors
# ws['K107'] = '=SUM(K2:K104)'
```

### Exact String Matching

Tests verify exact substrings or full strings for sheet names and row labels:
- Use `Calculations --->` not `Calculations`
- Use `Y/Y` not `Year-over-Year`
- Check exact casing, punctuation, spacing

### Sheet Order

`wb.sheetnames` must match the required list exactly. Create in order or use `wb.move_sheet()`.

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

## Verification Checklist

Run before declaring complete:

- [ ] Sheet names and order match spec exactly
- [ ] All required row labels exist verbatim (check casing, punctuation)
- [ ] Named ranges defined with `wb.define_name()` (count matches spec)
- [ ] Cross-sheet formulas reference correct sheet names with quotes if needed
- [ ] Formulas have NO leading `=` prefix
- [ ] Totals rows contain `SUM(...)` or equivalent formulas
- [ ] Row count matches source data (no dropped/duplicated rows)
- [ ] Run test suite: `python -m pytest test_output.py -v`

## Anti-Patterns to Avoid

| Anti-Pattern | Why It Fails | Correct Approach |
|-------------|--------------|------------------|
| `wb.defined_names['NAME'] = ...` | AttributeError, wrong API | `wb.define_name('NAME', 'Sheet!$A$1')` |
| Formulas with `=` prefix | Excel parse errors, #NAME? | Strip leading `=`, use `'SUM(A1:A10)'` |
| Hardcoded calculated values | Model doesn't update | All outputs as formulas referencing assumptions |
| Abbreviated labels | Exact string match fails | Copy labels verbatim from spec/source |
| Deep nested IFs (>3 levels) | Unmaintainable, error-prone | Named ranges + lookup tables on Assumptions sheet |

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Named ranges not appearing | Used `wb.defined_names` dict | Use `wb.define_name()` method |
| #NAME? errors in Excel | Formula has leading `=` | Remove `=` prefix |
| Test fails on sheet names | Label mismatch (spacing, punctuation) | Compare exact strings, check for `--->` suffix |
| Missing row labels | Loop bounds or blank handling | Verify row iteration covers all source rows |
| #REF! errors | Invalid sheet reference | Quote sheet names with spaces: `'EE Calcs'!A1` |

## Fallback Strategy

If tests fail after initial build:
1. Read the test file to understand expected structure
2. Compare `wb.sheetnames` against expected order
3. Check all row labels for exact string match
4. Verify named range count: `len(wb.defined_names.definedName)`
5. Add debug output showing exactly what was written
6. Rebuild incrementally, testing after each sheet

## Known Invariants (by sub-task)

### hwpx-supplier-contact-sheet
(Reserved for future task variants)

### hwpx-clinic-intake-summary
(Reserved for future task variants)

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
- Consider `write_only=True` workbook mode for generation speed
