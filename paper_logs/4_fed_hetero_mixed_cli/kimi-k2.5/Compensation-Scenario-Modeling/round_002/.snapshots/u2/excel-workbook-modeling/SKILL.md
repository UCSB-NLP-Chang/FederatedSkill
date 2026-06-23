---
name: excel-workbook-modeling
description: Build complex Excel workbooks with openpyxl including multi-sheet models, named ranges, cross-sheet formulas, and aggregation rows. Use for financial models, compensation calculators, or any structured workbook with formula-driven calculations. Critical when task requires formula-linked outputs (not hardcoded values), specific sheet ordering, named range references, or aggregation rows.
---

# Excel Workbook Modeling with openpyxl

## When to Use
- Building financial or compensation models in Excel
- Creating workbooks with multiple interlinked sheets
- Need named ranges for formula readability
- Cross-sheet references and aggregation calculations
- Verifier requires formula-based outputs (not static values)

## Workflow

0. **Read the grading tests FIRST**: Before writing any code, read `test_output.py` to understand exactly what the grader checks. Do not assume or guess.

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

9. **Defensive Validation**: After saving, reload with `data_only=False` and inspect specific cells to ensure formulas (not values) are present.

10. **Run grading tests (CRITICAL)**: Custom verification is insufficient. Always run the task's test suite as the PRIMARY verification:
    ```bash
    pytest test_output.py -v
    ```
    If tests fail, see the Troubleshooting section below. Do NOT rely solely on custom verification scripts.

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
# wb.defined_names.definedName               # Does not exist — DefinedNameDict is directly iterable
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
| **Named range not resolving** | Range defined but not used in formulas | Verify formulas reference named ranges correctly; check for typos in range names |
| **Sheet order mismatch** | Sheets created in wrong order | Define sheet list upfront, create in that exact sequence |

## Verification Checklist

Before declaring completion:

1. **Sheet order**: `wb.sheetnames` matches expected list
2. **Row counts**: Check max_row for each sheet
3. **Named ranges**: Count matches expectations, iterate to confirm
4. **Formula syntax**: Load saved file, check `cell.value` for formula strings starting with `=`
5. **Cross-sheet refs**: No #REF! or #NAME? errors
6. **Aggregation rows**: Present and contain SUM formulas
7. **Cell type verification**: Critical cells must be formulas, not values:
   ```python
   wb_check = openpyxl.load_workbook(path, data_only=False)
   cell = wb_check['Summary']['C21']
   assert str(cell.value).startswith('='), f"Expected formula, got {cell.value}"
   ```

Run `scripts/verify_xlsx.py` and `scripts/verify_formulas.py` after generation.

**CRITICAL**: After custom verification passes, ALWAYS run `pytest test_output.py -v` to validate against actual grading criteria. See `references/grading-patterns.md` for common grading check patterns.

## Troubleshooting Verifier Failures

### When custom verification passes but grading tests fail

This is the most common failure mode. Your verify_xlsx.py passes but `pytest test_output.py` fails:

1. **Run tests with verbose output**: `pytest test_output.py -v` to see exactly which assertions fail.
2. **Read the test file**: Inspect `test_output.py` to understand what the grader actually checks. Do not guess.
3. **Check grading criteria vs your assumptions**: The grader may check:
   - Exact sheet names (case-sensitive, including special characters)
   - Specific cell references in Summary formulas (must link to exact cells)
   - Named range names and targets (must match expected names exactly)
   - Row counts (header rows vs data rows — verify where data starts)
   - Formula presence in specific cells (not just any formula, but formulas in expected locations)
4. **Common mismatches**:
   - Archive/Notes sheets should be excluded from output
   - Aggregation row position must match spec exactly
   - Summary must link to calculation sheets by formula, not hardcoded values
   - Named ranges must use modern `DefinedName` API
5. **Fix iteratively**: Run `pytest test_output.py -v` after each fix. Do not batch changes without testing.

### When formulas appear correct but verifier rejects them

1. **Check for value vs formula**: Verifiers often require formulas, not calculated values. Reload with `data_only=False` and verify `cell.value` starts with `=`.

2. **Check named range scope**: Ensure named ranges are workbook-scoped (not sheet-scoped) unless intentionally local.

3. **Check for #REF! errors**: Save, reopen in Excel or reload with openpyxl and scan for error values.

4. **Verify aggregation references**: Ensure SUM ranges cover exactly the intended rows (e.g., 5:106 for 102 employees).

5. **Check sheet name references**: Mismatches between actual sheet names and formula references cause silent failures.

6. **Test formula evaluation**: Some formulas may parse but fail in Excel. Test by opening in Excel or checking `openpyxl` formula parsing.

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
- Excluded sheets must be explicitly removed, not just hidden
- Service year projections must use formula-based year offsets (e.g., `Roster!E5+1`), not hardcoded values

## References

- `references/formula-patterns.md`: Common formula templates and escaping patterns
- `references/grading-patterns.md`: Common grading criteria patterns — read before building
- `scripts/verify_xlsx.py`: Structural verification (sheet order, row counts, named ranges, forbidden sheets)
- `scripts/verify_formulas.py`: Formula integrity check (unquoted sheet refs, escape artifacts, named range listing)