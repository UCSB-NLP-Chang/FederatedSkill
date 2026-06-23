---
name: financial-rollforward-workbook
description: Build multi-period Excel rollforward workbooks with formulas, cross-sheet references, and control rows. Use for deferred revenue, accruals, warranty reserves, commission assets, or any financial rollforward schedule requiring Beginning→Additions→Releases→Ending flow with GL reconciliation.
---

# Financial Rollforward Workbook Builder

## Workflow (MANDATORY sequence)

1. **RUN skeleton script first.** Load and adapt `scripts/build_rollforward.py`. Do NOT build from scratch.
2. **Parse input files.** Load CSV schedules, JSON GL balances, optional JSON account mappings, optional CSV overrides.
3. **Filter records.** Active/eligible only. For project cost: dedup by row_id (highest revision), apply CSV overrides.
4. **Write detail sheets.** Headers, data rows, control rows in exact order: Period Totals → Ending Balance → Variance → GL Balance.
5. **Write formulas.** Use exact patterns below. **Variance MUST use column N for both operands.**
6. **Write summary sheet.** Cross-sheet links to control rows. Sheet names with spaces need single quotes.
7. **Run validation script.** `python scripts/validate_formulas.py <workbook>` before saving.

## Control Row Formula Patterns (CRITICAL)

### Period Totals Row
```
=SUM(B{first}:B{last})   # for each column B through N
O_total = =C{totals}+F{totals}+I{totals}+L{totals}  # sum of accruals
```

### Ending Balance Row
```
E_ending = =B{totals}+C{totals}-D{totals}           # Jul: Beg from Period Totals
H_ending = =E{ending}+F{totals}-G{totals}           # Aug: prior Ending + activity
K_ending = =H{ending}+I{totals}-J{totals}           # Sep: prior Ending + activity
N_ending = =K{ending}+L{totals}-M{totals}           # Oct: prior Ending + activity
```

**CRITICAL**: Ending Balance row's Beginning Balance MUST reference Period Totals row, NOT its own empty cell.

### Variance Row (MOST CRITICAL)
```
# CORRECT: Both operands use column N
= N{gl_row} - N{ending_row}

# WRONG: Do NOT use column O for GL Balance
= O{gl_row} - N{ending_row}  # ERROR - propagates bug
```

**STOP**: If you write `=O{gl_row}` in Variance formula, the workbook will fail verification.

### GL Balance Row
```
E_gl = <static value from JSON>    # Jul GL
H_gl = <static value from JSON>    # Aug GL
K_gl = <static value from JSON>    # Sep GL
N_gl = <static value from JSON>    # Oct GL
```

## Column Layout (standard)
| Col | Purpose |
|-----|---------|
| A | Partner/Description |
| B | Beginning Balance |
| C-D | Period 1 Accruals/Utilization |
| E | Period 1 Ending |
| F-G | Period 2 Accruals/Utilization |
| H | Period 2 Ending |
| I-J | Period 3 Accruals/Utilization |
| K | Period 3 Ending |
| L-M | Period 4 Accruals/Utilization |
| N | Period 4 Ending |
| O | Reserve/Formula column |

## Validation Assertion (run before save)

The validation script MUST pass. If it fails on Variance formula check:
```
AssertionError: Variance formula uses column O (wrong) instead of N
```
Fix the formula immediately: change `O{gl_row}` to `N{gl_row}`.

## Cross-Sheet References

Sheet names with spaces need single quotes:
```python
f"='{sheet_name}'!N{gl_row}"   # correct
f"={sheet_name}!N{gl_row}"      # breaks on spaces
```

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### deferred-revenue-rollforward
- Summary sheet cell positions are spec-given, not inferred.
- Sheet order: Summary first, then detail sheets in account number order.

### accrual-rollforward
- Variance row position: immediately after GL Balance row.

### warranty-reserve-rollforward
- Filter by `record_status` column: only `active` records included.
- Account mapping JSON maps bucket/code to sheet name.

### commission-asset-rollforward
- Filter by `eligible` flag in JSON activity data.

### project-cost-rollforward
- Dedup by row_id: keep highest revision number.
- Apply CSV overrides keyed by row_id.

## References

- `references/control-rows-template.md` - Exact formula templates for all control rows
- `scripts/build_rollforward.py` - Skeleton script to adapt (MANDATORY)
- `scripts/validate_formulas.py` - Formula validation with column-N assertion

## Anti-patterns

- Building workbook from scratch instead of adapting skeleton script
- Hardcoding row numbers instead of calculating dynamically
- Using column O in Variance formula (wrong)
- Self-referencing Ending Balance Beginning cell (must reference Period Totals)