---
name: project-cost-rollforward
description: Build project cost rollforward workbooks for capital implementation and leasehold improvement accounts. Use when source data is nested JSON with revision tracking, CSV overrides apply to specific row_ids, and the rollforward tracks Cap Adds and Amortization per period. Distinct from deferred-revenue or accrual rollforwards: uses running balance formulas in Ending Balance row, links summary to column O (total adds/amortization), and requires revision deduplication.
---

# Project Cost Rollforward Workbook Builder

## When to Use

- Capital implementation cost tracking (Cap Impl accounts)
- Leasehold improvement amortization schedules
- Project cost rollforwards with vendor-level line items
- Source data in nested JSON with revision numbers and active flags
- CSV overrides that patch specific row_ids with partial field updates

## Key Differences from Financial Rollforward Skill

| Aspect | Financial Rollforward | Project Cost Rollforward |
|--------|----------------------|--------------------------|
| Ending Balance row | SUM of data rows | Running balance: E=B+C-D, H=E+F-G |
| Variance formula | GL - Calculated Ending | O(GL row) - N(GL row) |
| Summary links | Final period ending balance column | Column O (total adds/amortization) |
| Data source | Flat CSVs | Nested JSON with revisions |
| Dedup | Not needed | Keep highest revision per row_id |
| Overrides | Not typical | CSV patches specific row_ids |

## Data Processing Workflow

### 1. Flatten and Filter JSON

Source JSON has structure: `accounts[] → groups[] → items[]`. Each item has:
- `row_id`, `revision`, `active` (boolean)
- `vendor_name`, `opening_balance`, `useful_life_months`, `memo`, `source_account`
- `months`: `{jun, jul, aug, sep}` each with `{adds, release, ending_balance}`

**Filter**: Keep only items where `active == true`.

**Deduplicate**: Group by `row_id`, keep the item with the highest `revision` number.

```python
from collections import defaultdict

# Flatten
all_items = []
for account in data['accounts']:
    for group in account['groups']:
        for item in group['items']:
            if item['active']:
                all_items.append(item)

# Deduplicate by row_id, keep highest revision
by_row_id = defaultdict(list)
for item in all_items:
    by_row_id[item['row_id']].append(item)

deduped = []
for row_id, items in by_row_id.items():
    deduped.append(max(items, key=lambda x: x['revision']))
```

### 2. Apply CSV Overrides

CSV columns: `row_id, notes_override, jul_adds, jul_release, jul_ending_balance, aug_adds, ...`

For each override row:
- Match by `row_id`
- If a field is non-empty in CSV, replace the corresponding field in the item
- If a field is empty in CSV, keep the original JSON value
- `notes_override` replaces `memo`

```python
import csv

with open(overrides_csv) as f:
    for row in csv.DictReader(f):
        rid = row['row_id']
        for item in deduped:
            if item['row_id'] == rid:
                if row['notes_override']:
                    item['memo'] = row['notes_override']
                for month in ['jul', 'aug', 'sep']:
                    for field in ['adds', 'release', 'ending_balance']:
                        col = f'{month}_{field}'
                        if row[col]:
                            item['months'][month][field] = float(row[col])
```

### 3. Sort

Sort line items alphabetically by `vendor_name` before writing to the sheet.

## Column Layout

| Col | Header | Content |
|-----|--------|---------|
| A | Vendor | Vendor name |
| B | Beginning Balance | `opening_balance` |
| C | Jun Cap Adds | `months.jun.adds` |
| D | Jun Amortization | `months.jun.release` |
| E | Jun Ending Balance | `months.jun.ending_balance` |
| F | Jul Cap Adds | `months.jul.adds` |
| G | Jul Amortization | `months.jul.release` |
| H | Jul Ending Balance | `months.jul.ending_balance` |
| I | Aug Cap Adds | `months.aug.adds` |
| J | Aug Amortization | `months.aug.release` |
| K | Aug Ending Balance | `months.aug.ending_balance` |
| L | Sep Cap Adds | `months.sep.adds` |
| M | Sep Amortization | `months.sep.release` |
| N | Sep Ending Balance | `months.sep.ending_balance` |
| O | Useful Life Months | `useful_life_months` |
| P | Notes | `memo` |
| Q | Source Account | `source_account` |

Headers start at row 5. Data rows start at row 6.

## Control Row Formulas

Compute positions dynamically:
```python
totals_row = start_row + len(data_rows)
ending_row = totals_row + 1
variance_row = ending_row + 1
gl_row = variance_row + 1
```

### Period Totals (row N+1)

- Columns B through N: `=SUM(B{start}:B{end})` etc.
- Column O: `=C{totals_row}+F{totals_row}+I{totals_row}+L{totals_row}` (sum of adds across periods)

### Ending Balance (row N+2) — RUNNING BALANCE FORMULAS

**CRITICAL**: Unlike financial rollforwards, this row uses running balance formulas, NOT SUM.

- B: `=B{totals_row}` (copy beginning balance total)
- E: `=B{ending_row}+C{totals_row}-D{totals_row}`
- H: `=E{ending_row}+F{totals_row}-G{totals_row}`
- K: `=H{ending_row}+I{totals_row}-J{totals_row}`
- N: `=K{ending_row}+L{totals_row}-M{totals_row}`
- O: `=D{totals_row}+G{totals_row}+J{totals_row}+M{totals_row}` (total amortization)

**Note**: These formulas reference the Ending Balance row's own cells (B, E, H, K) for the running balance chain. This is correct and NOT a circular reference because each formula references a different column on the same row, not its own cell.

### GL Balance (row N+4)

- Columns E, H, K, N: Hard-coded values from `gl_balances.json` keyed by account and period
- Column O: `=O{totals_row}-O{ending_row}` (total adds minus total amortization)

### Variance (row N+3)

- Column O: `=O{gl_row}-N{gl_row}` (GL Balance column O minus GL Balance column N)

## Summary Sheet

Link to **column O** of control rows, NOT to ending balance columns:

```python
# Cap Impl section
B7 = "='Cap Impl #1460'!O{totals_row}"      # Period Totals O
B8 = "='Cap Impl #1460'!O{ending_row}"      # Ending Balance O
B9 = "='Cap Impl #1460'!O{gl_row}"          # GL Balance O

# Leasehold section
B12 = "='Leasehold #1465'!O{totals_row}"
B13 = "='Leasehold #1465'!O{ending_row}"
B14 = "='Leasehold #1465'!O{gl_row}"

# Total
B16 = "=B9+B14"
```

## Anti-Patterns

| Issue | Wrong | Right |
|-------|-------|-------|
| Ending Balance formulas | `=SUM(E6:E8)` | Running balance: `=B{r}+C{totals}-D{totals}` |
| Summary links | Link to column N (Sep Ending) | Link to column O (total adds/amortization) |
| Revision handling | Use all items | Deduplicate by row_id, keep highest revision |
| Active filtering | Include all items | Filter to `active == true` only |
| CSV overrides | Replace entire item | Patch only non-empty fields |
| Variance formula | `=O{ending}-N{ending}` | `=O{gl}-N{gl}` |
| GL column O | Hard-coded value | Formula: `=O{totals}-O{ending}` |

## Verification

Run `scripts/verify_workbook.py` from the `financial-rollforward-workbook` skill directory to check for circular references and structural issues. Note: The verifier may flag same-row references in the Ending Balance row as circular; verify manually that formulas reference different columns (e.g., E references B, C, D — not E itself).

## Validation Checklist

1. JSON flattened, filtered to active, deduplicated by highest revision
2. CSV overrides applied correctly (only non-empty fields replaced)
3. Line items sorted by vendor name
4. Period Totals: SUM for B:N, adds formula for O
5. Ending Balance: Running balance chain (B→E→H→K→N), O = total amortization
6. GL Balance: Hard-coded values in E/H/K/N, O = totals O - ending O
7. Variance: O = GL O - GL N
8. Summary: Links to column O of control rows
9. Cross-sheet references use single quotes for sheet names with spaces or `#`