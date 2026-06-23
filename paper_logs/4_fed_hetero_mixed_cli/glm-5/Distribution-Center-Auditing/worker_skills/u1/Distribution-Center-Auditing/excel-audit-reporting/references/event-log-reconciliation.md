# Event Log Reconciliation Pattern

## Overview
When auditing planned items (manifests, orders, shipments) against actual events (scans, dispositions, transactions) from a separate log file, use this pattern to join, filter, and compute exception flags.

## Workflow

### 1. Load Both Sources
```python
import openpyxl

manifest_wb = openpyxl.load_workbook('Manifest.xlsx')
event_wb = openpyxl.load_workbook('ScanLog.xlsx')

manifest_ws = manifest_wb.active
event_ws = event_wb.active

manifest_rows = list(manifest_ws.iter_rows(min_row=2, values_only=True))
event_rows = list(event_ws.iter_rows(min_row=2, values_only=True))
```

### 2. Filter Events by Qualifying Status
Only count events with the specified status (e.g., `LOADED`, `COMPLETED`).

```python
QUALIFYING_STATUS = 'LOADED'

filtered_events = []
for row in event_rows:
    status = row[status_col_idx]
    if status and str(status).strip().upper() == QUALIFYING_STATUS:
        filtered_events.append(row)
```

### 3. Deduplicate: Select Latest Event Per Key
When multiple events exist for the same key, keep only the latest by timestamp.

```python
from datetime import datetime

event_lookup = {}  # (id1, id2) -> (timestamp, value)
for row in filtered_events:
    key = (str(row[id1_col]).strip(), str(row[id2_col]).strip())
    ts = row[timestamp_col]
    value = str(row[value_col]).strip()
    
    if key not in event_lookup or ts > event_lookup[key][0]:
        event_lookup[key] = (ts, value)
```

### 4. Compute Flags for Each Manifest Row

```python
results = []
for row in manifest_rows:
    key = (str(row[id1_col]).strip(), str(row[id2_col]).strip())
    planned_value = str(row[planned_col]).strip()
    
    if key not in event_lookup:
        missing = 1
        mismatch = 0
        error_summary = 'Missing Event'
    else:
        missing = 0
        actual_value = event_lookup[key][1]
        mismatch = 0 if planned_value.upper() == actual_value.upper() else 1
        error_summary = 'Mismatch' if mismatch else 'None'
    
    total_errors = missing + mismatch
    results.append(list(row) + [missing, mismatch, total_errors, error_summary])
```

### 5. Aggregate Summary
Group by specified keys, sum flags, filter to error rows, add Grand Total.

```python
from collections import defaultdict

agg = defaultdict(lambda: [0, 0, 0])  # [missing_sum, mismatch_sum, total_sum]
for row in results:
    group_key = (row[group_col1_idx], row[group_col2_idx])
    agg[group_key][0] += row[missing_col_idx]
    agg[group_key][1] += row[mismatch_col_idx]
    agg[group_key][2] += row[total_col_idx]

# Filter to error groups
error_agg = {k: v for k, v in agg.items() if v[2] > 0}

# Sort deterministically
sorted_keys = sorted(error_agg.keys())
summary_rows = [[*k, *v] for k, v in sorted_keys]

# Grand Total
if summary_rows:
    totals = [sum(r[i] for r in summary_rows) for i in range(2, 5)]
    summary_rows.append(['Grand Total', '-', *totals])
```

## Common Variations

| Task Type | Key Columns | Status Filter | Mismatch Check |
|-----------|-------------|---------------|----------------|
| Returns Disposition | (Return ID, Line ID) | COMPLETED | Final Disposition vs Planned Disposition |
| Outbound Manifest | (Shipment ID, Carton ID) | LOADED | Scanned Zone vs Planned Zone |
| Inbound Receipt | (PO Number, SKU) | RECEIVED | Received Qty vs Expected Qty |
| Dock Audit | (Trailer ID, Pallet ID) | SCANNED | Actual Location vs Planned Location |

## Anti-Patterns

- **Do not** skip status filtering — PENDING or VOID events should not count as completed.
- **Do not** assume one event per key — always deduplicate by latest timestamp.
- **Do not** compare values without normalization — use `.strip().upper()` for case-insensitive match.
- **Do not** forget to handle `None` values from openpyxl before string operations.
