---
name: deferred-revenue-rollforward
description: Build multi-sheet Excel rollforward workbooks (deferred revenue, accrual, warranty reserve, or commission asset) from CSV/JSON schedules and GL balance data. Use when the task involves creating a .xlsx with detail sheets per account and a summary sheet, including control rows (Period Totals, Ending Balance, Variance, GL Balance) with live Excel formulas. Covers deferred revenue (Billings/Recognition), accrual (Accruals/Releases), warranty reserve (Accruals/Claims Paid or Incurred/Paid), and commission asset (Capitalized/Amortization) variants.
---

# Rollforward Workbook Builder

## When to Use
- Task asks for a deferred revenue rollforward, accrual rollforward, warranty reserve, waterfall, or schedule workbook
- Source data is CSV schedules (per account) plus GL balances (JSON or CSV)
- Output must be a multi-sheet Excel file with formulas, not just static values

## Mandatory Pre-Coding Checklist

**Do not write any workbook code until you complete these steps:**

1. **Read all source files** — CSV schedules, GL balance data, and account mapping JSON if present.
2. **Filter source data** — If CSV contains `record_status`, filter to `active` only before anything else.
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
5. **Identify the variant** (deferred revenue, accrual, warranty reserve, or commission asset) using the table below.
6. **Write down the Variance formula before coding** — This is the #1 failure point. The formula MUST be `={final_period_col}{gl_row}-{final_period_col}{ending_row}`. Example: `=N12-N10` for a 4-month rollforward where GL Balance is row 12, Ending Balance is row 10, and final period is column N. Write it down now: ___________
7. **Start from `scripts/build_rollforward.py`** — adapt it rather than writing from scratch. The skeleton already has the correct Ending Balance and Variance formula patterns.

## Variant Detection

| Variant | Activity Columns | Month Column | Entity Column | Account Column |
|---------|-----------------|--------------|---------------|----------------|
| Deferred Revenue | Billings / Recognition | Contract Months | Customer | Revenue Code |
| Accrual | Accruals / Releases | Reserve Months | Accrual Bucket | Department Code |
| Warranty | Accruals / Claims Paid (or Incurred/Paid) | Coverage Months | Claim Group | Reserve Account |
| Commission Asset | Capitalized / Amortization | Useful Life Months | Payee | Asset Account |

See `references/accrual_variant.md` for accrual and warranty reserve column layouts and control row formulas.
See `references/warranty_reserve_variant.md` for warranty-specific data filtering and account mapping JSON patterns.
See `references/commission_asset_variant.md` for commission asset data structures, JSON parsing, and control row formulas.

## Spec-Driven Summary Sheet

The summary sheet is the most common failure point. Agents frequently guess row positions and get them wrong.

**Rule**: Parse the spec for explicit cell references (e.g., "B7 = link to Payroll totals"). Build a mapping table before coding.

**Anti-pattern**: Building the summary sheet with guessed row positions and then patching cells afterward.

**Correct pattern**: Write the summary sheet in a single pass using the extracted cell map. Verify row positions match the spec before saving.

## Critical Formula Patterns (MUST GET RIGHT)

### Ending Balance — The Most Common Bug
Each month's Ending Balance must chain from the **previous month's Ending Balance**, not from an empty cell in the same row.

**Two valid patterns:**

1. **Reference Period Totals** (preferred, used in existing specs):
   - Ending Balance row's Beginning Balance: `=B{totals_row}`
   - Month Ending: `=E{ending_row}+F{totals_row}-G{totals_row}` (activity from Period Totals row)

2. **Self-contained SUMs**:
   - Ending Balance row has its own SUM formulas for input columns: `=SUM(B6:B8)`
   - Month Ending: `=E{ending_row}+F{ending_row}-G{ending_row}` (activity from same row)

**WRONG** (self-referencing empty cell — the most common bug):
```
Row 11 (Ending Balance): B11 is empty, E11 = =B11+C11-D11  → computes 0 + C - D
```

**RIGHT** (Pattern A — reference Period Totals):
```
Row 10 (Period Totals): B10 = =SUM(B6:B9)
Row 11 (Ending Balance): B11 = =B10, E11 = =B11+C10-D10  → correctly rolls forward
```

**Anti-pattern**: Writing rollforward formulas that reference empty cells on the same row without SUM formulas.

### Variance
Variance = GL Balance − Ending Balance (for the final period). Zero means books balance.

**WRONG** (most common mistake — comparing two GL row cells):
```
=O12-N12   (GL Balance O minus GL Balance N — WRONG)
=O{gl_row}-N{gl_row}   (any formula comparing two GL cells — WRONG)
```

**RIGHT** (GL final period minus Ending Balance final period):
```
=N12-N10   (GL Balance N minus Ending Balance N)
=N{gl_row}-N{ending_row}
```

**Verification**: Before saving, confirm your Variance formula references the Ending Balance row, not just GL Balance row cells.

For 3-month rollforwards: `=N{gl_row}-N{ending_row}`
For 4-month rollforwards: `=N{gl_row}-N{ending_row}` (same pattern, different column)

### Period Totals
Simple SUM of line-item columns above. Use `=SUM(B6:B9)` style formulas.

### GL Balance Row
Hardcode the GL values from the source JSON into the ending-balance columns. The total column can be a formula: `=O{totals}-O{ending}`.

## Data Filtering

**Active/Eligible Records Only**: Many source files include archived or placeholder records. Always filter these out before building the workbook:

```python
# CSV with record_status column
active_rows = [r for r in csv_data if r.get("record_status") == "active"]

# JSON activity data with eligible flag (commission asset)
eligible_rows = [r for r in json_rows if r.get("eligible") == True]
```

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

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
- Same control-row formula invariants apply as deferred revenue (see `references/accrual_variant.md` for column layout differences).
- Activity columns use "Accruals/Releases" instead of "Billings/Recognition".
- Summary sheet often includes a "Combined GL Balance" row (e.g., `B16 = B9 + B14`).

### warranty-reserve
- Variant of accrual rollforward. Uses "Accruals/Claims Paid" or "Incurred/Paid" terminology.
- Column O typically holds "Coverage Months" instead of "Contract Months" or "Reserve Months".
- 4-month structure is common (Jun/Jul/Aug/Sep).
- GL checkpoints are provided per period in the GL JSON.
- Source CSV may contain `record_status` column — filter to `active` only.
- Account mapping JSON (e.g., `reserve_account_map.json`) may be provided for sheet names.
- See `references/accrual_variant.md` and `references/warranty_reserve_variant.md` for the column layout and control row formulas.

### commission-asset
- Uses "Capitalized/Amortization" terminology instead of "Billings/Recognition" or "Accruals/Releases".
- Activity data comes as nested JSON with `sections` containing `rows` with `eligible` flags — filter to `eligible=true`.
- Metadata joined via `line_key` from a separate CSV.
- Line items sorted by payee name then line_key.
- Same control-row formula invariants apply (Ending Balance MUST reference Period Totals, Variance MUST be GL minus Ending Balance).
- See `references/commission_asset_variant.md` for detailed commission asset handling.

## Common Pitfalls
- **Wrong Variance formula**: Using `=O{gl_row}-N{gl_row}` instead of `=N{gl_row}-N{ending_row}`. This is the #1 failure.
- **Self-referencing control rows**: Ending Balance formulas referencing empty cells on the same row.
- **Hardcoded values where formulas are expected**: Tests check for formula strings starting with `=`.
- **Missing cross-sheet references on Summary**: Summary sheet should link to detail sheets with formulas, not hardcoded values.
- **File name mismatch**: Extract the exact filename from the task description.
- **Sheet name mismatch**: Use exact names from source data or account mapping JSON.
- **Missing number formatting on formula cells**: Apply `#,##0.00` to every monetary cell.
- **Summary sheet row misalignment**: Spec gives exact cell positions; do not guess.
- **Skipping tests**: Always run `pytest test_output.py -v` before declaring success.
- **Including archived/ineligible records**: Filter out non-active or ineligible records before processing.
- **Writing from scratch instead of using the skeleton**: `scripts/build_rollforward.py` already has correct formula patterns. Adapt it.

## Fallback Strategy

If the verifier or test suite fails:
1. Read the test file (`test_output.py`) to understand exact expectations.
2. Compare expected sheet names, column headers, row positions, and formula patterns.
3. Rebuild with adjusted structure — do not try to patch individual cells.
4. If tests expect specific formula patterns (e.g., reference Period Totals vs self-contained), match that pattern exactly.
5. Verify the Ending Balance control row's Beginning Balance references Period Totals, not its own cell.
6. Verify Variance formula uses GL row minus Ending Balance row.

## References

- See `references/rollforward_anatomy.md` for the standard deferred revenue detail sheet layout.
- See `references/accrual_variant.md` for accrual and warranty reserve column headers and control row formulas.
- See `references/warranty_reserve_variant.md` for warranty-specific data filtering and account mapping JSON patterns.
- See `references/commission_asset_variant.md` for commission asset data structures, JSON parsing, and control row formulas.
- Use `scripts/build_rollforward.py` as your starting point for all rollforward workbooks.
- Run `scripts/verify_workbook.py <path>` after building to catch structural issues.
