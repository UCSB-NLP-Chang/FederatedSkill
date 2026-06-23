---
name: deferred-revenue-rollforward
description: Build deferred revenue rollforward workbooks (Excel) from CSV schedules and GL balance data. Use when creating multi-sheet .xlsx files with detail sheets per revenue account, control rows (Period Totals, Ending Balance, Variance, GL Balance), and live Excel formulas.
---

# Deferred Revenue Rollforward Workbook

## When to Use
- Task asks for a deferred revenue rollforward, waterfall, or schedule workbook
- Source data is CSV schedules (per account) plus GL balances (JSON)
- Output must be a multi-sheet Excel file with formulas, not static values

## Workflow

1. **Read all source files first** — CSV schedules and GL balance data.
2. **Determine the exact expected file name** from the task description. Do not guess.
3. **Plan the sheet structure**: Summary sheet first, then detail sheets per revenue account.
4. **Build with openpyxl** — see `scripts/build_rollforward.py` for a working template.
5. **Verify before submission** — see Verification section below.

## Critical Formula Patterns

### Ending Balance Control Row (most common bug)
Each month's Ending Balance must chain from the **previous period's totals**, not from an empty cell in the same row.

**WRONG:**
```
Row 12 (Ending Balance): =B12+C12-D12
```
B12 is empty — this self-references the Ending Balance row's own beginning balance.

**CORRECT:**
```
Row 11 (Period Totals): =SUM(B7:B10)
Row 12 (Ending Balance):
  B12: =B11 (equals Period Totals beginning balance)
  E12: =B12+C11-D11 (May Ending = BegBal + MayBillings - MayRecognition)
  H12: =E12+F11-G11 (Jun Ending = MayEnding + JunBillings - JunRecognition)
```

### Variance Formula Direction
Variance = GL Balance − Ending Balance. Zero means books balance.
Formula: `=N14-N12` where N14 is GL Balance and N12 is Ending Balance.

### Cross-Sheet References
Summary sheet must link to detail sheets with proper quoting:
```
='SaaS Rev #2300'!O11
```
Single quotes required for sheet names with spaces or special characters.

## Verification Steps

1. **Open the file with openpyxl and read back formula cells** — confirm formula text is correct.
2. **Manually compute expected values** for Period Totals, Ending Balance, and Variance from raw data.
3. **Confirm Variance = 0** for every account.
4. **Check sheet order** matches requirement exactly.
5. **Check file name** matches expected pattern.
6. **Run `python3 scripts/verify_workbook.py <path>`** if available.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### deferred-revenue-rollforward (standard)
- Ending Balance control row's Beginning Balance (B12) must reference Period Totals B11, not its own empty cell
- Variance = GL Balance minus Ending Balance: `=N14-N12`
- Period Totals = SUM of line item rows only, excluding control rows
- Cross-sheet links require single quotes: `='SaaS Rev #2300'!O11`
- Sheet names must match account names exactly (e.g., "SaaS Rev #2300" not "SaaS Rev 2300")
- Number format `#,##0.00` on all monetary cells including formula cells

## Common Pitfalls

- **Self-referencing control rows**: Ending Balance control row referencing its own empty Beginning Balance cell.
- **Wrong Variance sign**: Must be GL minus Ending Balance.
- **Hardcoded values where formulas expected**: Tests often check that cells contain formulas.
- **Missing cross-sheet references on Summary**: Summary must link to detail sheets with formulas.
- **File name mismatch**: Extract exact filename pattern from task description.
- **Sheet name mismatch**: Use exact names like `SaaS Rev #2300` not variants.

## References

- `references/rollforward_anatomy.md` — detailed row/column layout diagram
