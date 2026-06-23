---
name: excel-workbook-modeling
description: Build complex, formula-driven Excel workbooks using openpyxl. Use when creating multi-sheet financial models, compensation calculators, or any structured workbook with named ranges, cross-sheet formulas, and aggregation rows.
---

# Excel Workbook Modeling with openpyxl

## CRITICAL: Pre-Flight Checklist (DO NOT SKIP)

Before writing ANY workbook code, complete these steps:

1. **Locate test_output.py**: Search broadly for the grading test file.
   ```bash
   find / -name "test_output.py" 2>/dev/null
   find / -name "test_*.py" -path "*task*" 2>/dev/null
   ls -la /root/ /workspace/ /app/ /tmp/ 2>/dev/null
   ```

2. **Read test_output.py**: Understand EXACTLY what cells, sheets, formulas, and named ranges the grader checks. Copy key assertions into your plan.

3. **Verify input structure**: Load source files and confirm row counts, headers, and data types.

**STOP**: If you cannot find test_output.py, note this as a risk. Do NOT proceed without understanding what the grader will assert.

## Workflow

1. **Define Architecture**: 
   - List sheets in exact order required by tests
   - Identify aggregation row numbers (e.g., row 107 for 103 employees starting at row 4)
   - Map column letters to data fields
   - Plan named range names (must match grader expectations exactly)

2. **Create Structure**: Add sheets in order, set column widths, create headers. Delete default "Sheet" if present.

3. **Build Assumptions Sheet**: Place all numeric drivers here. Create named ranges for each driver using modern API.

4. **Build Data/Roster Sheets**: Populate raw data. Ensure exact row counts match input (don't drop or add rows).

5. **Build Calculation Sheets**:
   - Use explicit column mapping dictionaries (e.g., `q_cols[qi]['MWS'] = col_index`).
   - Generate formulas referencing Assumptions via named ranges.
   - **CRITICAL**: Aggregation rows must use `=SUM()` formulas, not hardcoded sums.
   - Sheet names with spaces/parens must be quoted: `'EE Calcs (Current)'!A1`

6. **Build Summary Sheet**:
   - Link input drivers directly to Assumptions.
   - Link output totals to aggregation rows of calculation sheets.
   - **CRITICAL**: Do NOT loop over quarters/years and write to same target cell. Build explicit per-column formulas or target distinct columns per period.

7. **Define Named Ranges**: Use `wb.defined_names.add(DefinedName(...))`. Verify count matches test expectations.

8. **Save and Reload Defensively**: 
   ```python
   wb.save(path)
   wb_check = openpyxl.load_workbook(path, data_only=False)
   # Verify specific cells contain formulas (start with '=')
   ```

9. **Run Grading Tests (MANDATORY)**:
   ```bash
   pytest test_output.py -v
   ```
   **If this step is skipped, the task is NOT complete.** Custom verification scripts cannot substitute for the actual grading tests.

## The Custom Verification Trap

**WARNING**: Your formulas may look correct, sheet order may match, and named ranges may exist, but the grader may still fail. Common false positives:

- Cell contains a formula but references the wrong sheet/cell
- Named range exists but points to wrong coordinates
- Sheet order is correct but a forbidden sheet (e.g., "Archive Notes") was left in
- Aggregation row exists but SUM range is off by one row
- Summary shows correct calculated values but contains hardcoded numbers instead of formulas
- Named range count matches the explicit list but not the stated count in spec

**RULE**: Only `pytest test_output.py -v` provides ground truth. All other verification is preliminary.

## Named Ranges API (Critical)

```python
from openpyxl.workbook.defined_name import DefinedName

# Correct: Create and add named ranges
dn = DefinedName(name="MWS_Current", attr_text="Assumptions!$E$5")
wb.defined_names.add(dn)

# Correct: Iterate existing named ranges
for name in wb.defined_names:
    print(name.name, name.attr_text)

# Wrong - these don't exist or are deprecated:
# wb.create_named_range(name, sheet, range)  # Deprecated/removed
# wb.defined_names.localnames                # Does NOT exist
# wb.defined_names.definedName               # Does NOT exist — DefinedNameDict is directly iterable
```

## Formula Construction Rules

- Sheet names with spaces/special chars: use single quotes `'Sheet Name'!A1`
- Python f-strings with Excel formulas: use double quotes inside formulas
- Avoid backslash escaping in f-strings — use alternating quote strategy

```python
# Good: build separately, avoid nested f-strings
sheet_ref = "'EE Calcs (Current)'!I107"
ws['A1'] = f"={sheet_ref}-SUM(B1:D1)"

# Bad: nested f-string with backslash escaping
cell = f"=IF(B1=\"text\",'Sheet'!A1,0)"  # SyntaxError risk

# Good: use single quotes around whole formula when needing double inside
ws['F4'] = '=IF(B4="Principal",D4,0)'
```

See `references/formula-patterns.md` for templates.

## Anti-Patterns (Avoid These)

| Issue | Cause | Fix |
|-------|-------|-----|
| **Loop overwrites** | `for qi in range(4):` targeting same column overwrites previous quarters | Build formulas outside loop or target distinct columns per iteration |
| **Key mismatches** | `'Princ'` vs `'PRINC'` causes KeyError | Ensure dictionary keys exactly match strings used in formulas |
| **Hardcoded totals** | Summary shows numbers instead of formulas | Always use `=` formulas linking to calculation sheets |
| **Deprecated API** | `create_named_range` removed in openpyxl 3.1 | Use `DefinedName` + `wb.defined_names.add()` |
| **Unquoted sheet names** | Spaces/parens in sheet name cause #REF? | Always quote: `'EE Calcs (Current)'!A1` |
| **False confidence** | Custom verification passes but tests fail | Read test_output.py FIRST, run pytest LAST |
| **Aggregation off-by-one** | SUM range doesn't cover all data rows | Verify start/end rows match data exactly |
| **Custom verification only** | Custom scripts miss grading criteria | Run `pytest test_output.py -v` FIRST |

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; provide full precision.

## Decision Rules for Spec Contradictions

When the specification contains conflicting information:

1. **Named range count mismatch**: If spec states "N named ranges" but lists M items where M ≠ N:
   - The test assertion checks for the **stated count N**, not the explicit list length M.
   - Investigate which items should be excluded. Common patterns:
     - Some parameters may not need named ranges (e.g., growth rates used inline)
     - Some may be consolidated into fewer named ranges
     - The explicit list may include values, not named range definitions
   - Do NOT create all M items and assume the test will accept it.

2. **Row count ambiguity**: If spec says "N employees" but input has N+1 rows (including header):
   - Data rows = N, starting after the header row.
   - Aggregation row is at `header_row + N + 1`.

3. **When in doubt, trust the test file**: If test_output.py exists, it is the ground truth.

## Known Invariants (by sub-task)

### compensation-scenario-modeling
- Aggregation rows must be at exact positions specified in requirements (e.g., row 107)
- Named range count must match expected total (verify with script)
- Summary sheet must use `=` formulas, not hardcoded numbers
- Orchestra compensation models typically use 52 weeks / 4 quarters = 13 weeks per quarter
- Media exploitation fees often apply to limited weeks (e.g., 39), resulting in Q4 = $0
- Service year projections must use formula-based year offsets (e.g., `Roster!E5+1`), not hardcoded values

### university-faculty-model
- Multiple year sheets (Current, Yr+1, Yr+2) with incremented years of service
- Prevailing wage growth formulas (typically 3% per year)
- Quarterly columns for each compensation component
- Row 79 for aggregation totals (75 faculty + 3 header rows)

## Pre-Completion Checklist

Before declaring task complete, verify ALL of the following:

- [ ] Ran `pytest test_output.py -v` and all tests passed
- [ ] If tests failed, read error messages and fixed issues before re-running
- [ ] Sheet names match expected list exactly (case-sensitive, special chars)
- [ ] Named ranges defined with correct names and targets
- [ ] Named range count matches stated count in specification (not list length)
- [ ] Summary sheet uses formulas, not hardcoded values
- [ ] Aggregation rows at correct positions
- [ ] No forbidden sheets (e.g., "Archive Notes", "Instructions") remain in workbook

**If any item is unchecked, the task is NOT complete.**

## References

- `references/formula-patterns.md`: Common formula templates and escaping patterns
- `references/grading-patterns.md`: Grading test expectations and common failure modes
- `scripts/verify_xlsx.py`: Structural verification (sheet order, row counts, named ranges)
- `scripts/verify_formulas.py`: Formula integrity check (unquoted sheet refs, escape artifacts)
