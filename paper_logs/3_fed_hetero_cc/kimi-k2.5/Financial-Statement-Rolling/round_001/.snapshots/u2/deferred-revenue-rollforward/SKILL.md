---
name: deferred-revenue-rollforward
description: Build deferred revenue rollforward workbooks in Excel from CSV schedules and GL balance data. Use when creating multi-sheet .xlsx files with detail sheets per revenue account, control rows (Period Totals, Ending Balance, Variance, GL Balance), and cross-sheet summary links with live formulas.
---

# Deferred Revenue Rollforward Workbook

## When to Use
- Task asks for a deferred revenue rollforward, waterfall, or schedule workbook
- Source data is CSV schedules (per account) plus GL balances (JSON)
- Output must be a multi-sheet Excel file with live formulas, not static values

## Workflow

1. **Read all source files first** — CSV schedules and GL balance JSON.
2. **Extract the exact expected file name** from the task. Do not guess; look for patterns like `CompanyName_Deferred_Revenue_MM-YY.xlsx`.
3. **Plan sheet structure**:
   - Summary sheet first (index 0), then one detail sheet per revenue account
   - Detail sheet column order: Customer, Beginning Balance, then per-month: Billings, Recognition, Ending Balance, then Contract Months, Notes, Revenue Code
4. **Build with openpyxl** — see `scripts/build_rollforward.py` for a working template.
5. **Validate formulas before declaring success** — see Verification below.

## Critical Formula Patterns

### Ending Balance Control Row (most common bug)

**WRONG** — Self-referencing (B12 is the Ending Balance row's own column B, which is empty):
```
Row 12 (Ending Balance): B12=empty, E12=B12+C12-D12
Result: E12 = 0+0-0 = 0 (wrong)
```

**RIGHT** — Ending Balance row's Beginning Balance references Period Totals:
```
Row 11 (Period Totals): B11 =SUM(B7:B10)
Row 12 (Ending Balance): B12 =B11, E12 =B12+C11-D11, H12 =E12+F11-G11, ...
Result: E12 = BegBal + Billings - Recognition (correct)
```

### Formula Reference Table

| Control Row | Column B | Column E (May) | Column H (Jun) | Column K (Jul) | Column N (Aug) |
|-------------|----------|----------------|----------------|----------------|----------------|
| Period Totals (11) | `=SUM(B7:B10)` | `=SUM(E7:E10)` | `=SUM(H7:H10)` | `=SUM(K7:K10)` | `=SUM(N7:N10)` |
| Ending Balance (12) | `=B11` | `=B12+C11-D11` | `=E12+F11-G11` | `=H12+I11-J11` | `=K12+L11-M11` |
| Variance (13) | — | — | — | — | `=N14-N12` |
| GL Balance (14) | — | hardcoded May GL | hardcoded Jun GL | hardcoded Jul GL | hardcoded Aug GL |

### Variance Formula Direction
Variance = GL Balance minus Ending Balance for the final period.
- Formula: `=N14-N12` (GL Balance row minus Ending Balance row)
- Should equal 0 when books balance.

### Cross-Sheet References
Summary sheet links to detail sheets with proper quoting for names containing spaces or special characters:
```
='SaaS Rev #2300'!N11    ← correct
=SaaS Rev #2300!N11      ← WRONG (missing quotes)
```

## Verification Steps

Before submitting, **always** run these checks:

1. **Open the file with openpyxl and read back every formula cell** — confirm formula text is correct.
2. **Manually compute expected values** for Period Totals, Ending Balance, and Variance from raw CSV.
3. **Confirm Variance = 0** for every account.
4. **Check sheet order** matches requirement (Summary first, then detail sheets).
5. **Check file name** matches expected pattern exactly.
6. **Check number format** `#,##0.00` on all monetary cells.

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs. Pass raw float values directly:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance decides acceptable precision; the skill's job is to give it full precision.

## Anti-Patterns

- **Self-referencing control rows**: Ending Balance row referencing its own empty Beginning Balance cell.
- **Wrong Variance sign**: Must be GL minus Ending Balance.
- **Hardcoded values where formulas expected**: Tests often check for `=SUM(...)` formulas.
- **Missing cross-sheet references on Summary**: Should link to detail sheets with formulas.
- **File name mismatch**: Extract exact name from task description.
- **Sheet name mismatch**: Use exact names like `SaaS Rev #2300` (with `#` and space).
- **Missing number formatting**: Apply `#,##0.00` to all monetary cells including formula cells.

## Known Invariants (by sub-task)

### deferred-revenue-rollforward (standard)
- Ending Balance control row's Beginning Balance (B12) must reference Period Totals B11 via formula `=B11`.
- Period Totals sums only line-item rows (e.g., 7-10), not control rows.
- Sheet order: Summary first (index 0), then detail sheets in account order.
- Cross-sheet links require single quotes: `='SaaS Rev #2300'!N11`.

## Scripts

- `scripts/build_rollforward.py` — Template with correct formula patterns.

## References

- `references/rollforward_anatomy.md` — Detailed layout diagram.
