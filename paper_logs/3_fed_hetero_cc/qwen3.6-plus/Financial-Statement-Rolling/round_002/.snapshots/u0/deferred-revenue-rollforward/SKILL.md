---
name: deferred-revenue-rollforward
description: Build multi-sheet Excel rollforward workbooks (deferred revenue or accrual) from CSV schedules and GL balance data. Use when the task involves creating a .xlsx with detail sheets per account and a summary sheet, including control rows (Period Totals, Ending Balance, Variance, GL Balance) with live Excel formulas. Covers both deferred revenue (Billings/Recognition) and accrual (Accruals/Releases) variants.
---

# Rollforward Workbook Builder

## When to Use
- Task asks for a deferred revenue rollforward, accrual rollforward, waterfall, or schedule workbook
- Source data is CSV schedules (per account) plus GL balances (JSON or CSV)
- Output must be a multi-sheet Excel file with formulas, not just static values

## Workflow

1. **Read all source files** first — CSV schedules and GL balance data.
2. **Extract the exact expected file name** from the task description. Do not guess.
3. **Extract the exact summary sheet cell map** from the spec before writing code. The summary sheet has rigid cell positions (e.g., B7, B8, B9, B12, B13, B14, B16). Write down the mapping explicitly.
4. **Plan the sheet structure**:
   - Summary sheet first, then one detail sheet per account
   - Detail sheet column order varies by variant (see References below)
5. **Build with openpyxl** — see `scripts/build_rollforward.py` for a working skeleton.
6. **Run the test suite immediately** after saving — do not rely on manual spot-checks.

## Spec-Driven Summary Sheet

The summary sheet is the most common failure point. Agents frequently guess row positions and get them wrong.

**Rule**: Parse the spec for explicit cell references (e.g., "B7 = link to Payroll totals", "B16 = B9 + B14"). Build a mapping table before coding:

```
B7  → ='Payroll Accrual #2105'!L9   (Period Totals)
B8  → ='Payroll Accrual #2105'!L10  (Ending Balance)
B9  → ='Payroll Accrual #2105'!L12  (GL Balance)
B12 → ='Bonus Accrual #2110'!L9
B13 → ='Bonus Accrual #2110'!L10
B14 → ='Bonus Accrual #2110'!L12
B16 → =B9+B14                       (Combined)
```

**Anti-pattern**: Building the summary sheet with guessed row positions and then patching cells afterward. This introduces off-by-one errors and formula reference bugs.

**Correct pattern**: Write the summary sheet in a single pass using the extracted cell map. Verify row positions match the spec before saving.

## Critical Formula Patterns

### Ending Balance (the most common bug)
Each month's Ending Balance must chain from the **previous month's Ending Balance**, not from an empty cell in the same row.

**Anti-pattern**: Writing `=B11+C11-D11` where B11 is the Beginning Balance column of the Ending Balance *control row* (which is empty/0).

**Correct pattern**: Set the Ending Balance control row's Beginning Balance to reference Period Totals: `B_ending = B_totals`. Then each month's Ending Balance formula uses the Ending Balance row for prior month and Period Totals row for current month activity.

### Variance
Variance = GL Balance − Ending Balance (for the final period). Zero means books balance.
Formula: `=L{gl_row}-K{ending_row}` for 3-month rollforwards, or `=N{gl_row}-N{ending_row}` for 4-month.

### Period Totals
Simple SUM of line-item columns above. Use `=SUM(B6:B9)` style formulas.

### GL Balance Row
Hardcode the GL values from the source JSON into the ending-balance columns. The L (or O) column can be a formula: `=L{totals}-L{ending}`.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs.
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- Apply `#,##0.00` number_format to all monetary cells including formula cells.

## Verification Steps

1. **Run the test suite first**: `pytest test_output.py -v` — do not skip this.
2. **Run `python3 scripts/verify_workbook.py <path>`** — automated check for sheet order, formula presence, and number formatting.
3. **Open the file with openpyxl and read back every formula cell** — confirm the formula text is correct.
4. **Manually compute expected values** for Period Totals, Ending Balance, and Variance from the raw CSV data.
5. **Confirm Variance = 0** for every account.
6. **Check sheet order** matches the requirement exactly.
7. **Check file name** matches the expected pattern.

## Known invariants (by sub-task)

### deferred-revenue-rollforward
- Output must use live Excel formulas (not hardcoded values) in control rows.
- Cross-sheet references require single quotes for sheet names with spaces/special chars: `='SaaS Rev #2300'!O10`.
- Sheet names must match source account names exactly.
- Number format `#,##0.00` must be applied to all monetary cells including formula cells.

### accrual-rollforward
- Same control-row formula invariants apply as deferred-revenue (see `references/accrual_variant.md` for column layout differences).
- Activity columns use "Accruals/Releases" instead of "Billings/Recognition".
- Summary sheet often includes a "Combined GL Balance" row (e.g., `B16 = B9 + B14`).

## Common Pitfalls
- **Self-referencing control rows**: Ending Balance control row referencing its own empty Beginning Balance cell.
- **Wrong Variance sign**: Variance should be GL minus Ending Balance.
- **Hardcoded values where formulas are expected**: Tests check for formula strings starting with `=`.
- **Missing cross-sheet references on Summary**: Summary sheet should link to detail sheets with formulas, not hardcoded values.
- **File name mismatch**: Extract the exact filename from the task description.
- **Sheet name mismatch**: Use exact names from source data.
- **Missing number formatting on formula cells**: Apply `#,##0.00` to every monetary cell.
- **Summary sheet row misalignment**: Spec gives exact cell positions; do not guess.

## Fallback Strategy

If the verifier or test suite fails:
1. Read the test file (`test_output.py`) to understand exact expectations.
2. Compare expected sheet names, column headers, row positions, and formula patterns.
3. Rebuild with adjusted structure — do not try to patch individual cells.
4. If openpyxl formulas don't evaluate as expected, check whether the test uses a formula evaluator that requires specific function syntax.

## References

- See `references/rollforward_anatomy.md` for the standard deferred revenue detail sheet layout.
- See `references/accrual_variant.md` for accrual-specific column headers and layout differences.