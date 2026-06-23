---
name: excel-workbook-modeling
description: Build complex formula-driven Excel workbooks using openpyxl with multi-sheet architecture, named ranges, cross-sheet formulas, and programmatic verification. Use when generating compensation models, financial calculators, or any structured workbook with formula-driven calculations.
---

# Excel Workbook Modeling with openpyxl

Build multi-sheet Excel workbooks programmatically while avoiding common pitfalls in loop logic, API compatibility, formula escaping, and verification.

## Workflow

1. **Read test_output.py FIRST**: Before writing any code, read the grading test file to understand exact assertions. Do not guess at requirements.

2. **Plan sheet architecture**: List all sheets in exact order. Designate aggregation row positions (e.g., row 107 for totals). Map column layouts per sheet. Plan named ranges for key drivers.

3. **Create workbook and sheets**:
   ```python
   import openpyxl
   wb = openpyxl.Workbook()
   # Add sheets in order; delete default sheet if needed
   for name in sheet_names:
       wb.create_sheet(title=name)
   if 'Sheet' in wb.sheetnames:
       del wb['Sheet']
   ```

4. **Build Assumptions sheet**: Place all numeric drivers. Create named ranges for each driver across projection years using the API contract below.

5. **Build Data/Roster sheets**: Populate raw data. Ensure unique IDs and exact row counts match specifications.

6. **Build Calculation sheets**:
   - Use explicit column mapping dicts with exact key names: `q_cols[qi]['MWS'] = col_index`
   - Generate formulas referencing Assumptions via named ranges or absolute cell refs
   - Add aggregation row at the designated position: `ws.cell(row=107, column=c, value=f'=SUM({col_letter}4:{col_letter}106)')`

7. **Build Summary sheet**:
   - Link input drivers directly to Assumptions cells
   - Link output totals to aggregation rows in calculation sheets
   - **Critical**: Do NOT loop over quarters/periods writing to the same target cell — this overwrites Q1-Q3 with Q4. Build explicit cross-period formulas or target distinct columns per period.

8. **Define named ranges**: Use ONLY this pattern:
   ```python
   from openpyxl.workbook.defined_name import DefinedName
   dn = DefinedName(name="MWS_Current", attr_text="Assumptions!$E$5")
   wb.defined_names.add(dn)
   ```
   Never use `create_named_range` (deprecated) or `localnames` (does not exist).

9. **Verify before saving**: Run the verification script:
   ```bash
   python3 scripts/verify_workbook.py <path_to_workbook.xlsx>
   ```
   Adapt the script's constants to match the task's specific requirements. Fix all errors before proceeding.

10. **Run the actual grading tests**: Custom verification is insufficient. Always run the task's test suite:
    ```bash
    pytest test_output.py -v
    ```
    If tests fail, see the Troubleshooting section below.

## Named Ranges API (Critical — WRONG vs RIGHT)

```python
from openpyxl.workbook.defined_name import DefinedName

# ✅ RIGHT: Create and add named ranges
named_range = DefinedName(name="MWS_Current", attr_text="Summary!$D$7")
wb.defined_names.add(named_range)

# ✅ RIGHT: Iterate existing named ranges
for name in wb.defined_names:
    print(name.name, name.attr_text)

# ❌ WRONG: These don't exist or are deprecated
# wb.create_named_range(name, sheet, range)  # deprecated
# wb.defined_names.localnames                # does NOT exist
# wb.defined_names.definedName               # does NOT exist — DefinedNameDict is directly iterable
```

## Anti-Patterns

- **Loop overwrites**: `for qi in range(4):` writing to `column=3` overwrites Q1-Q3 with Q4. Build formulas outside the loop or target distinct columns per period.
- **Key mismatches**: `'Princ'` vs `'PRINC'` causes `KeyError`. Ensure dictionary keys exactly match strings used in formula generation loops.
- **Hardcoded totals**: Never hardcode calculated totals in Summary. Always use `=` formula references linking to calculation sheets.
- **Backslash escaping**: Never use `\` in f-strings for Excel formulas — causes `SyntaxError`. Build formula parts separately:
  ```python
  # BAD: f"=IF(B1=\"text\",'Sheet'!A1,0)"  # escape issues
  # GOOD: build separately
  sheet_ref = "'EE Calcs (Current)'!I107"
  ws['A1'] = f"={sheet_ref}-SUM(B1:D1)"
  ```
- **Unquoted sheet names**: Sheet names with spaces, parens, or special chars MUST be single-quoted: `'EE Calcs (Current)'!A1`, not `EE Calcs (Current)!A1`.
- **Deprecated API**: Never use `wb.create_named_range()` — use `DefinedName` + `wb.defined_names.add()`.
- **Missing verification**: openpyxl silently accepts invalid formulas. Always verify before saving.
- **`continue` in loop skips subsequent writes**: If using `continue` to skip a default formula branch, ensure all required cell writes (e.g., Total = Gross + Tax) happen BEFORE the `continue` or are moved outside the conditional block.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Multi-Year Projection Patterns

When building workbooks with projected years (Yr+1, Yr+2):
- **Service year projection**: Increment years of service by 1 for each projected year. Use `source_years + year_offset`.
- **Named ranges per year**: Create separate named ranges for each year (e.g., `MWS_Current`, `MWS_Yr1`, `MWS_Yr2`).
- **Cross-sheet Y/Y formulas**: Build year-over-year growth formulas that compare totals across year sheets: `=(Yr1_total/Current_total)-1`.
- **Keep assumptions flat unless escalation rates are specified**: Do not invent annual increase rates for MWS or other drivers unless the source data provides them.

## Troubleshooting: Self-Verification Passes but Tests Fail

When your custom verification passes but `pytest test_output.py` fails:

1. **Run tests with verbose output**: `pytest test_output.py -v` to see exactly which assertions fail.
2. **Check grading criteria vs your assumptions**: The grader may check:
   - Exact sheet names (case-sensitive, including special characters like `--->`)
   - Specific cell references in Summary formulas (must link to exact EE Calcs cells)
   - Named range names and targets (must match expected names exactly)
   - Row counts (header rows vs data rows — verify where data starts)
   - Formula presence in specific cells (not just any formula, but formulas in expected locations)
3. **Inspect the test file**: Read `test_output.py` to understand what the grader actually checks. Do not guess.
4. **Common mismatches**:
   - Archive Notes sheet should be excluded from output
   - Aggregation row position must match spec (often row 107 for 103 employees + headers)
   - Summary must link to EE Calcs by formula, not hardcoded values
   - Named ranges must use modern `DefinedName` API
5. **Fix iteratively**: Run tests after each fix. Do not batch multiple changes without testing.

## Known invariants (by sub-task)

### compensation-scenario-modeling
- Orchestra compensation models typically use 52 weeks / 4 quarters = 13 weeks per quarter
- Media exploitation fees often apply to a limited number of weeks (e.g., 39 weeks), resulting in Q4 = $0
- Payroll tax brackets are annual; quarterly calculations should use cumulative approach or apply brackets proportionally
- Seniority pay is typically annual amount / 4 for quarterly calculations
- Aggregation rows must be at exact positions specified in requirements (e.g., row 107)
- Named range count must match expected total
- Summary sheet must use `=` formulas, not hardcoded numbers
- Output must use formula references, not hardcoded values in Summary sheet
- Service year projections must use formula-based year offsets (e.g., `Roster!E5+1`), not hardcoded values
- Excluded sheets like "Archive Notes" must be explicitly removed, not just hidden

## Formula patterns

See `references/formula-patterns.md` for common formula templates, string-building patterns, and escaping rules.

See `references/grading-patterns.md` for common grading criteria patterns to anticipate what tests check.

## Verification

Run `python3 scripts/verify_workbook.py <workbook.xlsx>` after generation. It checks:
- Sheet names and order
- Row counts per sheet
- Named range count
- Formula presence in key cells
- Cross-sheet reference validity
- Backslash artifacts in formulas

Run `python3 scripts/verify_formulas.py <workbook.xlsx>` for formula-specific checks:
- Unquoted sheet names with special characters
- Backslash artifacts
- Named range listing

Run `python3 scripts/verify_xlsx.py <workbook.xlsx>` for comprehensive verification:
- Forbidden sheets check
- Must-be-formula cells validation
- Error reference detection (#REF!, #NAME?)

Adapt script constants to match the specific task requirements.

**Critical**: After custom verification passes, ALWAYS run `pytest test_output.py -v` to validate against the actual grading criteria.
