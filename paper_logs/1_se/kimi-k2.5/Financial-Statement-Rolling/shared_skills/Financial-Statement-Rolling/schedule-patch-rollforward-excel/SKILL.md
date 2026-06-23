---
name: schedule-patch-rollforward-excel
description: Build accrual rollforward workbooks from schedule data with patch overrides and row insertions. Use when you see schedule_patch.csv with 'override' and 'insert' actions, status-based filtering (open/superseded), or row-level field updates applied to base schedules. Common for rebate reserves, partner accruals, or any liability schedule requiring surgical updates before rollforward generation.
---

# Schedule Patch Rollforward Workbooks

Build Excel workbooks from base schedule data with selective overrides and insertions applied before rollforward calculation.

## When to Use This Skill

Use this skill (not vanilla accrual-rollforward) when:
- **schedule_patch.csv** exists with `action` column (`override` or `insert`)
- Base schedules have **status flags** requiring filtering (`open` vs `superseded`)
- Row-level **field overrides** must be applied (e.g., update only `sep_accruals` for one row)
- New rows must be **inserted** into existing schedules
- Keywords: **schedule patch**, **override**, **insert**, **status=open**, **superseded**

## Data Processing Pipeline

**Step 1: Filter by status**
```python
# Keep only 'open' rows, discard 'superseded'
filtered = [row for row in base_data if row['status'] == 'open']
```

**Step 2: Process patches (AFTER filtering)**
```python
for patch in patch_data:
    if patch['action'] == 'override':
        # Find matching row_key, update specified fields only
        # Other fields remain from base
    elif patch['action'] == 'insert':
        # Create new row from patch data, append to list
```

**Step 3: Sort and build**
- Sort by name (alphabetical for consistency)
- Build detail sheets with accrual rollforward formulas

## Patch Action Types

| Action | Behavior | Fields Required |
|--------|----------|-----------------|
| `override` | Modify existing row by `row_key` | `target_sheet`, `row_key`, fields to change |
| `insert` | Add new row with full data | `target_sheet`, all row fields including `row_key` |

## Critical: Field-Level vs Row-Level Patches

**Override (field-level):**
```csv
action,target_sheet,row_key,sep_accruals,comments
override,Channel Rebates #6120,CR-09,4000,Quarterly true-up
```
- Keeps all base data for CR-09
- Changes only `sep_accruals` to 4000
- Updates `comments` if provided

**Insert (row-level):**
```csv
action,target_sheet,row_key,partner,beginning_balance,...,comments
insert,MDF Accrual #6125,MDF-07,Echo Events,0,...,October summit
```
- Creates entirely new row
- All fields must be present in patch

## Verification Checklist

```python
# 1. Status filtering worked
assert 'Legacy Partner' not in [r['partner'] for r in channel_data]
assert len(channel_data) == 3  # Not 4 (superseded excluded)

# 2. Override applied
corevista = [r for r in channel_data if r['row_key'] == 'CR-09'][0]
assert corevista['sep_accruals'] == 4000  # Patched, not 0
assert corevista['sep_ending_balance'] == 5500  # Recalculated

# 3. Insert applied
assert 'Echo Events' in [r['partner'] for r in mdf_data]
assert len(mdf_data) == 3  # Base 2 + insert 1

# 4. Sort order
assert [r['partner'] for r in channel_data] == sorted(
    [r['partner'] for r in channel_data])
```

## Formula Pattern

Same rolling chain as accrual-rollforward-excel:
- Row 9: Period Totals with `=SUM()`
- Row 10: Ending Balance with `=prior+adds-releases`
- Row 11: Variance `=O12-N12`
- Row 12: GL Balance (hardcoded) with `=O9-O10`

## Column Mapping

| Source Field | Excel Column | Notes |
|--------------|--------------|-------|
| `partner` | A | Sorted alphabetically |
| `beginning_balance` | B | |
| `{month}_adds` | C, F, I, L | Accruals/capitalized |
| `{month}_release` | D, G, J, M | Utilization/releases |
| `{month}_ending_balance` | E, H, K, N | Calculated |
| `term_months` | O | Reserve months |
| `comments` | P | Notes |
| `account_number` | Q | Expense account |

## Anti-Patterns

- **Don't apply patches before status filtering** — patches may reference superseded rows
- **Don't treat override as full row replacement** — only change specified fields
- **Don't forget to recalculate ending_balance after override** — formula depends on patched adds/releases
- **Don't hardcode row positions** — data count varies with inserts/deletes
- **Don't skip alphabetical sorting** — specs usually require sorted partners

## Troubleshooting

**Wrong row count:**
- Check status filter excluded superseded rows
- Verify insert rows actually appended
- Confirm no duplicate row_key after insert

**Override not applied:**
- Verify row_key exists in filtered data
- Check field names match exactly (case-sensitive)
- Ensure override happens after filtering, before sorting

**Ending balance wrong:**
- Recalculate: beginning + adds - release
- Verify prior period ending flows to next period beginning (if applicable)

## See Also

- `accrual-rollforward-excel` — Base rollforward pattern without patching
- `project-cost-rollforward-excel` — For JSON-based revision filtering (different pattern)
