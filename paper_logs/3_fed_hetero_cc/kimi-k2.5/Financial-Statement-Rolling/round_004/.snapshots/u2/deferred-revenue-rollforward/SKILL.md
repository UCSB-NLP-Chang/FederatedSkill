---
name: deferred-revenue-rollforward
description: Build multi-sheet Excel rollforward workbooks (deferred revenue, accrual, warranty reserve, or commission asset) from CSV/JSON schedules and GL balance data. Use when the task involves creating a .xlsx with detail sheets per account and a summary sheet, including control rows (Period Totals, Ending Balance, Variance, GL Balance) with live Excel formulas. Covers deferred revenue (Billings/Recognition), accrual (Accruals/Releases), warranty reserve (Incurred/Paid), and commission asset (Capitalized/Amortization) variants.
---

# Rollforward Workbook Builder

## When to Use
- Task asks for a deferred revenue rollforward, accrual rollforward, warranty reserve, commission asset, waterfall, or schedule workbook
- Source data is CSV schedules, JSON activity data, or GL balances
- Output must be a multi-sheet Excel file with formulas, not just static values
- Source data may contain status columns (record_status) or eligibility flags (eligible) requiring filtering

## Workflow

1. **Read all source files** first — CSV schedules, GL balance data, and account mapping JSON if present.
2. **Filter source data**: If the CSV contains status columns like `record_status`, filter to `active` only (exclude archived/placeholder records). If JSON activity data has `eligible` flags, filter to `eligible=true` only.
3. **Extract account mappings**: If provided (e.g., `reserve_account_map.json`), use these to map buckets/codes to sheet names.
4. **Extract the exact expected file name** from the task description. Do not guess.
5. **Extract the exact summary sheet cell map** from the spec before writing code. The summary sheet has rigid cell positions (e.g., B7, B8, B9, B12, B13, B14, B16). Write down the mapping explicitly.
6. **Plan the sheet structure**:
   - Summary sheet first, then one detail sheet per account
   - Detail sheet column order varies by variant (see References below)
7. **Build with openpyxl** — see `scripts/build_rollforward.py` for a working skeleton.
8. **Run the test suite immediately** after saving — do not rely on manual spot-checks.

## Variant Detection

| Variant | Activity Columns | Month Column | Entity Column |
|---------|-----------------|--------------|---------------|
| Deferred Revenue | Billings / Recognition | Contract Months | Customer |
| Accrual | Accruals / Releases | Reserve Months | Accrual Bucket |
| Warranty | Incurred / Claims Paid (or Accruals/Claims Paid) | Coverage Months | Claim Group |
| Commission Asset | Capitalized / Amortization | Useful Life Months | Payee |

See `references/warranty_reserve_variant.md` for warranty-specific layout and formulas.
See `references/commission_asset_variant.md` for commission asset data structures and formulas.

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
Each month's Ending Balance must chain from the **previous month's Ending Balance**.

**Two valid patterns:**

1. **Reference Period Totals** (preferred in existing specs):
   - Ending Balance row's Beginning Balance: `=B{totals_row}`
   - Month Ending: `=E{ending_row}+F{totals_row}-G{totals_row}` (reference Period Totals for activity)

2. **Self-contained SUMs**:
   - Ending Balance row has its own SUM formulas for input columns: `=SUM(B6:B8)`
   - Month Ending: `=E{ending_row}+F{ending_row}-G{ending_row}` (reference same row)

**WRONG** (self-referencing empty cells):
```
Row 11 (Ending Balance): B11 is empty, E11 = =B11+C11-D11  → computes 0 + C - D
```

**RIGHT** (reference Period Totals):
```
Row 10 (Period Totals): B10 = =SUM(B6:B9)
Row 11 (Ending Balance): B11 = =B10, E11 = =B11+C10-D10  → correctly rolls forward
```

**Anti-pattern**: Writing rollforward formulas that reference empty cells on the same row without SUM formulas.

### Variance
Variance = GL Balance − Ending Balance (for the final period). Zero means books balance.
Formula: `=L{gl_row}-K{ending_row}` for 3-month rollforwards, or `=N{gl_row}-N{ending_row}` for 4-month.

### Period Totals
Simple SUM of line-item columns above. Use `=SUM(B6:B9)` style formulas.

### GL Balance Row
Hardcode the GL values from the source JSON into the ending-balance columns. The L (or O) column can be a formula: `=L{totals}-L{ending}`.

## Data Filtering

**Active/Eligible Records Only**: Source data often includes archived or ineligible records. Always filter before building:

```python
# CSV with record_status
active_rows = [r for r in csv_data if r.get("record_status") == "active"]

# JSON with eligible flag (commission asset)
eligible_rows = [r for r in json_data if r.get("eligible") == True]
```

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

### warranty-reserve-rollforward
- Variant of accrual rollforward. Uses "Incurred/Claims Paid" or "Accruals/Claims Paid" terminology.
- Column O typically holds "Coverage Months" instead of "Contract Months" or "Reserve Months".
- GL checkpoints are provided per period in the GL JSON.
- Must filter to `record_status=active` only.
- See `references/warranty_reserve_variant.md` for column layout and account mapping JSON patterns.

### commission-asset-rollforward
- Uses "Capitalized/Amortization" terminology instead of "Billings/Recognition" or "Accruals/Releases".
- Activity data often comes as nested JSON with `sections` containing `rows` with `eligible` flags.
- Metadata joined via `line_key` from a separate CSV.
- Line items sorted by payee name then line_key.
- Same control-row formula invariants apply (Ending Balance MUST reference Period Totals).
- Variance formula MUST reference Ending Balance row, not compare two GL cells.
- See `references/commission_asset_variant.md` for detailed commission asset handling.

## Common Pitfalls
- **Self-referencing control rows**: Ending Balance control row referencing its own empty Beginning Balance cell.
- **Wrong Variance sign**: Variance should be GL minus Ending Balance.
- **Hardcoded values where formulas are expected**: Tests check for formula strings starting with `=`.
- **Missing cross-sheet references on Summary**: Summary sheet should link to detail sheets with formulas, not hardcoded values.
- **File name mismatch**: Extract the exact filename from the task description.
- **Sheet name mismatch**: Use exact names from source data or account mapping JSON.
- **Missing number formatting on formula cells**: Apply `#,##0.00` to every monetary cell.
- **Summary sheet row misalignment**: Spec gives exact cell positions; do not guess.
- **Including archived records**: Filter out non-active records before processing.

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
- See `references/accrual_variant.md` for accrual and warranty reserve column headers and layout differences.
- See `references/warranty_reserve_variant.md` for warranty reserve patterns (Incurred/Paid columns, active record filtering, account mapping JSON).
- See `references/commission_asset_variant.md` for commission asset data structures, metadata joining, and formula patterns.
- Use `scripts/build_rollforward.py` as your starting point for all rollforward workbooks.
- Run `scripts/verify_workbook.py <path>` after building to catch structural issues.
