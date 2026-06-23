# Common Grading Criteria for Workbook Tasks

This document captures patterns observed in grading test suites. Read this AND `test_output.py` before building.

## Sheet Architecture Checks

- **Exact sheet names**: `wb.sheetnames == expected_list` with case-sensitive matching. Special characters (spaces, parens, arrows like `--->`) must match exactly.
- **Sheet order**: Order in `wb.sheetnames` matters, not just presence.
- **Forbidden sheets**: Source sheets ("Archive Notes", "Instructions") must be explicitly removed, not just hidden.
- **Navigation sheets**: Sheets named "Calculations --->" or similar are intentional and must match exactly.

## Row and Column Checks

- **Header vs data rows**: Graders often count data rows excluding headers. If spec says "103 employees", verify that rows 4-106 contain employee data (103 rows), and row 107 is the aggregation row.
- **Aggregation row position**: For N employees starting at row S, aggregation is typically at row `S + N`. Common pattern: employees at rows 4-106, aggregation at row 107.
- **Row 1 indexing**: openpyxl uses 1-indexed rows; row 4 is the 4th row (not 3rd).
- **Column layouts**: Graders may check specific columns contain formulas vs static values.

## Formula Checks

- **Formula presence**: `cell.value.startswith('=')` is the common check. Ensure formulas exist in the right locations.
- **Cross-sheet references**: Summary formulas must link to calculation sheets by formula, not hardcoded values. Pattern: `='EE Calcs (Current)'!E107`
- **Year-over-Year formulas**: Growth calculations like `=(Yr2/Yr1)-1` must be formulas, not computed values.
- **Service year projections**: Yr+1, Yr+2 sheets must use formulas like `='Current'!F4+1`, not hardcoded increments.
- **No backslash artifacts**: Formulas should not contain `\` escape characters. Single quotes for sheet names are valid: `'Sheet Name'!A1`.
- **Aggregation formulas**: Row 107 should contain `=SUM(E4:E106)` style formulas for each calculation column.

## Named Range Checks

- **Exact names**: Graders check for specific named range names. Use the exact names specified in the task (case-sensitive).
- **Correct targets**: Named ranges must point to the correct cells. Verify `attr_text` matches expected cell references.
- **Count matters**: Graders may check the total number of named ranges. If spec says "50 named ranges" but lists 57 items, trust the stated count (50), not the list length.
- **Modern API only**: Use `DefinedName` + `wb.defined_names.add()`. Never use deprecated `create_named_range()`.
- **Workbook scope**: Unless specified otherwise, ranges should be workbook-scoped.

## Value Precision Checks

- **No rounding**: Graders compare values with tolerance (often 1e-4). Do not round, format, or truncate values when writing to cells.
- **Raw floats**: Pass raw float values directly to `ws.cell(row=r, column=c, value=x)`.
- **Y/Y growth formulas**: Summary should contain formulas like `=(Yr1_total/Current_total)-1` for growth calculations.
- **Consistent assumptions**: Unless escalation rates are specified, assumptions (MWS, tax rates, etc.) should be identical across years.

## Common Failure Modes

| Test Failure | Likely Cause | Diagnostic |
|--------------|--------------|------------|
| `assert cell.value.startswith('=')` | Cell contains value, not formula | Check for `ws['A1'] = 123` instead of `ws['A1'] = "=123"` |
| Sheet name mismatch | Wrong order or extra sheets | Print `wb.sheetnames` and compare to expected |
| Row count off by 1 | Aggregation row counted as data | Verify `max_row` vs expected data rows |
| Wrong cell reference | Formula points to wrong row | Check if you used row 78 vs 79 for totals |
| Named range count mismatch | Created all listed items vs stated count | Trust stated count N, not list length M |
| Named range missing | Wrong API used or name typo | Use `DefinedName`; verify exact name spelling |
| Formula not found | Formula written to wrong cell or overwritten | Check loop logic; ensure no `continue` skips writes |
| Value precision failure | Values rounded or formatted | Pass raw floats; no `round()` or `format()` |
| Y/Y growth wrong | Comparing wrong cells or using hardcoded values | Build formulas linking to correct quarter totals |
| Tests pass in custom verification but fail grading | Custom scripts miss grading criteria | Run `pytest test_output.py -v` FIRST |

## The "Legacy Pytest Suite" Pattern

Some tasks use `test_legacy_pytest_suite` which runs multiple sub-checks. If this fails:
1. Look for the specific sub-test that failed in the verbose output
2. Often checks: sheet existence → row counts → formula presence → value approximations
3. Fix in order: structure → formulas → precision

## Verification Strategy

**CRITICAL ORDER**:
1. **Run `pytest test_output.py -v` FIRST** - This is the authoritative check. Do NOT skip.
2. Read test output to understand exact assertions that failed
3. **Structure**: `wb.sheetnames` matches expected list exactly
4. **Data**: Row counts match (check `ws.max_row` for each sheet)
5. **Formulas**: Critical cells start with `=` (load with `data_only=False`)
6. **References**: Open in Excel or scan for `#REF!` errors
7. **Precision**: Raw floats, no rounding

**Remember**: Custom scripts catch ~80% of issues. Only the actual test file catches the remaining 20% (specific cell references, exact named range names, forbidden sheets, named range count vs list length).

## Critical Reminder

**Never declare task completion without running `pytest test_output.py -v` and seeing all tests pass.** Custom verification scripts are helpful for development but cannot replace the actual grading tests. The grader checks specific criteria that may not be obvious from the task description.

## Debugging Workflow

1. **Run `pytest test_output.py -v` FIRST** - This is the authoritative check.
2. Read test output to understand exact assertions that failed
3. For each failure, inspect the specific cell/sheet/named range being checked
4. Fix one issue at a time; re-run tests after each fix
5. Do not rely solely on custom verification scripts - they may miss grading criteria
6. If tests fail with cryptic errors, load the workbook in openpyxl and inspect the specific cells mentioned

## Handling Verification Script Failures

When `scripts/verify_xlsx.py` or `scripts/verify_formulas.py` fails:

1. **Do NOT dismiss as false positive** without investigation
2. Check if you updated the EXPECTED_* constants for your task:
   ```python
   EXPECTED_SHEETS = ["Your", "Sheet", "Names"]
   EXPECTED_ROWS = {"SheetName": expected_count}
   EXPECTED_NAMED_RANGES = your_count
   ```
3. If constants are wrong, update them and re-run
4. If constants are correct, the failure indicates a real issue - investigate and fix
5. Even after verification passes, you MUST still run `pytest test_output.py -v`

**Common false positive trap**: An agent may pass custom verification but fail the actual grading test because the verification script constants were not updated for the specific task. Always verify the script's expectations match your task.