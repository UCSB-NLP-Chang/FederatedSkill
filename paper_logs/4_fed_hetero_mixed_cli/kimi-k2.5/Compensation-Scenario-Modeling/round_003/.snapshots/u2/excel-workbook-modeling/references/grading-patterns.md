# Common Grading Criteria for Workbook Tasks

This document captures patterns observed in grading test suites. Read this AND `test_output.py` before building.

## Sheet Architecture Checks

- **Exact sheet names**: `wb.sheetnames == expected_list` with case-sensitive matching
- **Sheet order**: Order in `wb.sheetnames` matters, not just presence
- **Forbidden sheets**: Source sheets ("Archive Notes", "Instructions") must be explicitly removed, not just hidden
- **Navigation sheets**: Sheets named "Calculations --->" or similar are intentional and must match exactly

## Row and Column Checks

- **Header vs data rows**: If spec says "N employees", verify data occupies exactly N rows (e.g., rows 4-78 for 75 employees means aggregation at row 79)
- **Aggregation row position**: Typically at `first_data_row + employee_count`
- **Row 1 indexing**: openpyxl uses 1-indexed rows; row 4 is the 4th row (not 3rd)

## Formula Checks

- **Formula presence**: `cell.value.startswith('=')` is the common check
- **Cross-sheet references**: Summary must link to calculation sheets, not contain values
- **Year-over-Year formulas**: Growth calculations like `=(Yr2/Yr1)-1` must be formulas, not computed values
- **Service year projections**: Yr+1, Yr+2 sheets must use formulas like `='Current'!F4+1`, not hardcoded increments

## Named Range Checks

- **Exact names**: Names like `B9M_Yr1` must match exactly (case-sensitive)
- **Correct targets**: `attr_text` must resolve to correct cell (e.g., `Assumptions!$C$7`)
- **Count matters**: Graders may check the total number of named ranges. If spec says "50 named ranges" but lists 57, tests check for 50 — trust the stated count, not the list length.
- **Workbook scope**: Unless specified otherwise, ranges should be workbook-scoped
- **Modern API only**: Use `DefinedName` + `wb.defined_names.add()`. Never use deprecated `create_named_range()`.

## Value Precision Checks

- **No rounding**: Graders compare values with tolerance (often 1e-4). Do not round, format, or truncate values when writing to cells.
- **Raw floats**: Pass raw float values directly to `ws.cell(row=r, column=c, value=x)`.

## Common Failure Modes

| Test Failure | Likely Cause | Diagnostic |
|--------------|--------------|------------|
| `assert cell.value.startswith('=')` | Cell contains value, not formula | Check for `ws['A1'] = 123` instead of `ws['A1'] = "=123"` |
| Sheet name mismatch | Wrong order or extra sheets | Print `wb.sheetnames` and compare to expected |
| Row count off by 1 | Aggregation row counted as data | Verify `max_row` vs expected data rows |
| Wrong cell reference | Formula points to wrong row | Check if you used row 78 vs 79 for totals |
| Named range count | Wrong number of defined names | Count assumptions/parameters * years; trust stated count over list |
| Value precision failure | Values rounded or formatted | Pass raw floats; no `round()` or `format()` |

## The "Legacy Pytest Suite" Pattern

Some tasks use `test_legacy_pytest_suite` which runs multiple sub-checks. If this fails:
1. Look for the specific sub-test that failed in the verbose output
2. Often checks: sheet existence → row counts → formula presence → value approximations
3. Fix in order: structure → formulas → precision

## Verification Strategy

1. **Structure**: `wb.sheetnames` matches expected list exactly
2. **Data**: Row counts match (check `ws.max_row` for each sheet)
3. **Formulas**: Critical cells start with `=` (load with `data_only=False`)
4. **References**: Open in Excel or scan for `#REF!` errors
5. **Precision**: Raw floats, no rounding

Remember: Custom scripts catch ~80% of issues. Only the actual test file catches the remaining 20% (specific cell references, exact named range names, forbidden sheets).
