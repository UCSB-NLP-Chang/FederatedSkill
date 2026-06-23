---
name: prepaid-amortizing-assets-excel
description: Build commission expense or prepaid asset amortization workbooks with rolling balance calculations. Use for commission assets, prepaid expenses, or any capitalized cost amortized over useful life. Trigger when you see 'capitalized', 'amortized', 'useful life', 'commission assets', or prepaid expense schedules with beginning balance + capitalized - amortized = ending balance logic.
---

# Prepaid/Amortizing Asset Workbooks

Build Excel workbooks tracking capitalized costs amortized over useful life periods.

## Pattern Recognition

Use this skill when the data shows:
- **Capitalized** amounts added each period (not billings)
- **Amortization** amounts expensed each period (not recognition/releases)
- **Useful life** in months determining amortization period
- Keywords: **commission assets**, **prepaid expenses**, **capitalized costs**, **amortization schedule**

| Scenario | Use This Skill |
|----------|---------------|
| Commission assets (capitalized/amortized) | ✓ Prepaid/amortizing assets |
| Deferred revenue (billings/recognition) | ✗ Use `deferred-revenue-excel` |
| Accrual reserves (incurred/paid) | ✗ Use `accrual-rollforward-excel` |

## Critical: Column O Semantics

Unlike deferred revenue or accrual patterns, **column O has dual meaning**:

- **O{period_totals_row} (Period Totals):** `=C{row}+F{row}+I{row}+L{row}` — sums **capitalized** columns (additions)
- **O{ending_row} (Ending Balance):** `=D{row}+G{row}+J{row}+M{row}` — sums **amortized** columns (reductions)
- **O{gl_row} (GL Balance):** `=O{period_totals_row}-O{ending_row}` — reconciles totals

## Standard Structure

**Summary Sheet:**
- Row 1: Company name
- Row 2: Period ending
- Row 4: Account section header (e.g., "Field Comm Asset #1510")
- Row 5: Column headers "Description", "Amount"
- Row 7: Period Totals → `='Detail Sheet'!O{period_totals_row}`
- Row 8: Ending Balance → `='Detail Sheet'!O{ending_row}`
- Row 9: GL Balance → `='Detail Sheet'!O{gl_row}`
- Row 16: Total `=B9+B15` (for two-account rollup)

**Detail Sheets:**
- Row 5: Headers — Payee, Beginning Balance, [Month] Capitalized/Amortized/Ending Balance columns, Useful Life Months, Notes, Asset Account
- Rows 6+: Data rows, sorted by payee name
- Control rows (see positioning below)

## Control Row Positioning (CRITICAL)

Calculate rows dynamically based on data count. **Never hardcode** without verification:

```python
data_row_count = len(data_rows)  # Actual data lines
first_data_row = 6
last_data_row = first_data_row + data_row_count - 1

month_totals_row = last_data_row + 1    # Period Totals label + SUM formulas
ending_balance_row = last_data_row + 2  # Ending Balance label + rolling formulas
variance_row = last_data_row + 3        # Variance label + formula
gl_balance_row = last_data_row + 4      # GL Balance label + hardcoded values
```

**Example:** 41 data rows → controls at rows 47, 48, 49, 50

## Rolling Ending Balance Formulas

Each period's ending balance depends on the prior period (rolling chain, not cumulative):

```
Jan Ending (E) = Beginning (B) + Jan Cap (C) - Jan Amort (D)
Feb Ending (H) = Jan Ending (E) + Feb Cap (F) - Feb Amort (G)
Mar Ending (K) = Feb Ending (H) + Mar Cap (I) - Mar Amort (J)
Apr Ending (N) = Mar Ending (K) + Apr Cap (L) - Apr Amort (M)
```

Excel formulas in ending_balance_row:
- `E{row}: =B{row}+C{row}-D{row}`
- `H{row}: =E{row}+F{row}-G{row}`
- `K{row}: =H{row}+I{row}-J{row}`
- `N{row}: =K{row}+L{row}-M{row}`
- `O{row}: =D{row}+G{row}+J{row}+M{row}` (total amortized)

## Summary Sheet Links

Reference the O-column values from detail sheets:

```python
# Account 1250 section
ws['B7'] = f"='PPD Exp #1250'!O{expense_totals_row}"   # Period Totals
ws['B8'] = f"='PPD Exp #1250'!O{expense_ending_row}"  # Ending Balance
ws['B9'] = f"='PPD Exp #1250'!O{expense_gl_row}"      # GL Balance

# Account 1251 section  
ws['B12'] = f"='PPD Ins #1251'!O{insurance_totals_row}"   # Period Totals
ws['B13'] = f"='PPD Ins #1251'!O{insurance_ending_row}"  # Ending Balance
ws['B14'] = f"='PPD Ins #1251'!O{insurance_gl_row}"      # GL Balance

# Total
ws['B16'] = '=B9+B14'
```

## Verification Checklist

**Critical:** Verify exact row references match data count:

```python
from openpyxl import load_workbook
wb = load_workbook('/path/to/file.xlsx')
summary = wb['Prepaid Summary']

# Verify summary cross-references point to correct rows
assert "!O" in str(summary['B7'].value)   # Period Totals
assert "!O" in str(summary['B8'].value)   # Ending Balance
assert "!O" in str(summary['B9'].value)   # GL Balance

detail = wb['PPD Exp #1250']

# Verify control row labels are in correct positions
assert detail.cell(month_totals_row, 1).value == 'Month Totals'
assert detail.cell(ending_balance_row, 1).value == 'Ending Balance'
assert detail.cell(variance_row, 1).value == 'Variance'
assert detail.cell(gl_balance_row, 1).value == 'GL Balance'

# Verify rolling chain formulas (not cumulative)
assert '=B' in str(detail.cell(ending_balance_row, 5).value)   # E col
assert '=E' in str(detail.cell(ending_balance_row, 8).value)   # H col
assert '=H' in str(detail.cell(ending_balance_row, 11).value)  # K col
assert '=K' in str(detail.cell(ending_balance_row, 14).value)  # N col

# Verify O-column semantics
assert 'C' in str(detail.cell(month_totals_row, 15).value)    # sums capitalized
assert 'D' in str(detail.cell(ending_balance_row, 15).value)   # sums amortized

# Verify GL values are hardcoded (not formulas) in E, H, K, N
gl_row_cells = [detail.cell(gl_balance_row, c) for c in [5, 8, 11, 14]]
for cell in gl_row_cells:
    assert cell.value is None or not str(cell.value).startswith('='), \
        f"GL cell should be hardcoded value, got {cell.value}"
```

## Common Errors

**Off-by-one in row calculations:**
- Calculate: `last_data_row = first_data_row + data_count - 1`
- 41 rows starting at 6 → last row is 46, controls at 47-50
- Verify by checking actual row contents, not just formulas

**Wrong O-column formulas:**
- O{period_totals_row} sums capitalized amounts (C, F, I, L)
- O{ending_row} sums amortized amounts (D, G, J, M)
- Don't use ending balance columns (E, H, K, N) in O-column formulas

**Summary references broken:**
- Verify row numbers match actual control row positions
- Use f-strings to embed calculated row numbers
- Check sheet name spelling matches exactly

## Data Sources

Typical inputs:
- `*_prepaid_schedule.csv` — Line items with capitalized/amortized amounts
- `gl_balances.json` — Period-end GL balances keyed by account

Column mapping:
| CSV Column | Excel Column | Content |
|------------|--------------|---------|
| `vendor` / `payee` / `entity` | A | Payee name |
| `beginning_balance` | B | Starting balance |
| `{month}_capitalized` / `{month}_adds` | C, F, I, L | Capitalized amounts |
| `{month}_amortized` / `{month}_amortization` | D, G, J, M | Amortization expense |
| `{month}_ending_balance` | E, H, K, N | Calculated ending |
| `amortization_months` / `useful_life_months` | O | Useful life |
| `comments` / `notes` | P | Notes |
| `account_number` / `account_code` | Q | Account number |

## Anti-Patterns

- **Don't use deferred revenue formulas** — this pattern rolls forward, not cumulative
- **Don't use accrual rollforward** — that uses incurred/paid, not capitalized/amortized
- **Don't hardcode control row numbers** — calculate from data count
- **Don't validate by Python summing** — verify formula strings match expected pattern
- **Don't skip row label verification** — ensure 'Month Totals', 'Ending Balance' etc. are in correct rows

## See Also

- `references/formula-patterns.md` — Complete column layout and formula reference
- `references/row-positioning.md` — Detailed row calculation examples