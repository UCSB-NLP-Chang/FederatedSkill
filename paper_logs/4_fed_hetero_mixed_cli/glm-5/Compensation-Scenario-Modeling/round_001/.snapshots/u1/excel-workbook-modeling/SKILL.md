---
name: excel-workbook-modeling
description: Build complex, formula-driven Excel workbooks using openpyxl. Use when creating multi-sheet financial models, compensation calculators, or any structured workbook with named ranges, cross-sheet formulas, and aggregation rows.
---

# Excel Workbook Modeling with openpyxl

## When to Use

- Building financial or compensation models in Excel
- Creating workbooks with multiple interlinked sheets
- Need named ranges for formula readability
- Cross-sheet references and aggregation formulas
- Multi-period projections (quarters, years)

## Workflow

1. **Define Architecture**: List sheets in exact order. Plan column layouts and designate aggregation rows (e.g., row 107 for totals).
2. **Build Assumptions Sheet**: Place all numeric drivers here. Create named ranges for each driver.
3. **Build Data/Roster Sheets**: Populate raw data. Ensure unique IDs and exact row counts.
4. **Build Calculation Sheets**:
   - Use explicit column mapping dictionaries (e.g., `q_cols[qi]['MWS'] = col_index`).
   - Generate formulas referencing Assumptions via named ranges.
   - Add a final aggregation row (e.g., `=SUM(F4:F106)`) for each metric column.
5. **Build Summary Sheet**:
   - Link input drivers directly to Assumptions.
   - Link output totals to the aggregation rows of calculation sheets.
   - **Critical**: Do NOT loop over quarters/years and write to the same target cell. Build explicit cross-quarter formulas or target distinct columns per period.
6. **Define Named Ranges**: Use `wb.defined_names.add(DefinedName(...))` pattern. Verify count matches expectations.
7. **Verify Structure**: Run verification scripts before declaring completion.

## Named Ranges API (Critical)

```python
from openpyxl.workbook.defined_name import DefinedName

# Correct: Create and add named ranges
named_range = DefinedName(name="MWS_Current", attr_text="Summary!$D$7")
wb.defined_names.add(named_range)

# Correct: Iterate existing named ranges
for name in wb.defined_names:
    print(name.name, name.attr_text)

# Wrong - these are deprecated or don't exist:
# wb.create_named_range(name, sheet, range)  # deprecated
# wb.defined_names.localnames                # does not exist
```

## Formula Construction Rules

- Sheet names with spaces/special chars: use single quotes `'Sheet Name'!A1`
- Build formulas outside f-strings when possible to avoid escaping issues
- Never use backslash escaping in f-strings for Excel formulas

```python
# Bad: nested f-string with escape issues
ws['A1'] = f"=IF(B1=\"text\",'Sheet'!A1,0)"

# Good: build separately
sheet_ref = "'EE Calcs (Current)'!I107"
ws['A1'] = f"={sheet_ref}-SUM(B1:D1)"

# Good: IF with text - single quotes around formula, double quotes inside
ws['F4'] = '=IF(B4="Principal",D4,0)'
```

## Anti-Patterns (Avoid These)

- **Loop Overwrites**: Writing summary formulas inside `for qi in range(4):` that targets `column=3` overwrites Q1-Q3 with Q4. Build formulas outside the loop or target distinct columns.
- **Key Mismatches**: Dictionary keys for column headers must exactly match strings used in formula loops. `'Princ'` vs `'PRINC'` causes KeyError.
- **Hardcoded Totals**: Never hardcode calculated totals in Summary. Always use `=` formulas linking to calculation sheets.
- **Missing Verification**: openpyxl silently accepts invalid formula syntax. Always verify.
- **Backslash Escaping**: `\` in Python f-strings causes `SyntaxError` in formula context.

## Verification Checklist

Before claiming completion:

1. **Sheet order**: `wb.sheetnames` matches expected list
2. **Formula syntax**: Load saved file and check `cell.value` for formula strings starting with `=`
3. **Named ranges**: Iterate and confirm all defined with correct count
4. **Data integrity**: Count rows, check for dropped/duplicated data
5. **Cross-sheet refs**: Verify sheet names quoted properly when containing spaces/parens

Run `scripts/verify_xlsx.py` and `scripts/verify_formulas.py` after generation. Adapt script constants to task requirements.

## Known Invariants (by sub-task)

### compensation-scenario-modeling
- Aggregation rows must be at exact positions specified in requirements (e.g., row 107)
- Named range count must match expected total (verify with script)
- Summary sheet must use `=` formulas, not hardcoded numbers

## References

- `references/formula-patterns.md`: Common formula templates and escaping patterns
- `scripts/verify_xlsx.py`: Structural verification (sheet order, row counts, named ranges)
- `scripts/verify_formulas.py`: Formula integrity check (unquoted sheet refs, escape artifacts)