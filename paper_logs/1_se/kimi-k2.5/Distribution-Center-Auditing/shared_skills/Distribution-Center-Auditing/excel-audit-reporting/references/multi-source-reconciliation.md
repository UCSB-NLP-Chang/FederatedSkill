# Multi-Source Reconciliation with Alias Normalization

Pattern for auditing across multiple related datasets where values have semantic equivalents (aliases) that must be normalized before comparison.

## Trigger Scenarios

- Planned vs actual disposition/destination/status comparisons
- Master data validation against reference tables
- Cross-system reconciliation where codes vary by source
- Inventory, returns, logistics, or compliance audits with lookup tables

## Data Structure Pattern

```
Source A (Plan/Request):     Return ID, Line ID, Planned Value, ...
Source B (Events/Actual):    Return ID, Line ID, Event Status, Final Value, ...
Reference Table (Aliases):   Alias Value -> Standard Value
```

## Core Workflow

### 1. Load All Sources

```python
plan = pd.read_excel('Plan.xlsx')
events = pd.read_excel('Events.xlsx')
aliases = pd.read_excel('Aliases.xlsx')  # Columns: Alias, Standard
```

### 2. Build Normalization Dictionary

```python
# Case-insensitive mapping from alias to standard
alias_map = dict(zip(
    aliases['Alias'].str.lower(),
    aliases['Standard'].str.upper()
))
```

### 3. Identify Latest Completed Events

Critical: Events may have multiple statuses (PENDING, COMPLETED, VOID). Use only latest COMPLETED.

```python
# Filter to COMPLETED only, then get latest per Return+Line
completed = events[events['Event Status'] == 'COMPLETED'].copy()
completed['Event Time'] = pd.to_datetime(completed['Event Time'])
latest = completed.sort_values('Event Time').groupby(['Return ID', 'Line ID']).last().reset_index()
```

### 4. Merge and Calculate Exceptions

```python
# Left join: all planned items must have events
merged = plan.merge(
    latest[['Return ID', 'Line ID', 'Event Status', 'Final Disposition']],
    on=['Return ID', 'Line ID'],
    how='left'
)

# Exception 1: Missing final event (no COMPLETED status)
merged['Missing Final Event'] = merged['Event Status'].isna().astype(int)

# Exception 2: Disposition mismatch (after normalization)
def normalize_and_check(row):
    if pd.isna(row['Final Disposition']):
        return 0
    planned = row['Planned Disposition'].upper()
    actual_normalized = alias_map.get(row['Final Disposition'].lower(), row['Final Disposition'].upper())
    return int(planned != actual_normalized)

merged['Disposition Mismatch'] = merged.apply(normalize_and_check, axis=1)
```

### 5. Summary Aggregation

Group by dimensions relevant to accountability (Warehouse, Carrier, Handler, etc.)

```python
summary = merged.groupby(['Warehouse', 'Carrier']).agg({
    'Missing Final Event': 'sum',
    'Disposition Mismatch': 'sum',
    'Total Errors': 'sum'
}).reset_index()
```

## Key Decision Rules

| Situation | Rule |
|-----------|------|
| Multiple event statuses | Filter to COMPLETED only; PENDING/VOID count as "missing final event" |
| Case variations in values | Normalize via alias table; never hardcode in exception logic |
| Unmapped aliases | Default to uppercase original; flag for alias table update |
| No event record at all | Left join produces NaN → count as missing final event |
| Planned item with VOID event | VOID ≠ COMPLETED → count as missing final event |

## Anti-Patterns

| Anti-Pattern | Why It Fails |
|-------------|--------------|
| Hardcode alias mappings in Python | Brittle; new aliases break the audit silently |
| Use string equality without normalization | "Liquidation" ≠ "LIQUIDATE" causes false mismatches |
| Treat PENDING as valid final event | Incomplete processing; should flag as missing |
| Inner join instead of left join | Drops unprocessed items from audit scope |
| Ignore Event Time for multiple events | May use outdated completion instead of latest |

## Validation Checklist

- [ ] All Return+Line combinations from plan appear in output (no dropped rows)
- [ ] Alias table covers all observed values in event data
- [ ] PENDING and VOID statuses correctly flagged as missing
- [ ] Normalized comparison produces expected matches (spot-check 3-5)
- [ ] Summary totals equal sum of detail exception columns

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| All rows show disposition mismatch | Alias map case sensitivity | Ensure keys are lower(), values match planned case |
| Missing events not detected | Inner join used | Switch to `how='left'` merge |
| False mismatches on valid data | Unmapped alias values | Update alias table; add validation for unmapped |
| Duplicate rows in summary | Multiple events per Return+Line | Pre-aggregate to latest COMPLETED before merge |

## Example: Returns Disposition Audit

See trace `harbor_returns_disposition_audit__uPkE9Bz` for full implementation:
- 12 return plan lines
- 12 event log entries (2 PENDING, 1 VOID, 9 COMPLETED)
- Alias table normalized "Liquidation"→"LIQUIDATE", "Scrapped"→"SCRAP", etc.
- Result: 2 Missing Final Events, 0 Disposition Mismatches
