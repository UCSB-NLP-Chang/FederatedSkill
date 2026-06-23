---
name: deferred-revenue-rollforward
description: Build multi-sheet Excel rollforward workbooks (deferred revenue, accrual, or warranty reserve) from CSV schedules and GL balance data. Use when the task involves creating a .xlsx with detail sheets per account and a summary sheet, including control rows (Period Totals, Ending Balance, Variance, GL Balance) with live Excel formulas. Covers deferred revenue (Billings/Recognition), accrual (Accruals/Releases), and warranty reserve variants.
---

# Rollforward Workbook Builder

## Mandatory Pre-Coding Checklist

**Do not write any workbook code until you complete these steps:**

1. **Read all source files** — CSV schedules, GL balance data, and account mapping JSON if present.
2. **Filter source data**: If CSV has `record_status` column, filter to `active` only (exclude archived/placeholder records).
3. **Extract the exact expected file name** from the task description. Do not guess.
4. **Extract the exact summary sheet cell map** from the spec. Write it down as a table before coding:
   ```
   B7  → ='Account Name'!O{pt_row}   (Period Totals)
   B8  → ='Account Name'!O{eb_row}   (Ending Balance)
   B9  → ='Account Name'!O{gl_row}   (GL Balance)
   B12 → ='Account2 Name'!O{pt_row}
   ...
   B16 → =B9+B14                     (Combined GL)
   ```
5. **Identify the variant** (deferred revenue, accrual, or warranty reserve) and load the correct reference layout.
6. **Start from `scripts/build_rollforward.py`** — adapt it rather than writing from scratch. The skeleton already has the correct Ending Balance and Variance formula patterns.

## Critical Formula Patterns (MUST GET RIGHT)

### Ending Balance — STOP AND VERIFY THIS FIRST

**Decision rule**: If you are writing an Ending Balance control row, its Beginning Balance cell MUST reference the Period Totals Beginning Balance cell, NOT be left empty.

**WRONG** (self-referencing — the #1 bug across all rounds):
```
Row 11 (Ending Balance): B11 is empty, E11 = =B11+C11-D11  → computes 0 + C - D
```

**RIGHT** (chain from Period Totals):
```
Row 10 (Period Totals): B10 = =SUM(B6:B9)
Row 11 (Ending Balance): B11 = =B10, E11 = =B11+C10-D10  → correctly rolls forward
```

**Before writing any control row code, verify**: the Ending Balance row's Beginning Balance cell references the Period Totals row, not its own empty cell.

**Note on alternative patterns**: Some specs use self-contained SUM formulas (Ending Balance row has `=SUM(B6:B8)` in its own input columns so each cell has a value). Only use this pattern if the spec explicitly shows it. Default to referencing Period Totals.

### Variance
Variance = GL Balance − Ending Balance (for the final period). Zero means books balance.

**WRONG**: `=O13-N13` (comparing two GL row cells)
**RIGHT**: `=N{gl_row}-N{ending_row}` (GL final period minus Ending Balance final period)

For 3-month rollforwards: `=N{gl_row}-N{ending_row}`
For 4-month rollforwards: `=N{gl_row}-N{ending_row}` (same pattern, different column)

### Period Totals
Simple SUM of line-item columns above. Use `=SUM(B6:B9)` style formulas.

### GL Balance Row
Hardcode the GL values from the source JSON into the ending-balance columns. The total column can be a formula: `=O{totals}-O{ending}`.

## Data Filtering

**Active Records Only**: Many source CSVs include archived or placeholder records (e.g., `record_status=archived`). Always filter these out before building the workbook:

```python
active_rows = [r for r in csv_data if r.get("record_status") == "active"]
```

If an account mapping JSON is provided (e.g., `reserve_account_map.json`), use it to map buckets/codes to sheet names.

## Spec-Driven Summary Sheet

The summary sheet is the most common failure point. Agents frequently guess row positions and get them wrong.

**Rule**: Parse the spec for explicit cell references (e.g., "B7 = link to Payroll totals", "B16 = B9 + B14"). Build a mapping table before coding.

**Anti-pattern**: Building the summary sheet with guessed row positions and then patching cells afterward. This introduces off-by-one errors and formula reference bugs.

**Correct pattern**: Write the summary sheet in a single pass using the extracted cell map. Verify row positions match the spec before saving.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.
- Apply `#,##0.00` number_format to all monetary cells including formula cells.

## Verification Steps

1. **Run the test suite first**: `pytest test_output.py -v` — do not skip this.
2. **Run `python3 scripts/verify_workbook.py <path>`** — automated check for sheet order, formula presence, and number formatting.
3. **Open the file with openpyxl and read back every formula cell** — confirm the formula text is correct.
4. **Manually compute expected values** for Period Totals, Ending Balance, and Variance from the raw CSV data.
5. **Confirm Variance = 0** for every account.
6. **Check sheet order** matches the requirement exactly.
7. **Check file name** matches the expected pattern.
8. **Verify no archived records** appear in the output.

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

### warranty-reserve
- Variant of accrual rollforward. Uses "Accruals/Claims Paid" or "Incurred/Paid" terminology.
- 4-month structure (vs 3-month for standard accrual).
- Coverage Months instead of Reserve Months; Reserve Account instead of Department Code.
- Must filter out archived records (`record_status != "active"`) before building.
- Account mapping JSON may determine sheet names — use it rather than hardcoding.
- See `references/warranty_reserve_variant.md` for detailed warranty handling.

## Common Pitfalls
- **Self-referencing control rows**: Ending Balance control row referencing its own empty Beginning Balance cell. This is the #1 bug. Verify B_ending = B_totals.
- **Wrong Variance sign or wrong cells**: Variance should be GL minus Ending Balance for the final period column.
- **Hardcoded values where formulas are expected**: Tests check for formula strings starting with `=`.
- **Missing cross-sheet references on Summary**: Summary sheet should link to detail sheets with formulas, not hardcoded values.
- **File name mismatch**: Extract the exact filename from the task description.
- **Sheet name mismatch**: Use exact names from source data or account mapping JSON.
- **Missing number formatting on formula cells**: Apply `#,##0.00` to every monetary cell.
- **Summary sheet row misalignment**: Spec gives exact cell positions; do not guess.
- **Writing from scratch instead of using the skeleton**: `scripts/build_rollforward.py` already has correct formula patterns. Adapt it.
- **Including archived records**: Filter out non-active records before processing.

## Fallback Strategy

If the verifier or test suite fails:
1. Read the test file (`test_output.py`) to understand exact expectations.
2. Compare expected sheet names, column headers, row positions, and formula patterns.
3. Rebuild with adjusted structure — do not try to patch individual cells.
4. If openpyxl formulas don't evaluate as expected, check whether the test uses a formula evaluator that requires specific function syntax.
5. Verify the Ending Balance control row's Beginning Balance references Period Totals, not its own cell.
6. Verify Variance formula uses GL row minus Ending Balance row.

## References

- See `references/rollforward_anatomy.md` for the standard deferred revenue detail sheet layout.
- See `references/accrual_variant.md` for accrual and warranty reserve column headers and layout differences.
- See `references/warranty_reserve_variant.md` for warranty-specific data filtering, account mapping JSON, and summary sheet patterns.
- Use `scripts/build_rollforward.py` as your starting point for all rollforward workbooks.
- Run `scripts/verify_workbook.py <path>` after building to catch structural issues.
