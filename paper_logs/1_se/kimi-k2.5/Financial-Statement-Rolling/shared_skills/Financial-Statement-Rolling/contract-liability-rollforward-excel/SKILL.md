---
name: contract-liability-rollforward-excel
description: Build contract liability rollforward workbooks from JSON source data with revision deduplication, status filtering, and manual bridge overrides/inserts. Use when you see contract liability data with `contract_key`, `revision_no`, `active_flag`, `record_type`, and `month_roll` structure containing `booked`/`earned` flows. Trigger on keywords: contract liability, deferred revenue, subscriptions, services, contract_key, revision_no, active_flag, booked, earned, manual bridge.
---

# Contract Liability Rollforward Workbooks

Build Excel workbooks tracking contract liabilities (deferred revenue style) with complex data processing requirements: revision deduplication, status filtering, and manual bridge patching.

## Pattern Recognition: When to Use This Skill

Use this skill when the data structure shows:
- **JSON source** with `contract_key` and `revision_no` (highest revision wins per key)
- **Status flags**: `active_flag` (true/false) and `record_type` (detail/summary) requiring filtering
- **Monthly roll data**: `month_roll.{month}.booked` (billings) and `month_roll.{month}.earned` (recognition)
- **Manual bridge** CSV with `action` column (`override` or `insert`)
- Keywords: **contract liability**, **deferred revenue**, **subscriptions**, **services**, **contract_key**, **revision_no**, **booked**, **earned**, **manual bridge**

| Scenario | Use This Skill | Alternative |
|----------|--------------|-------------|
| Contract liability with revisions + active filtering | ✓ This skill | — |
| Simple accruals (incurred/paid) | ✗ | `accrual-rollforward-excel` |
| Deferred revenue from CSV schedules | ✗ | `deferred-revenue-excel` |
| Versioned refund reserves with case_id | ✗ | `refund-reserve-rollforward-excel` |
| Schedule patches on CSV | ✗ | `schedule-patch-rollforward-excel` |

## Critical: Pattern Classification

**This is a DEFERRED REVENUE pattern, not accrual.**

The data uses `booked`/`earned` terminology (billings/recognition), not `adds`/`releases`:
- Ending balance rolls forward: `prior_ending + booked - earned`
- O9 (Period Totals) sums **booked** columns (C, F, I, L)
- O10 (Ending Balance) sums **earned** columns (D, G, J, M) — unlike accrual which sums releases

## Data Processing Pipeline

**Step 1: Filter by status**
```python
# Keep only active detail rows, exclude summary/inactive
filtered = [
    row for row in data
    if row.get('active_flag') == True
    and row.get('record_type') == 'detail'
]
```

**Step 2: Deduplicate by revision (keep highest)**
```python
from collections import defaultdict

def dedupe_by_revision(items):
    by_key = defaultdict(list)
    for item in items:
        by_key[item['contract_key']].append(item)
    
    result = []
    for key, versions in by_key.items():
        highest = max(versions, key=lambda x: x['revision_no'])
        result.append(highest)
    return result
```

**Step 3: Apply manual bridge (AFTER filtering)**
```python
# Override: Update specific fields on existing contract_key
# Insert: Create new row with full data
for bridge in manual_bridge:
    if bridge['action'] == 'override':
        # Find by contract_key, update specified month fields
        pass
    elif bridge['action'] == 'insert':
        # Append new row with all required fields
        pass
```

**Step 4: Sort alphabetically by party_name**

**Step 5: Calculate rolling ending balances**
```python
# For each row, calculate ending balances
sep_ending = beginning + sep_booked - sep_earned
oct_ending = sep_ending + oct_booked - oct_earned
nov_ending = oct_ending + nov_booked - nov_earned
# etc.
```

## Column Mapping

| JSON Field | Excel Column | Content |
|------------|--------------|---------|
| `party_name` | A | Customer/vendor name |
| `opening_amount` | B | Beginning balance |
| `month_roll.{m}.booked` | C, F, I, L | Billings (adds) |
| `month_roll.{m}.earned` | D, G, J, M | Recognition (releases) |
| Calculated ending | E, H, K, N | Rolling ending balance |
| `term_hint` | O | Contract months |
| `memo_label` | P | Notes |
| `acct` | Q | Account number |

## Control Row Formulas

**Row 9: Period Totals**
- `B9: =SUM(B6:B8)` (Beginning Balance)
- `C9: =SUM(C6:C8)` (Sep Booked)
- `D9: =SUM(D6:D8)` (Sep Earned)
- `O9: =C9+F9+I9+L9` (Total Booked)

**Row 10: Ending Balance (rolling chain)**
- `E10: =B10+C10-D10` (Sep: beg + booked - earned)
- `H10: =E10+F10-G10` (Oct: prior + booked - earned)
- `K10: =H10+I10-J10` (Nov: prior + booked - earned)
- `N10: =K10+L10-M10` (Dec: prior + booked - earned)
- `O10: =D10+G10+J10+M10` (Total Earned — **deferred revenue pattern**)

**Row 11: Variance**
- `O11: =O12-N12` (GL Balance - Ending Balance)

**Row 12: GL Balance**
- `E12, H12, K12, N12`: Hardcoded from `gl_balances.json`
- `O12: =O9-O10` (Period Totals - Ending Balance)

## Summary Sheet Structure

```
Row 1: Company Name
Row 2: Report Title  
Row 3: Period Ending

Row 5: Account Header (e.g., "Subscriptions #2350")
Row 7: Period Totals → ='Sheet'!O9
Row 8: Ending Balance → ='Sheet'!O10
Row 9: GL Balance → ='Sheet'!O12

Row 11: Second Account
Row 12: Period Totals → ='Sheet2'!O9
Row 13: Ending Balance → ='Sheet2'!O10
Row 14: GL Balance → ='Sheet2'!O12

Row 16: Total GL Balance → =B9+B14
```

**CRITICAL:** Verify exact row numbers from task spec. Common variants use rows 6-8 or 7-9.

## Verification Checklist

```python
from openpyxl import load_workbook

wb = load_workbook('/path/to/file.xlsx')

# 1. Sheet order
assert wb.sheetnames[0] == 'Contract Liability Summary'

# 2. Revision filtering worked
sub = wb['Subscriptions #2350']
# Should have revision 2 values, not revision 1

# 3. Status filtering
assert 'SUB-X' not in [r[0].value for r in sub.iter_rows()]  # summary excluded

# 4. Manual bridge override applied
# Check specific field values updated

# 5. Manual bridge insert applied
assert 'Ember Training' in [r[0].value for r in svc.iter_rows()]

# 6. Rolling formula pattern (deferred revenue style)
assert '=B10+C10-D10' in str(sub['E10'].value)
assert '=E10+F10-G10' in str(sub['H10'].value)

# 7. O10 sums earned (deferred revenue), not releases (accrual)
assert 'D10+G10+J10+M10' in str(sub['O10'].value)

# 8. Summary cross-references
summary = wb['Contract Liability Summary']
assert '!O9' in str(summary['B7'].value)
assert '!O12' in str(summary['B9'].value)
```

## Data Sources

**Primary JSON (`contract_liability_dump.json`):**
```json
{
  "exports": [
    {
      "source_bucket": "sub_live",
      "clusters": [
        {
          "cluster_name": "Core Subscriptions",
          "records": [
            {
              "contract_key": "SUB-001",
              "revision_no": 2,
              "active_flag": true,
              "record_type": "detail",
              "party_name": "Aurora Transit",
              "opening_amount": 0,
              "month_roll": {
                "sep": {"booked": 20000, "earned": 5000}
              },
              "term_hint": 12,
              "memo_label": "Enterprise transit subscription",
              "acct": 2350
            }
          ]
        }
      ]
    }
  ]
}
```

**Manual Bridge CSV (`manual_bridge.csv`):**
```csv
action,source_bucket,contract_key,party_name,...,dec_booked,...,comments,account_number
override,sub_live,SUB-020,,,,2000,,Riders annual renewal,
insert,svc_live,SVC-220,Ember Training,0,...,3000,...,Training services reserve,2355
```

**Bucket Aliases (`bucket_aliases.csv`):**
```csv
source_bucket,sheet_name,gl_key,account_number
sub_live,Subscriptions #2350,subscriptions_2350,2350
svc_live,Services #2355,services_2355,2355
```

**GL Balances (`gl_balances.json`):**
```json
{
  "subscriptions_2350": {"sep": 21000, "oct": 26000, "nov": 20000, "dec": 11000},
  "services_2355": {"sep": 12000, "oct": 14750, "nov": 10000, "dec": 6250}
}
```

## Anti-Patterns

- **Don't use accrual rollforward formulas** — This is deferred revenue (booked/earned), not accrual (adds/releases)
- **Don't forget revision filtering** — Multiple revisions exist; keep highest per contract_key
- **Don't apply manual bridge before status filtering** — May reference superseded/inactive rows
- **Don't treat override as full row replacement** — Only change specified fields
- **Don't guess summary row positions** — Verify exact rows from spec
- **Don't skip alphabetical sorting** — Usually required by spec

## Troubleshooting

**Wrong ending balances:**
- Verify rolling chain: `=prior_ending+booked-earned`
- Not cumulative sum or accrual pattern
- Check manual bridge values applied correctly

**Wrong line item count:**
- Check active_flag=true AND record_type=detail
- Verify revision deduplication kept highest
- Confirm inserts actually appended

**Missing columns in data:**
- Some months may only have `earned` (no `booked`)
- Missing fields = 0, not error
- Handle gracefully with `.get(month, {}).get('booked', 0)`

## See Also

- `deferred-revenue-excel` — Base pattern without revision/filtering
- `refund-reserve-rollforward-excel` — Similar versioned data pattern with different terminology
- `project-cost-rollforward-excel` — Similar revision/active filtering with different data structure
