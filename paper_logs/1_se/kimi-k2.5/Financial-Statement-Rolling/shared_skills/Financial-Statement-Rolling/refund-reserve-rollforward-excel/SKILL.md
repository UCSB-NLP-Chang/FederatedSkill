---
name: refund-reserve-rollforward-excel
description: Build refund reserve accrual workbooks with version-based deduplication and patch processing. Use for refund reserves, credit reserves, or customer liability accounts with versioned snapshots, approved/detail row filtering, and accrued/credited flow terminology. Trigger when you see 'refund', 'credit reserve', 'version', 'approved', 'row_kind', 'accrued', 'credited', or snapshot-based data with case_id/version pairs.
---

# Refund Reserve Rollforward Workbooks

Build Excel workbooks tracking refund or credit reserves with versioned data, approval filtering, and patch-based adjustments.

## Pattern Recognition

Use this skill when:
- **Versioned snapshots** with `case_id` and `version` fields (highest version wins)
- **Status filtering** on `approved=true` and `row_kind=detail` (exclude summary/header rows)
- **Terminology:** `accrued` (adds) / `credited` (releases) instead of adds/releases
- **Patch overrides/inserts** via CSV with field-level or row-level changes
- Keywords: **refund reserve**, **credit reserve**, **case_id**, **version**, **approved**, **accrued**, **credited**

| Scenario | Use This Skill |
|----------|---------------|
| Refund reserves with versioned snapshots | ✓ Refund reserve rollforward |
| Schedule patches on CSV base schedules | ✗ Use `schedule-patch-rollforward-excel` |
| Project costs with revision filtering | ✗ Use `project-cost-rollforward-excel` |
| Simple accruals without versioning | ✗ Use `accrual-rollforward-excel` |

## Critical: Data Processing Pipeline

**Step 1: Filter by status**
```python
# Keep only approved detail rows
filtered = [
    row for row in data 
    if row.get('approved') == True 
    and row.get('row_kind') == 'detail'
]
```

**Step 2: Version deduplication (keep highest)**
```python
from collections import defaultdict

def dedupe_versions(items):
    by_case = defaultdict(list)
    for item in items:
        by_case[item['case_id']].append(item)
    
    result = []
    for case_id, versions in by_case.items():
        highest = max(versions, key=lambda x: x['version'])
        result.append(highest)
    return result
```

**Step 3: Apply patch overrides/inserts**
- Override: Update specific fields on existing case_id
- Insert: Append new row with full data

**Step 4: Sort by customer_name, then case_id**

## Column Mapping

| JSON Field | Excel Column | Notes |
|------------|--------------|-------|
| `customer_name` | A | Sorted alphabetically |
| `opening_amount` / `opening_balance` | B | Beginning balance |
| `flow_months.{month}.accrued` | C, F, I, L | Additions (capitalized) |
| `flow_months.{month}.credited` | D, G, J, M | Releases (credited) |
| Calculated ending | E, H, K, N | `prior + accrued - credited` |
| `term_hint` / `term_months` | O | Reserve months |
| `memo_text` / `comments` | P | Notes |
| `account_code` | Q | Account number |

## Formula Patterns

**Rolling Ending Balance (critical chain):**
- `E10: =B10+C10-D10` (Aug: beg + accrued - credited)
- `H10: =E10+F10-G10` (Sep: prior ending + accrued - credited)
- `K10: =H10+I10-J10` (Oct: prior ending + accrued - credited)
- `N10: =K10+L10-M10` (Nov: prior ending + accrued - credited)

**Column O (Reserve Months / Total Credited):**
- O9 (Period Totals): `=C9+F9+I9+L9` (sum of all accrued columns)
- O10 (Ending Balance): `=D10+G10+J10+M10` (sum of all credited columns)
- O12 (GL Balance): `=O9-O10` (Period Totals - Ending Balance)

## Control Row Structure

| Row | Content | Formula Pattern |
|-----|---------|-----------------|
| 9 | Period Totals | `=SUM(B6:B8)` etc., O9 sums accrued |
| 10 | Ending Balance | Rolling chain (E10, H10, K10, N10) |
| 11 | Variance | `=O12-N12` or `=O12-O10` |
| 12 | GL Balance | Hardcoded per period, `=O9-O10` |

## Summary Sheet Links

```python
# Enterprise section (adjust rows per spec)
ws['B7'] = "='Enterprise Refunds #2215'!O9"   # Period Totals
ws['B8'] = "='Enterprise Refunds #2215'!O10"  # Ending Balance
ws['B9'] = "='Enterprise Refunds #2215'!O12"  # GL Balance

# Total formula
ws['B16'] = '=B9+B14'  # Sum of GL Balances
```

## Verification Checklist

```python
from openpyxl import load_workbook

wb = load_workbook('/path/to/file.xlsx')

# 1. Sheet order
assert wb.sheetnames[0] == 'Refund Summary'

# 2. Version filtering worked
enterprise = wb['Enterprise Refunds #2215']
# Should have v2 values, not v1

# 3. Approved/detail filtering
assert 'Not Approved' not in [r[0].value for r in enterprise.iter_rows()]

# 4. Patch override applied
# Check specific values updated

# 5. Insert applied
assert 'Fable Services' in [r[0].value for r in smb_sheet.iter_rows()]

# 6. Formula patterns
assert '=B10+C10-D10' in str(enterprise['E10'].value)
assert '=E10+F10-G10' in str(enterprise['H10'].value)

# 7. Summary cross-references
summary = wb['Refund Summary']
assert '!O9' in str(summary['B7'].value)
assert '!O12' in str(summary['B9'].value)
```

## Anti-Patterns

- **Don't forget approved/detail filtering** — Many rows have approved=false or row_kind=summary
- **Don't keep lowest version** — Highest version wins for each case_id
- **Don't treat accrued/credited as adds/releases** — Same pattern, different terminology
- **Don't apply patches before filtering** — May reference superseded/unapproved rows
- **Don't hardcode row positions** — Data count varies with inserts/filters

## Troubleshooting

**Wrong line item count:**
- Check approved=true filter applied
- Verify row_kind=detail (exclude summary rows)
- Confirm version deduplication kept highest, not lowest

**Override not applied:**
- Apply patches AFTER status/version filtering
- Verify case_id exists in filtered dataset
- Check field name matches (accrued vs adds)

**Ending balance formula wrong:**
- Use rolling chain: `=prior_ending+accrued-credited`
- Not cumulative sum like deferred revenue
- Verify B10 carries beginning balance (usually 0)

## See Also

- `schedule-patch-rollforward-excel` — For CSV-based schedules with status filtering
- `project-cost-rollforward-excel` — For JSON with revision/active flags
- `accrual-rollforward-excel` — Base accrual pattern without versioning
