# Common Grading Criteria for Workbook Tasks

This document captures patterns observed in grading test suites for Excel workbook generation tasks. Use this to anticipate what graders check and avoid common mismatches.

## Sheet Architecture Checks

- **Exact sheet names**: Graders check `wb.sheetnames == expected_list` with exact string matching. Case-sensitive. Special characters (spaces, parens, arrows like `--->`) must match exactly.
- **Sheet order matters**: The order in `wb.sheetnames` must match the expected list exactly.
- **Excluded sheets**: Source sheets like "Archive Notes" or "Instructions" should NOT appear in the output workbook.

## Row and Column Checks

- **Header vs data rows**: Graders often count data rows excluding headers. If spec says "103 employees", verify that rows 4-106 contain employee data (103 rows), and row 107 is the aggregation row.
- **Aggregation row position**: For N employees starting at row S, aggregation is typically at row `S + N`. Common pattern: employees at rows 4-106, aggregation at row 107.
- **Column layouts**: Graders may check specific columns contain formulas vs static values.

## Formula Checks

- **Formula presence in specific cells**: Graders check `cell.value.startswith('=')` for expected cells. Ensure formulas exist in the right locations.
- **Cross-sheet references**: Summary formulas must link to calculation sheets by formula, not hardcoded values. Pattern: `='EE Calcs (Current)'!E107`
- **No backslash artifacts**: Formulas should not contain `\` escape characters. Single quotes for sheet names are valid: `'Sheet Name'!A1`
- **Aggregation formulas**: Row 107 should contain `=SUM(E4:E106)` style formulas for each calculation column.

## Named Range Checks

- **Exact names**: Graders check for specific named range names. Use the exact names specified in the task.
- **Correct targets**: Named ranges must point to the correct cells. Verify `attr_text` matches expected cell references.
- **Count matters**: Graders may check the total number of named ranges.
- **Modern API only**: Use `DefinedName` + `wb.defined_names.add()`. Never use deprecated `create_named_range()`.

## Value Precision Checks

- **No rounding**: Graders compare values with tolerance (often 1e-4). Do not round, format, or truncate values when writing to cells.
- **Raw floats**: Pass raw float values directly to `ws.cell(row=r, column=c, value=x)`.

## Year-over-Year Checks

- **Projected service years**: Yr+1 should show `source_years + 1`, Yr+2 should show `source_years + 2`.
- **Y/Y growth formulas**: Summary should contain formulas like `=(Yr1_total/Current_total)-1` for growth calculations.
- **Consistent assumptions**: Unless escalation rates are specified, assumptions (MWS, tax rates, etc.) should be identical across years.

## Common Failure Modes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Sheet order mismatch | Sheets created in wrong order or default 'Sheet' not deleted | Create sheets in exact order; delete 'Sheet' if present |
| Row count off by 1 | Header row counted as data or vice versa | Verify data starts at correct row; aggregation row is separate |
| Named range missing | Wrong API used or name typo | Use `DefinedName`; verify exact name spelling |
| Formula not found | Formula written to wrong cell or overwritten | Check loop logic; ensure no `continue` skips writes |
| Value precision failure | Values rounded or formatted | Pass raw floats; no `round()` or `format()` |
| Y/Y growth wrong | Comparing wrong cells or using hardcoded values | Build formulas linking to correct quarter totals |

## Debugging Workflow

1. Read `test_output.py` to understand exact assertions
2. Run `pytest test_output.py -v` to see failures
3. For each failure, inspect the specific cell/sheet/named range being checked
4. Fix one issue at a time; re-run tests after each fix
5. Do not rely solely on custom verification scripts - they may miss grading criteria