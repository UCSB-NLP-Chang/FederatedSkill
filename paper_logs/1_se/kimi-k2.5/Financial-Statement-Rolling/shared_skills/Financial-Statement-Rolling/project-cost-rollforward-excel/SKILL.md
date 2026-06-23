---
name: project-cost-rollforward-excel
description: Build capitalized project cost rollforward workbooks with revision filtering, override processing, and amortization tracking. Use for ERP implementations, leasehold improvements, or any capitalized project with multiple revisions, monthly adds/releases, and useful life amortization. Trigger when you see 'project cost', 'capitalized', 'revision', 'adds/releases', or 'implementation' with month-by-month rollforwards.
---

# Capitalized Project Cost Rollforwards

Build Excel workbooks tracking capitalized project costs with revision management, override processing, and amortization schedules.

## Pattern Recognition

Use this skill when the data shows:
- **Multiple revisions** of the same project (highest revision wins)
- **Active/inactive flags** requiring filtering
- **Override CSV** with notes or value adjustments
- **Monthly adds/releases** across Jun-Sep or other periods
- Keywords: **project cost**, **capitalized**, **ERP implementation**, **leasehold improvements**, **revision**, **wave**, **change order**

## Data Structure

**Source JSON (`*_project_cost_rollforward.json`):**
```json
{
  "accounts": [
    {
      "sheet_name": "Cap Impl #1460",
      "groups": [
        {
          "portfolio": "ERP",
          "items": [
            {
              "row_id": "PC-101",
              "revision": 2,
              "active": true,
              "vendor_name": "Aether Consulting",
              "opening_balance": 0,
              "months": {
                "jun": {"adds": 22000, "release": 2750, "ending_balance": 19250},
                "jul": {"adds": 0, "release": 2750, "ending_balance": 16500}
              },
              "useful_life_months": 8,
              "memo": "ERP implementation wave 2",
              "source_account": 1460
            }
          ]
        }
      ]
    }
  ]
}
```

**Overrides CSV (`schedule_overrides.csv`):**
```csv
row_id,notes_override,jul_adds,jul_release,jul_ending_balance
PC-104,Testing expansion,,,
PC-110,Change order approved,4500,,15375
```

**GL Balances JSON (`gl_balances.json`):**
```json
{
  "cap_impl_1460": {"jun": 32375, "jul": 40875, "aug": 40375, "sep": 29875}
}
```

## Critical: Revision Filtering Logic

**Keep highest revision only, filter inactive:**
```python
from collections import defaultdict

def filter_items(items):
    by_row_id = defaultdict(list)
    for item in items:
        by_row_id[item['row_id']].append(item)
    
    result = []
    for row_id, versions in by_row_id.items():
        # Keep only active items with highest revision
        active = [v for v in versions if v.get('active', True)]
        if active:
            highest = max(active, key=lambda x: x['revision'])
            result.append(highest)
    return result
```

## Critical: Override Processing

Apply overrides AFTER revision filtering:
```python
def apply_override(item, override):
    # Notes override
    if override.get('notes_override'):
        item['memo'] = override['notes_override']
    
    # Value overrides for specific months
    for month in ['jun', 'jul', 'aug', 'sep']:
        for field in ['adds', 'release', 'ending_balance']:
            key = f"{month}_{field}"
            if override.get(key):
                item['months'][month][field] = float(override[key])
```

## Control Row Positioning

**CRITICAL:** Verify exact row numbers from task spec. Common variants:

| Pattern | Period Totals | Ending Balance | GL Balance | Variance |
|---------|---------------|----------------|------------|----------|
| Standard (4 data rows) | Row 9 | Row 10 | Row 12 | Row 11 |
| Extended (4+ data rows) | Row 10 | Row 11 | Row 13 | Row 12 |

**Verify before writing:**
```python
# Check spec for exact rows
assert period_totals_row == expected_row, f"Spec requires row {expected_row}"
```

## Formula Patterns

**Period Totals row:**
- `B{row}: =SUM(B{first_data}:B{last_data})` for beginning balance
- `C{row}: =SUM(C{first_data}:C{last_data})` for Jun adds
- Continue through column N
- `O{row}: =C{row}+F{row}+I{row}+L{row}` (sum of all adds columns)

**Ending Balance row (rolling chain):**
- `E{row}: =B{row}+C{row}-D{row}` (Jun ending)
- `H{row}: =E{row}+F{row}-G{row}` (Jul ending)
- `K{row}: =H{row}+I{row}-J{row}` (Aug ending)
- `N{row}: =K{row}+L{row}-M{row}` (Sep ending)
- `O{row}: =D{row}+G{row}+J{row}+M{row}` (total releases)

**GL Balance row:**
- Hardcoded values from `gl_balances.json` in E, H, K, N
- `O{row}: =O{period_totals}-O{ending_balance}`

**Variance row:**
- `O{row}: =O{gl_balance}-N{gl_balance}` or `=O{gl_row}-N{gl_row}`

## Column Mapping

| CSV/JSON Field | Excel Column | Content |
|----------------|--------------|---------|
| `vendor_name` | A | Vendor/contractor name |
| `opening_balance` | B | Beginning balance |
| `{month}_adds` | C, F, I, L | Capitalized additions |
| `{month}_release` | D, G, J, M | Amortization/releases |
| `{month}_ending_balance` | E, H, K, N | Calculated ending |
| `useful_life_months` | O | Useful life (Period Totals) / Total releases (Ending Balance) |
| `memo` | P | Notes |
| `source_account` | Q | Account number |

## Summary Sheet Structure

```
Row 1: Company Name
Row 2: Report Title
Row 3: Period Ending

Row 5: Account Header (e.g., "Cap Impl #1460")
Row 7: Period Total Amortization → ='{Sheet}'!O{period_row}
Row 8: Ending Balance → ='{Sheet}'!O{ending_row}
Row 9: GL Balance → ='{Sheet}'!O{gl_row}

Row 11: Second Account Header
Row 12: Period Total Amortization → ='{Sheet2}'!O{period_row}
Row 13: Ending Balance → ='{Sheet2}'!O{ending_row}
Row 14: GL Balance → ='{Sheet2}'!O{gl_row}

Row 16: Total GL Balance → =B9+B14
```

**VERIFY EXACT ROWS:** Different specs use 6/7/8 or 7/8/9 or other variants.

## Verification Checklist

```python
from openpyxl import load_workbook

def verify_structure(wb, spec):
    """Verify workbook matches spec."""
    # Check sheet order
    assert wb.sheetnames[0] == 'Project Cost Summary'
    
    # Check revision filtering (highest active revision kept)
    # Check overrides applied
    # Check control row formulas match spec rows
    # Check cross-references in summary
    
    summary = wb['Project Cost Summary']
    detail = wb['Cap Impl #1460']
    
    # Verify formula strings, not calculated values
    assert detail[f'O{spec["period_totals_row"]}'].value.startswith('=C')
    assert '=B' in str(detail[f'E{spec["ending_balance_row"]}'].value)
    
    # Verify cross-references
    assert f"'Cap Impl #1460'!O{spec['gl_balance_row']}" in str(summary['B9'].value)
```

## Anti-Patterns

- **Don't forget revision filtering** — Multiple revisions exist; keep highest active only
- **Don't apply overrides before filtering** — Overrides apply to surviving items only
- **Don't assume fixed row numbers** — Verify spec for Period Totals/Ending/GL Balance rows
- **Don't skip inactive filtering** — Check `active` flag on each item
- **Don't use deferred revenue formulas** — This uses rolling balance, not cumulative
- **Don't validate by Python calculation** — Verify formula strings match expected pattern

## Differences from Prepaid/Amortizing Assets

| Aspect | Prepaid Assets | Project Costs |
|--------|---------------|---------------|
| Revision handling | None | Keep highest active revision |
| Override processing | Rare | Common (notes and values) |
| Data source | Single CSV | JSON with groups/portfolios |
| Portfolio grouping | No | Yes (ERP, Infrastructure, etc.) |

## Troubleshooting

**Wrong item count:**
- Check revision filtering kept highest, not lowest
- Verify inactive items were excluded
- Confirm duplicates properly collapsed

**Wrong ending balances:**
- Verify rolling chain formulas (not cumulative)
- Check override values applied correctly
- Confirm prior period ending flows to next period beginning

**Summary links broken:**
- Re-read spec for exact row numbers
- Verify O-column references (different row in different sheets)
- Check sheet name spelling matches exactly

## Scripts

- `scripts/build_project_cost_rollforward.py` — Reusable builder with revision filtering and override processing
