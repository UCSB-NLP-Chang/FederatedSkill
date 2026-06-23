---
name: deferred-revenue-rollforward
description: Build a deferred revenue rollforward workbook (Excel) from CSV schedules and GL balance data. Use when the task involves creating a multi-sheet .xlsx with detail sheets per revenue account and a summary sheet, including control rows (Period Totals, Ending Balance, Variance, GL Balance) with live Excel formulas.
---

# Deferred Revenue Rollforward Workbook

## When to Use
- Task asks for a deferred revenue rollforward, waterfall, or schedule workbook
- Source data is CSV schedules (per account) plus GL balances (JSON or CSV)
- Output must be a multi-sheet Excel file with formulas, not just static values

## Workflow

1. **Read all source files** first — CSV schedules and GL balance data.
2. **Determine the exact expected file name** from the task description. Do not guess; look for patterns like `CompanyName_Deferred_Revenue_MM-YY.xlsx`.
3. **Plan the sheet structure** before writing code:
   - Summary sheet first, then one detail sheet per revenue account
   - Detail sheet column order: Customer, Beginning Balance, then for each month: Billings, Recognition, Ending Balance, then Contract Months, Notes, Revenue Code
4. **Build with openpyxl** — see `scripts/build_rollforward.py` for a working skeleton.
5. **Validate formulas** before declaring success — see Verification below.

## Critical Formula Patterns

### Ending Balance (the most common bug)
Each month's Ending Balance must chain from the **previous month's Ending Balance**, not from an empty cell in the same row.

| Row | May Ending | Jun Ending | Jul Ending | Aug Ending |
|-----|-----------|-----------|-----------|------------|
| Line item | `=B+C-D` (BegBal+Billings-Recognition) | `=E+F-G` (MayEnd+Billings-Recognition) | `=H+I-J` | `=K+L-M` |
| **Ending Balance control** | `=B_ctrl+C_ctrl-D_ctrl` | `=E_ctrl+F_ctrl-G_ctrl` | `=H_ctrl+I_ctrl-J_ctrl` | `=K_ctrl+L_ctrl-M_ctrl` |

**Anti-pattern**: Writing `=B11+C11-D11` where B11 is the Beginning Balance column of the Ending Balance *control row* (which is empty/0). The Beginning Balance for the control row's May calculation must come from the sum of line-item beginning balances, not from the control row's own column B.

**Correct pattern**: Set the Ending Balance control row's Beginning Balance to reference Period Totals: `B_ending = B_totals` (e.g., `=B10`). Then each month's Ending Balance formula uses the Ending Balance row for prior month and Period Totals row for current month activity:
- May: `=B{ending}+C{totals}-D{totals}`
- Jun: `=E{ending}+F{totals}-G{totals}`
- Jul: `=H{ending}+I{totals}-J{totals}`
- Aug: `=K{ending}+L{totals}-M{totals}`

### Variance
Variance = GL Balance − Ending Balance (for the final period). Zero means books balance.
Formula: `=N{gl_row}-N{ending_row}` where N_gl is the GL Balance value and N_ending is the Ending Balance value for the same period.

### Period Totals
Simple SUM of line-item columns above. Use `=SUM(B6:B9)` style formulas.

### GL Balance Row
Hardcode the GL values from the source JSON into the ending-balance columns (E, H, K, N). The O column can be a formula or the Aug GL value.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.
- Apply `#,##0.00` number_format to all monetary cells including formula cells.

## Verification Steps

After creating the workbook, **always** run these checks:

1. **Run `python3 scripts/verify_workbook.py <path>`** — automated check for sheet order, formula presence, and number formatting.
2. **Open the file with openpyxl and read back every formula cell** — confirm the formula text is correct, not just that the cell is non-empty.
3. **Manually compute expected values** for Period Totals, Ending Balance, and Variance from the raw CSV data and compare.
4. **Confirm Variance = 0** for every account — if not, the rollforward formulas are wrong.
5. **Check sheet order** matches the requirement exactly.
6. **Check file name** matches the expected pattern.
7. **If a test suite exists**, run it before finishing. Do not assume manual spot-checks are sufficient.

## Known invariants (by sub-task)

### deferred-revenue-rollforward
- Output must use live Excel formulas (not hardcoded values) in control rows — verifier checks for formula strings starting with `=`.
- Cross-sheet references require single quotes for sheet names with spaces/special chars: `='SaaS Rev #2300'!O10`.
- Sheet names must match source account names exactly (e.g., "SaaS Rev #2300" not "SaaS Rev 2300").
- Number format `#,##0.00` must be applied to all monetary cells including formula cells.

## Common Pitfalls

- **Self-referencing control rows**: Ending Balance control row referencing its own empty Beginning Balance cell instead of the Period Totals row.
- **Wrong Variance sign**: Variance should be GL minus Ending Balance. Must produce 0 when books balance.
- **Hardcoded values where formulas are expected**: Tests often check that cells contain formulas (e.g., `=SUM(...)`) not static numbers.
- **Missing cross-sheet references on Summary**: Summary sheet should link to detail sheets with formulas like `='SaaS Rev #2300'!N11`, not hardcoded values.
- **File name mismatch**: The test may expect a specific filename pattern. Extract it from the task description carefully.
- **Sheet name mismatch**: Use exact names like `SaaS Rev #2300` not `SaaS Rev 2300` or `SaaS #2300`.
- **Missing number formatting on formula cells**: Apply `#,##0.00` to every monetary cell, including those containing formulas.

## Fallback Strategy

If the verifier fails after building the workbook:
1. Read the test file (`test_output.py`) to understand exact expectations.
2. Compare expected sheet names, column headers, row positions, and formula patterns.
3. Rebuild with adjusted structure — do not try to patch individual cells.
4. If openpyxl formulas don't evaluate as expected, consider whether the test uses a formula evaluator that requires specific function syntax.

## References

- See `references/rollforward_anatomy.md` for a detailed layout diagram of a typical detail sheet.
