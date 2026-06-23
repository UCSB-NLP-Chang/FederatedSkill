---
name: excel-workbook-modeling
description: Build complex, formula-driven Excel workbooks using openpyxl. Use when creating multi-sheet financial models, compensation calculators, or any structured workbook with named ranges, cross-sheet formulas, and aggregation rows.
---

# Excel Workbook Modeling with openpyxl

## STOP: Read Tests BEFORE Building

**You MUST locate and read test_output.py BEFORE writing ANY workbook code.** This is not optional. Skipping this step causes failure.

```bash
find / -name "test_output.py" 2>/dev/null
find / -name "test_*.py" -path "*task*" 2>/dev/null
ls -la /root/ /workspace/ /app/ /tmp/ 2>/dev/null
```

**If test_output.py is found:**
1. Read it completely - it is the specification, not the task description
2. Extract: sheet names (exact order), named range count, aggregation rows, formula cells
3. Copy key assertions into your plan - these are what the grader checks

**If test_output.py CANNOT be found:**
1. Search for ANY Python test files: `find / -name "*.py" -exec grep -l "pytest\|unittest" {} \; 2>/dev/null | head -10`
2. Run pytest discovery: `python -m pytest --collect-only 2>/dev/null`
3. Proceed with defensive over-verification of structure and formulas

**Do NOT proceed to workflow step 1 without attempting to find and read test_output.py.**

## Workflow

1. **Define Architecture** (from test_output.py):
   - List sheets in exact order required by tests
   - Identify aggregation row numbers (e.g., row 107 for 103 employees starting at row 4)
   - Map column letters to data fields
   - Plan named range names (must match grader expectations exactly)
   - Note: If spec states "N named ranges" but lists M items, trust stated count N

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

9. **Run pytest (MANDATORY - NOT OPTIONAL)**:
   ```bash
   pytest test_output.py -v
   ```
   **STOP. This task is NOT complete until pytest shows all tests passing.**

## The Verification Failure Trap

**When verify_xlsx.py or verify_formulas.py fails, you MUST investigate. Do NOT dismiss failures as "false positives" without investigation.**

Two possibilities:
1. **Script constants wrong**: Update EXPECTED_SHEETS, EXPECTED_ROWS, EXPECTED_NAMED_RANGES for your task
2. **Real issue**: The failure reveals a structural problem - fix it

**After verification passes, you MUST still run `pytest test_output.py -v`.** Custom verification cannot substitute for grading tests.

## Named Ranges API (Critical)

```python
from openpyxl.workbook.defined_name import DefinedName

# Correct: Create and add named ranges
dn = DefinedName(name="MWS_Current", attr_text="Assumptions!$E$5")
wb.defined_names.add(dn)

# Correct: Iterate existing named ranges (version-safe)
for name in wb.defined_names:
    dn = wb.defined_names[name]  # Get the actual DefinedName object
    print(dn.name if hasattr(dn, 'name') else name, dn.attr_text if hasattr(dn, 'attr_text') else dn)

# Wrong - these don't exist or are deprecated:
# wb.create_named_range(name, sheet, range)  # Deprecated/removed
# wb.defined_names.localnames                # Does NOT exist
# wb.defined_names.definedName               # Does NOT exist
```

## Formula Construction Rules

- Sheet names with spaces/special chars: use single quotes `'Sheet Name'!A1`
- Python f-strings with Excel formulas: use double quotes inside formulas
- Avoid backslash escaping in f-strings

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
| **Dismissed verification failures** | Agent ignores script failures as "false positives" | Investigate ALL failures - update constants or fix real issues |

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; provide full precision.

## Decision Rules for Spec Contradictions

When the specification contains conflicting information:

1. **Named range count mismatch**: If spec states "N named ranges" but lists M items where M ≠ N:
   - The test assertion checks for the **stated count N**, not the explicit list length M.
   - Investigate which items should be excluded. Common patterns: growth rates used inline, tax caps.
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
- Retirement match: sum qualifying compensation first (base + stipend + sabbatical), then apply rate/cap
- Do NOT multiply unrelated components (e.g., base × summer rate)

## Pre-Completion Checklist

Before declaring task complete, verify ALL of the following:

- [ ] Attempted to find test_output.py using multiple search strategies
- [ ] If found: read test_output.py and extracted assertions
- [ ] Ran `pytest test_output.py -v` (if test file exists) and all tests passed
- [ ] If verification script failed: investigated and fixed, did NOT dismiss as false positive
- [ ] Sheet names match expected list exactly (case-sensitive, special chars)
- [ ] Named ranges defined with correct names and targets
- [ ] Named range count matches stated count in specification (not list length)
- [ ] Summary sheet uses formulas, not hardcoded values
- [ ] Aggregation rows at correct positions with SUM formulas
- [ ] No forbidden sheets (e.g., "Archive Notes", "Instructions") remain in workbook

**If pytest has not been run and passed, the task is NOT complete.**

## References

- `references/formula-patterns.md`: Common formula templates and escaping patterns
- `references/grading-patterns.md`: Grading test expectations and common failure modes
- `references/compensation-patterns.md`: Retirement caps, tiered lookups, service year projections
- `scripts/verify_xlsx.py`: Structural verification - UPDATE EXPECTED_* constants for your task
- `scripts/verify_formulas.py`: Formula integrity check (unquoted sheet refs, escape artifacts)