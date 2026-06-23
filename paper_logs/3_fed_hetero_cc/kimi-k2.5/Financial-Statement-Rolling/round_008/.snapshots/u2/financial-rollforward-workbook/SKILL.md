---
name: financial-rollforward-workbook
description: Build multi-sheet Excel rollforward workbooks with formulas, cross-sheet references, and GL reconciliation. Use for rebate reserves, accrual rollforwards, warranty reserves, or any period-over-period financial schedule.
---

# Financial Rollforward Workbook Builder

## When to use
- Multi-period financial schedules (monthly/quarterly columns)
- Rollforward workbooks with Beginning Balance → Additions → Releases → Ending Balance flow
- Cross-sheet summary pages linking to detail sheets
- GL balance reconciliation with variance analysis

## Pre-Coding Checklist (MANDATORY - Do This First)

Before writing ANY formulas, write down these three items:

1. **Variance formula**: Must be `=N{gl_row}-N{ending_row}` (column N for BOTH operands)
2. **Ending Balance first period**: Must be `=B{period_totals}+C{period_totals}-D{period_totals}`
3. **Control row indices**: Period Totals = last_data_row + 1, Ending Balance = +2, Variance = +3, GL Balance = +4

If you don't write these down before coding, you will make mistakes.

## Core workflow

### 1. Load source data
- CSV schedules: entity, beginning_balance, monthly columns, ending_balance, account_number
- JSON GL balances: monthly ending balances per account
- Filter to active records only (ignore archived/closed/superseded)

### 2. Build workbook structure
```python
from openpyxl import Workbook
wb = Workbook()
wb.remove(wb.active)
wb.create_sheet('Summary', 0)
wb.create_sheet('Detail #XXXX', 1)
```

**Sheet order**: Summary first, then detail sheets in account order.

### 3. Write period columns (B-N standard layout)
| Col | Content |
|-----|---------|
| A | Partner/Description |
| B | Beginning Balance |
| C-D | Month 1 Accruals/Utilization |
| E | Month 1 Ending |
| F-G | Month 2 Accruals/Utilization |
| H | Month 2 Ending |
| I-J | Month 3 Accruals/Utilization |
| K | Month 3 Ending |
| L-M | Month 4 Accruals/Utilization |
| N | Month 4 Ending |
| O | Reserve/Formula column |

### 4. Control row formulas (CRITICAL)

Given data rows 6-N, control rows follow:
- Row N+1: Period Totals
- Row N+2: Ending Balance
- Row N+3: Variance
- Row N+4: GL Balance

**Period Totals formulas**:
```python
ws[f'B{pt_row}'] = f'=SUM(B6:B{last_data_row})'
# Repeat for columns C through N
ws[f'O{pt_row}'] = f'=C{pt_row}+F{pt_row}+I{pt_row}+L{pt_row}'  # Sum of accruals
```

**Ending Balance formulas** (reference Period Totals for activity):
```python
# Month 1: Beginning + Accruals - Utilization
ws[f'E{eb_row}'] = f'=B{pt_row}+C{pt_row}-D{pt_row}'
# Month 2: Prior Ending + Accruals - Utilization (reference EB row for prior)
ws[f'H{eb_row}'] = f'=E{eb_row}+F{pt_row}-G{pt_row}'
ws[f'K{eb_row}'] = f'=H{eb_row}+I{pt_row}-J{pt_row}'
ws[f'N{eb_row}'] = f'=K{eb_row}+L{pt_row}-M{pt_row}'
ws[f'O{eb_row}'] = f'=E{eb_row}+H{eb_row}+K{eb_row}+N{eb_row}'  # Sum of endings
```

**Variance formula (CRITICAL - COLUMN N, NOT O)**:
```python
# CORRECT: Variance = GL Balance (column N) - Ending Balance (column N)
ws[f'O{var_row}'] = f'=N{gl_row}-N{eb_row}'

# WRONG - DO NOT USE:
# ws[f'O{var_row}'] = f'=O{gl_row}-N{eb_row}'  # WRONG!
# ws[f'O{var_row}'] = f'=O12-N12'  # WRONG!
```

**GL Balance row**: Static values from JSON in columns E, H, K, N.

### 5. Summary sheet cross-sheet links
```python
sheet_name = 'Channel Rebates #6120'
summary['B7'] = f"='{sheet_name}'!O{pt_row}"   # Period Totals Reserve
summary['B8'] = f"='{sheet_name}'!O{eb_row}"   # Ending Balance Reserve
summary['B9'] = f"='{sheet_name}'!N{gl_row}"   # GL Balance (column N)
```

**Always wrap sheet names with spaces in single quotes**.

### 6. Number formatting
Apply `#,##0.00` format to all monetary cells.

### 7. Run quick_validate.py (BLOCKING)
Execute `python scripts/quick_validate.py <workbook>` - if this FAILS, the test suite WILL fail. Fix errors first.

### 8. Run test suite
Execute `python -m pytest tests/` before declaring success.

## Known invariants (by sub-task)

### rebate-reserve-rollforward
- Variance = N(GL_row) - N(EB_row), using column N for both
- GL Balance values in columns E, H, K, N (monthly endings)

### accrual-rollforward
- Same Variance formula pattern
- Activity columns vary by accrual type

### refund-reserve-rollforward
- Filter approved detail rows with `row_kind='detail'`
- Dedupe by case_id keeping highest version
- Apply CSV adjustments by case_id
- Insert new rows from adjustments file

## Anti-patterns (DO NOT DO)

1. **WRONG Variance formula**: `=O12-N12` or `=O(GL)-N(EB)` - This uses column O for GL which is WRONG. GL Balance is in column N.

2. **Self-referencing Ending Balance**: EB Beginning Balance must reference Period Totals row, not own row's empty B cell.

3. **Hardcoded row numbers**: Calculate control row positions dynamically.

4. **Skipping quick_validate.py**: This script catches fatal bugs. Models that skip it fail 100% of the time. Run it FIRST.

5. **Missing test execution**: Always run test suite before completion.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance decides acceptable precision; the skill gives full precision.

## BLOCKING Pre-Submit Validation

**STOP. Run this script BEFORE running test suite. It catches the two most common fatal bugs:**

```bash
python scripts/quick_validate.py <workbook_path>
```

**If quick_validate.py FAILS, the test suite WILL fail. Fix the errors first.**

This script checks:
1. Variance formula uses column N for BOTH operands
2. Ending Balance references Period Totals (not self)

## Known invariants (by sub-task)

### rebate-reserve-rollforward
- Variance = N(GL_row) - N(EB_row), using column N for both
- GL Balance values in columns E, H, K, N (monthly endings)

### accrual-rollforward
- Same Variance formula pattern
- Activity columns vary by accrual type

### warranty-reserve-rollforward
- Filter to `record_status='active'` before processing

### commission-asset-rollforward
- Nested JSON with `sections`→`rows`→`eligible` flags
- Filter to `eligible=true`
- Sort by payee name then line_key

### refund-reserve-rollforward
- Filter approved detail rows with `row_kind='detail'`
- Dedupe by case_id keeping highest version
- Apply CSV adjustments by case_id
- Insert new rows from adjustments file

### contract-liability-rollforward
- Billings = additions, Revenue = utilization
- Ending Balance = Beginning + Billings - Revenue
- Filter out `record_type='summary'` and `active_flag=false`
- Dedup by contract_key keeping highest revision
- Apply bridge CSV overrides/inserts after normalization
- Bridge CSV columns: `dec_adds`, `dec_release`, `comments`, `account_number`

## References

- `references/formula-templates.md` - Complete formula code examples
- `scripts/quick_validate.py` - **BLOCKING pre-submit check** (MUST pass before test suite)
- `scripts/validate_rollforward.py` - Full validation script (run after quick_validate passes)
- `scripts/verify_workbook.py` - Post-build validation script

## Validation checklist

Before completion:
- [ ] Sheet order: Summary, then detail sheets ascending
- [ ] Run `python scripts/quick_validate.py <workbook>` - **MUST PASS (blocking)**
- [ ] Variance formula uses column N (NOT O) for GL Balance
- [ ] Ending Balance references Period Totals (not self)
- [ ] Cross-sheet links use single quotes for spaces
- [ ] Number format `#,##0.00` applied
- [ ] Run `python scripts/validate_rollforward.py <workbook>` - MUST pass
- [ ] Test suite passes
