---
name: excel-workbook-modeling
description: Build complex Excel workbooks with openpyxl including multi-sheet models, named ranges, cross-sheet formulas, and aggregation rows. Use for financial models, compensation calculators, or any structured workbook with formula-driven calculations.
---

# Excel Workbook Modeling with openpyxl

## When to Use
- Building financial or compensation models in Excel
- Creating workbooks with multiple interlinked sheets
- Need named ranges for formula readability
- Cross-sheet references and aggregation calculations

## Workflow

1. **Define Architecture**: List sheets in exact order. Plan column layouts and designate aggregation rows (e.g., row 107 for totals).

2. **Create Structure**: Add sheets in order, set column widths, create headers.

3. **Build Assumptions Sheet**: Place all numeric drivers here. Create named ranges for each driver.

4. **Build Data/Roster Sheets**: Populate raw data. Ensure unique IDs and exact row counts.

5. **Build Calculation Sheets**:
   - Use explicit column mapping dictionaries (e.g., `q_cols[qi]['MWS'] = col_index`).
   - Generate formulas referencing Assumptions via named ranges.
   - Add aggregation row (e.g., `=SUM(F4:F106)`) for each metric column.

6. **Build Summary Sheet**:
   - Link input drivers directly to Assumptions.
   - Link output totals to aggregation rows of calculation sheets.
   - **Critical**: Do NOT loop over quarters/years and write to same target cell. Build explicit cross-quarter sum formulas (e.g., `=Sheet!F107+Sheet!N107+...`) or target distinct columns per period.

7. **Define Named Ranges**: Use `wb.defined_names.add(DefinedName(...))`. Verify count matches expectations.

8. **Verify Programmatically**: Run `scripts/verify_xlsx.py` to confirm structure, formulas, and references before saving.

## Named Ranges API (Critical)

```python
from openpyxl.workbook.defined_name import DefinedName

# Correct: Create and add named ranges
named_range = DefinedName(name="MWS_Current", attr_text="Summary!$D$7")
wb.defined_names.add(named_range)

# Correct: Iterate existing named ranges
for name in wb.defined_names:
    print(name.name, name.attr_text)

# Wrong - these don't exist or are deprecated:
# wb.create_named_range(name, sheet, range)  # Deprecated
# wb.defined_names.localnames                # Does not exist
```

## Formula Construction Rules

- Sheet names with spaces/special chars: use single quotes `'Sheet Name'!A1`
- Python f-strings with Excel formulas: use double quotes inside formulas
- When formulas contain quotes: use `"` inside the formula string, wrap outer in single quotes or alternate quotes

```python
# Good: build separately, avoid nested f-strings
sheet_ref = "'EE Calcs (Current)'!I107"
ws['A1'] = f"={sheet_ref}-SUM(B1:D1)"

# Bad: nested f-string with backslash escaping (causes SyntaxError)
ws['A1'] = f"=IF(B1=\"text\",'Sheet'!A1,0)"  # SyntaxError

# Good: use single quotes around whole formula
ws['F4'] = '=IF(B4="Principal",D4,0)'
```

See `references/formula-patterns.md` for templates.

## Anti-Patterns & Pitfalls

| Issue | Cause | Fix |
|-------|-------|-----|
| **Loop overwrites** | `for qi in range(4):` targeting `column=3` overwrites Q1-Q3 with Q4 | Build formulas outside loop or target distinct columns per period |
| **Key mismatches** | `'Princ'` vs `'PRINC'` causes KeyError | Ensure dictionary keys exactly match strings used in formula generation |
| **Hardcoded totals** | Summary shows numbers instead of formulas | Always use `=` formulas linking to calculation sheets |
| **Deprecated named range API** | `create_named_range` removed in openpyxl 3.1 | Use `wb.defined_names.add(DefinedName(...))` |
| **Backslash in f-strings** | Python escape causes SyntaxError in formula | Use single quotes around whole formula, avoid `\"` inside f-strings |
| **Unquoted sheet names** | Spaces/parens in sheet name cause #REF? | Always quote: `'EE Calcs (Current)'!A1` |

## Verification Checklist

Before declaring completion:

1. **Sheet order**: `wb.sheetnames` matches expected list
2. **Row counts**: Check max_row for each sheet
3. **Named ranges**: Count matches expectations, iterate to confirm
4. **Formula syntax**: Load saved file, check `cell.value` for formula strings starting with `=`
5. **Cross-sheet refs**: No #REF! or #NAME? errors
6. **Aggregation rows**: Present and contain SUM formulas

Run `scripts/verify_xlsx.py` after generation.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### compensation-model
- Output must use formula references, not hardcoded values in Summary sheet
- Aggregation row positions (e.g., row 107) must match task specification
- Named range count must match expected number
