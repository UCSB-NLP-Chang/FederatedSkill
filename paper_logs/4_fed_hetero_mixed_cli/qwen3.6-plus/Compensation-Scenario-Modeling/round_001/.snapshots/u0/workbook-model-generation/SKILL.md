---
name: workbook-model-generation
description: Build complex formula-driven Excel workbooks using openpyxl with multi-sheet architecture, named ranges, cross-sheet formulas, and programmatic verification. Use when generating compensation models, financial calculators, or any structured workbook with formula-driven calculations.
---

# Workbook Model Generation

Build multi-sheet Excel workbooks programmatically while avoiding common pitfalls in loop logic, API compatibility, formula escaping, and verification.

## Workflow

1. **Plan sheet architecture**: List all sheets in exact order. Designate aggregation row positions (e.g., row 107 for totals). Map column layouts per sheet. Plan named ranges for key drivers.

2. **Create workbook and sheets**:
   ```python
   import openpyxl
   wb = openpyxl.Workbook()
   # Add sheets in order; delete default sheet if needed
   for name in sheet_names:
       wb.create_sheet(title=name)
   if 'Sheet' in wb.sheetnames:
       del wb['Sheet']
   ```

3. **Build Assumptions sheet**: Place all numeric drivers. Create named ranges for each driver across projection years using the API contract below.

4. **Build Data/Roster sheets**: Populate raw data. Ensure unique IDs and exact row counts match specifications.

5. **Build Calculation sheets**:
   - Use explicit column mapping dicts with exact key names: `q_cols[qi]['MWS'] = col_index`
   - Generate formulas referencing Assumptions via named ranges or absolute cell refs
   - Add aggregation row at the designated position: `ws.cell(row=107, column=c, value=f'=SUM({col_letter}4:{col_letter}106)')`

6. **Build Summary sheet**:
   - Link input drivers directly to Assumptions cells
   - Link output totals to aggregation rows in calculation sheets
   - **Critical**: Do NOT loop over quarters/periods writing to the same target cell — this overwrites Q1-Q3 with Q4. Build explicit cross-period formulas or target distinct columns per period.

7. **Define named ranges**: Use ONLY this pattern:
   ```python
   from openpyxl.workbook.defined_name import DefinedName
   dn = DefinedName(name="MWS_Current", attr_text="Assumptions!$E$5")
   wb.defined_names.add(dn)
   ```
   Never use `create_named_range` (deprecated) or `localnames` (does not exist).

8. **Verify before saving**: Run the verification script:
   ```bash
   python3 scripts/verify_workbook.py <path_to_workbook.xlsx>
   ```
   Adapt the script's constants to match the task's specific requirements. Fix all errors before proceeding.

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

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

(No sub-task invariants recorded yet. Update this section when verifier failures reveal task-specific quirks.)

## Formula patterns

See `references/formula-patterns.md` for common formula templates, string-building patterns, and escaping rules.

## Verification

Run `python3 scripts/verify_workbook.py <workbook.xlsx>` after generation. It checks:
- Sheet names and order
- Row counts per sheet
- Named range count
- Formula presence in key cells
- Cross-sheet reference validity
- Backslash artifacts in formulas

Adapt the script's constants to match the specific task requirements.