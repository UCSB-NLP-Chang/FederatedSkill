# Cycle Count Variance Audit Pattern

## Overview
Audits cycle count plan lines against count event logs to identify missing final counts and approval threshold violations.

## Input Structure
- **Plan file**: Contains Facility, Session ID, Bin ID, Product ID, Expected Qty, Allowed Variance, Approval Needed (YES/NO)
- **Event log**: Contains Facility, Session ID, Bin ID, Event Time, Event Type (PRELIMINARY/FINAL/VOID), Count Qty, Approval Code
- **Template file**: May contain an Overview sheet to preserve in output

## Flag Definitions

### Missing Final Count
`1` if no FINAL event exists for the plan line (Facility + Session ID + Bin ID), OR if the FINAL event has NaN/null Count Qty.

```python
if key not in final_events:
    missing = 1
elif final_events[key][0] is None:  # Count Qty is NaN
    missing = 1
else:
    missing = 0
```

### Approval Gap
`1` if ALL of the following are true:
1. Approval Needed = 'YES'
2. A valid FINAL count exists (Count Qty is not NaN)
3. Absolute variance |Expected Qty - Count Qty| > Allowed Variance

```python
if missing == 1:
    approval_gap = 0  # Cannot have approval gap without valid count
else:
    count_qty = final_events[key][0]
    variance = abs(expected_qty - count_qty)
    approval_gap = 1 if (approval_needed == 'YES' and variance > allowed_variance) else 0
```

### Total Errors
`Missing Final Count + Approval Gap` (integer sum)

### Error Summary
Comma-separated list of error names, or literal string `"None"` if no errors.

```python
errors = []
if missing:
    errors.append('Missing Final Count')
if approval_gap:
    errors.append('Approval Gap')
error_summary = ', '.join(errors) if errors else 'None'  # STRING, not Python None
```

## Event Log Processing

1. **Filter to FINAL events only**: Ignore PRELIMINARY, VOID, and other statuses.
2. **Deduplicate by latest timestamp**: If multiple FINAL events exist for the same key, keep the one with the latest Event Time.
3. **Handle NaN Count Qty**: A FINAL event with NaN/null Count Qty is treated as missing.

```python
final_events = {}  # (Facility, Session ID, Bin ID) -> (Count Qty, Event Time)
for row in event_rows:
    if str(row[event_type_col]).strip().upper() != 'FINAL':
        continue
    key = (str(row[facility_col]).strip(), str(row[session_col]).strip(), str(row[bin_col]).strip())
    evt_time = row[time_col]
    count_qty = row[count_col]  # May be None/NaN
    
    if key not in final_events or evt_time > final_events[key][1]:
        final_events[key] = (count_qty, evt_time)
```

## Summary Aggregation
Group by (Facility, Session ID), sum flags, filter to Total Errors > 0, add Grand Total row.

```python
from collections import defaultdict
agg = defaultdict(lambda: [0, 0, 0])  # [missing_sum, approval_gap_sum, total_sum]
for row in formatted_rows:
    key = (row[facility_idx], row[session_idx])
    agg[key][0] += row[missing_idx]
    agg[key][1] += row[approval_gap_idx]
    agg[key][2] += row[total_idx]

error_agg = {k: v for k, v in agg.items() if v[2] > 0}
sorted_keys = sorted(error_agg.keys())
summary_rows = [[k[0], k[1], v[0], v[1], v[2]] for k, v in sorted_keys]

if summary_rows:
    totals = [sum(r[i] for r in summary_rows) for i in range(2, 5)]
    summary_rows.append(['Grand Total', '-', *totals])
```

## Preserving Template Sheets

If the input includes a template with an Overview sheet, copy it to the output before adding other sheets:

```python
template_wb = openpyxl.load_workbook('Cycle_Template.xlsx')
out_wb = openpyxl.Workbook()
out_wb.remove(out_wb.active)

# Copy Overview first
if 'Overview' in template_wb.sheetnames:
    src_ws = template_wb['Overview']
    out_ws = out_wb.create_sheet('Overview')
    for row in src_ws.iter_rows(values_only=True):
        out_ws.append(row)

# Then add RawData, Formatted Data, Summary
```

## Critical Rules

1. **Error Summary must be string "None"**, not Python None, not empty string.
2. **NaN Count Qty = Missing**: A FINAL event with null Count Qty counts as missing.
3. **Approval Gap requires valid count**: If count is missing/NaN, Approval Gap = 0.
4. **Filter events to FINAL only**: PRELIMINARY and VOID events do not count.
5. **Latest FINAL wins**: If multiple FINAL events exist, use the one with latest timestamp.

## Common Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Using Python None for Error Summary | Empty cells or NaN in output | Use string `'None'` explicitly |
| Counting PRELIMINARY events | Missing Final Count undercounted | Filter to `Event Type == 'FINAL'` only |
| Ignoring NaN Count Qty | False negatives for missing counts | Check `count_qty is None` after filtering |
| Approval Gap when count missing | Incorrect flag computation | Set `approval_gap = 0` when `missing = 1` |