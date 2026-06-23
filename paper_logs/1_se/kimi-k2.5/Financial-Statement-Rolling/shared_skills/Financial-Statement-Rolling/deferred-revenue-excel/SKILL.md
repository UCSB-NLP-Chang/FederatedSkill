---
name: deferred-revenue-excel
description: Build deferred revenue reconciliation workbooks with cross-sheet formulas linking detail schedules to summary controls. Use when creating multi-period revenue rollforwards with GL variance reconciliation, especially with openpyxl where formula calculation requires special handling.
---

# Deferred Revenue Reconciliation Workbooks

Build Excel workbooks that reconcile deferred revenue balances across multiple periods with automated variance detection against GL balances.

## Standard Structure

**Summary Sheet:**
- Company header (rows 1-3)
- Account sections with cross-references to detail sheets
- Period Totals, Ending Balance, GL Balance per account
- Total GL Balance rollup

**Detail Sheets (one per revenue code):**
- Header row 5: Customer, Beginning Balance, [Period] Billings/Recognition/Ending Balance columns, Contract Months, Notes, Revenue Code
- Data rows 6-9: Customer line items
- Control rows 10-13:
  - Row 10: Period Totals (sum of billing columns)
  - Row 11: Ending Balance (cumulative recognition calculation)
  - Row 12: Variance (GL Balance minus calculated ending)
  - Row 13: GL Balance (hardcoded values from source system)

## Formula Pattern

Detail sheet column O formulas:
- **O10 (Period Totals):** `=C10+F10+I10+L10` (sum billing columns C, F, I, L)
- **O11 (Ending Balance):** `=D11+G11+J11+M11` (sum recognition columns D, G, J, M)
- **O12 (Variance):** `=O13-N13` (GL Balance minus Ending Balance)
- **O13 (GL Balance):** `=O10-O11` (Period Totals minus Ending Balance)

Cross-reference formulas (Summary sheet):
- `='Sheet Name'!O10` for Period Totals
- `='Sheet Name'!O11` for Ending Balance  
- `='Sheet Name'!O13` for GL Balance

## Critical: Formula Calculation Limitation

**openpyxl never evaluates formulas on save.** Formulas exist in XML but `.value` returns None until Excel opens the file.

**Options for verification:**

1. **Accept formula strings as correct** - Verify formula text, not calculated value
2. **Use `data_only=True` with saved file** - Only works if file was previously opened in Excel
3. **Use xlwings/pywin32** - Requires Excel installation, see `references/formula-evaluation.md`

## Verification Strategy

```python
# Verify formulas exist (not calculated values)
from openpyxl import load_workbook
wb = load_workbook('/path/to/file.xlsx')
ws = wb['Sheet Name']

# Check formula string, not .value
assert ws['O10'].value.startswith('=') or isinstance(ws['O10'].value, str)
assert 'O10' in [cell.value for cell in ws['O10'].value if 'O10' in str(cell.value)]

# For data validation, check raw inputs
assert ws['E13'].value == 81000  # Hardcoded GL value
```

## Anti-Patterns

- **Don't rely on `cell.value` for formula results** - Always None until Excel calculates
- **Don't use openpyxl's `guess_types`** - Can corrupt formula strings
- **Don't validate by summing cells in Python** - Use source data instead

## Data Sources

Typical input files:
- `*_deferred_revenue_schedule.csv` - Line item schedules with adds/releases/ending balances
- `gl_balances.json` - Period-end GL balances by account

Column mapping (CSV to Excel):
- `entity` → Column A (Customer)
- `beginning_balance` → Column B
- `{month}_adds` → Billings columns (C, F, I, L)
- `{month}_release` → Recognition columns (D, G, J, M)
- `{month}_ending_balance` → Ending balance columns (E, H, K, N)
- `term_months` → Column O (Contract Months)
- `comments` → Column P (Notes)
- `account_number` → Column Q (Revenue Code)