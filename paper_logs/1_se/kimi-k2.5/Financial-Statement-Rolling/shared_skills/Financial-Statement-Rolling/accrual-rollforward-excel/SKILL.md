---
name: accrual-rollforward-excel
description: Build multi-period accrual rollforward workbooks with rolling balance calculations and GL reconciliation. Use for payroll accruals, bonus accruals, warranty reserves, or any liability account requiring period-by-period rollforwards with beginning balance + adds - releases = ending balance logic. This pattern applies whenever you see incurred/paid/close columns or reserve movements across multiple periods.
---

# Accrual Rollforward Workbooks

Build Excel workbooks that track accrual balances across multiple periods with rolling calculations and automated GL variance detection.

## Pattern Recognition: When to Use This Skill

Use accrual rollforward (not deferred revenue) when:
- Data shows **incurred / paid / closing** movements (not billings/recognition)
- Balance **resets each period** with new activity (not cumulative recognition)
- Keywords: **warranty reserve**, **payroll accrual**, **bonus accrual**, **claims paid**, **reserve movements**
- Formula pattern needed: `ending = prior_ending + adds - releases` (rolling chain)

| Scenario | Use This Skill | Pattern |
|----------|--------------|---------|
| Warranty reserves with incurred/paid | ✓ Accrual rollforward | Rolling chain |
| Payroll/bonus accruals | ✓ Accrual rollforward | Rolling chain |
| Deferred revenue recognition | ✗ Use `deferred-revenue-excel` | Cumulative |
| Contract billings/recognition | ✗ Use `deferred-revenue-excel` | Cumulative |

## Key Differences from Deferred Revenue

| Aspect | Deferred Revenue | Accrual Rollforward |
|--------|---------------|---------------------|
| Balance flow | Cumulative recognition | Rolling period-by-period |
| Ending balance formula | Beginning + all prior recognition | Prior ending + current adds - releases |
| Typical accounts | 2100-2199 (unearned revenue) | 2105-2110 (payroll, bonus, warranty accruals) |
| Period linkage | Independent calculations | Chain: Sep ending → Oct beginning |

## Standard Structure

**Accrual Summary Sheet:**
- Company header (rows 1-3)
- Account sections with cross-references to detail sheets
- Total GL Balance rollup

**Detail Sheets (one per accrual account):**
- Row 5: Headers — Accrual Bucket, Beginning Balance, [Month] Accruals/Releases/Ending Balance (×3+), Reserve Months, Notes, Dept Code
- Rows 6-8: Data rows (3 line items typical, sorted alphabetically)
- Rows 9-12: Control rows

## Control Row Formulas (Critical Pattern)

**Row 9: Period Totals**
- B9: `=SUM(B6:B8)` (Beginning Balance total — usually 0)
- C9: `=SUM(C6:C8)` (Sep Accruals)
- D9: `=SUM(D6:D8)` (Sep Releases)
- E9: `=SUM(E6:E8)` (Sep Ending Balance)
- Repeat pattern for Oct (F-H), Nov (I-K), etc.
- **L9 (Reserve Months):** `=C9+F9+I9` (sum of all accrual columns)

**Row 10: Ending Balance (Rolling Calculation)**
- E10: `=B10+C10-D10` (Sep: beginning + adds - releases)
- H10: `=E10+F10-G10` (Oct: prior ending + adds - releases)
- K10: `=H10+I10-J10` (Nov: prior ending + adds - releases)
- **L10:** `=D10+G10+J10` (total releases across all periods)

**Row 11: Variance**
- L11: `=L12-K12` (GL Balance - Ending Balance)

**Row 12: GL Balance**
- E12, H12, K12: Hardcoded values from source JSON
- **L12:** `=L9-L10` (Period Totals - Ending Balance)

## Cross-Reference Pattern (Summary Sheet)

Link to detail sheet control rows:
- `='Payroll Accrual #2105'!L9` → Period Totals
- `='Payroll Accrual #2105'!L10` → Ending Balance  
- `='Payroll Accrual #2105'!L12` → GL Balance

## Summary Sheet Layout Validation

**Critical:** Verify exact row positioning matches requirements:

```python
# Always verify summary sheet row references match spec
summary = wb['Warranty Summary']

# Consumer section should be in specific rows
assert "!O9" in str(summary['B7'].value)   # Period Totals
assert "!O10" in str(summary['B8'].value)  # Ending Balance  
assert "!O12" in str(summary['B9'].value)  # GL Balance

# Commercial section spacing
assert "!O9" in str(summary['B12'].value)
assert "!O10" in str(summary['B13'].value)
assert "!O12" in str(summary['B14'].value)
```

## Column Mapping

From CSV source to Excel columns:

| CSV Column | Excel Column | Content |
|------------|--------------|---------|
| `entity` | A | Accrual Bucket name |
| `beginning_balance` | B | Starting balance (usually 0) |
| `{month}_incurred` or `{month}_adds` | C, F, I | Accruals/additions |
| `{month}_paid` or `{month}_release` | D, G, J | Releases/reductions |
| `{month}_close` or `{month}_ending_balance` | E, H, K | Calculated ending |
| `coverage_months` / `term_months` | L | Reserve Months |
| `explanation` / `comments` | M | Notes |
| `gl_code` / `account_number` | N | Department Code |

## Verification Strategy

**Critical:** openpyxl never evaluates formulas. See `references/formula-evaluation.md` in `deferred-revenue-excel` for full discussion.

**Validate by formula presence, not value:**
```python
from openpyxl import load_workbook
wb = load_workbook('/path/to/file.xlsx')
ws = wb['Payroll Accrual #2105']

# Verify formula strings exist
assert ws['E10'].value == '=B10+C10-D10'
assert ws['H10'].value == '=E10+F10-G10'
assert ws['K10'].value == '=H10+I10-J10'
assert ws['L9'].value == '=C9+F9+I9'

# Verify hardcoded GL values from source
assert ws['E12'].value == 3500.0  # from gl_balances.json
assert ws['H12'].value == 4600.0
assert ws['K12'].value == 5700.0
```

**Validate cross-references in Summary:**
```python
summary = wb['Accrual Summary']
assert "'Payroll Accrual #2105'!L9" in str(summary['B7'].value)
assert "'Payroll Accrual #2105'!L12" in str(summary['B9'].value)
```

## Troubleshooting

**Formulas in wrong rows:**
- Re-read task spec for exact row numbers
- Common pattern: consumer in rows 6-9, commercial in rows 11-14
- Verify summary formulas point to correct detail sheet rows (9=totals, 10=ending, 12=GL)

**Wrong formula pattern applied:**
- If task mentions "warranty reserve", "claims paid", "incurred" → use rolling chain
- If task mentions "deferred revenue", "billings", "recognition" → use `deferred-revenue-excel`

## Anti-Patterns

- **Don't use deferred revenue's cumulative formula** (`=D11+G11+J11`) — accruals need rolling `=prior+adds-releases`
- **Don't skip the chain in Ending Balance** — each period depends on the prior period's ending
- **Don't validate by summing in Python** — verify formula strings match expected pattern
- **Don't forget L9 formula** — Reserve Months sums accrual columns, not ending balances
- **Don't guess summary row positions** — verify exact rows match requirements

## Data Sources

Typical inputs:
- `*_accrual_schedule.csv` — Line items with adds/releases per period
- `*_warranty_reserve.csv` — Warranty-specific with incurred/paid/close
- `gl_balances.json` — Period-end GL balances keyed by account

Example JSON structure:
```json
{
  "payroll_accrual_2105": {"sep": 3500, "oct": 4600, "nov": 5700},
  "bonus_accrual_2110": {"sep": 17000, "oct": 31000, "nov": 50400},
  "consumer_warranty_2440": {"jun": 15000, "jul": 17500, "aug": 13500, "sep": 7500}
}
```
