# Multi-File Excel Join Pattern

## Overview
When audit data spans multiple Excel files instead of multiple sheets in one workbook, load each file independently and join in Python using dictionary lookups.

## Pattern

```python
import openpyxl

# Load each file
plan_wb = openpyxl.load_workbook('Plan.xlsx')
event_wb = openpyxl.load_workbook('Events.xlsx')
alias_wb = openpyxl.load_workbook('Aliases.xlsx')

# Extract rows
plan_rows = list(plan_wb.active.iter_rows(min_row=2, values_only=True))
event_rows = list(event_wb.active.iter_rows(min_row=2, values_only=True))

# Build lookup dicts
event_lookup = {}
for row in event_rows:
    key = (row[0], row[1])  # e.g., (Return ID, Line ID)
    event_lookup[key] = row

# Join during iteration
for plan_row in plan_rows:
    key = (plan_row[0], plan_row[1])
    matching_event = event_lookup.get(key)
    # Process...
```

## Key Considerations

1. **Key construction**: Use tuple of identifier columns. Strip whitespace and normalize case if needed.
2. **Missing keys**: Use `.get(key)` and handle `None` gracefully (e.g., flag as missing).
3. **Duplicate keys**: If multiple rows share a key, decide selection criteria (latest timestamp, highest priority, etc.) before building the lookup.
4. **Memory**: For large files (>100k rows), consider streaming or chunked processing. For typical audit files (<10k rows), full load is fine.

## Alias Normalization

```python
alias_map = {}
for row in alias_rows:
    alias_val, standard = row[0], row[1]
    if alias_val is not None:
        alias_map[str(alias_val).strip().lower()] = str(standard).strip()

def normalize(value, alias_map):
    if value is None:
        return None
    return alias_map.get(str(value).strip().lower(), str(value).strip())
```

## Event Status Filtering

```python
QUALIFYING_STATUSES = {'COMPLETED'}  # Adjust per task

def is_qualifying(status):
    if status is None:
        return False
    return str(status).strip().upper() in QUALIFYING_STATUSES
```
