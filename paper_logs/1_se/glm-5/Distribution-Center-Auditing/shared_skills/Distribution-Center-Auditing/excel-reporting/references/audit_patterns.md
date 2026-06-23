# Common Audit Calculation Patterns

Reusable patterns for building audit and exception reports from transactional data.

## Multi-File Join Pattern

When an audit requires joining data across multiple Excel files (e.g., plan vs. actual, or master data vs. transactions):

```python
from openpyxl import load_workbook

# Read primary data file
wb_plan = load_workbook('/path/to/Return_Plan.xlsx')
plan_ws = wb_plan.active
plan_data = list(plan_ws.iter_rows(values_only=True))
plan_headers = plan_data[0]
plan_rows = plan_data[1:]

# Read reference/event file
wb_events = load_workbook('/path/to/Event_Log.xlsx')
events_ws = wb_events.active
events_data = list(events_ws.iter_rows(values_only=True))
event_headers = events_data[0]
event_rows = events_data[1:]

# Build lookup from events by composite key
completed_events = set()
for row in event_rows:
    row_dict = dict(zip(event_headers, row))
    if row_dict['Event Status'] == 'COMPLETED':
        key = (row_dict['Return ID'], row_dict['Line ID'])
        completed_events.add(key)

# Check each plan row against events
for row in plan_rows:
    row_dict = dict(zip(plan_headers, row))
    key = (row_dict['Return ID'], row_dict['Line ID'])
    missing_event = 0 if key in completed_events else 1
```

### Pattern: Multiple Lookup Tables

When joining multiple reference files:

```python
# Build alias normalization lookup
wb_alias = load_workbook('/path/to/Alias_Mapping.xlsx')
alias_ws = wb_alias.active
alias_map = {}
for row in alias_ws.iter_rows(values_only=True):
    if row[0] == 'Alias':  # skip header
        continue
    alias_map[row[0]] = row[1]  # alias -> standard value

# Normalize values using alias map
def normalize_disposition(raw_value):
    return alias_map.get(raw_value, raw_value)  # fallback to original if no alias
```

## Lookup Table Pattern

When source workbooks contain reference data in one sheet and transactional data in another, build a lookup dictionary from the reference sheet:

```python
from openpyxl import load_workbook

wb = load_workbook('/path/to/source.xlsx')

# Read reference/rules sheet into a lookup dict
rules_ws = wb['SLA_Rules']  # or 'Config', 'Reference', 'Thresholds'
rules = {}
for row in rules_ws.iter_rows(values_only=True):
    if row[0] == 'Key Column Header':  # skip header row
        continue
    key = row[0]  # e.g., 'P1', 'P2'
    rules[key] = {
        'Max Hours': row[1],
        'Required': row[2]
    }
# Example: rules = {'P1': {'Max Hours': 4, 'Required': 'Y'}, ...}

# Apply rules to transactional data
tickets_ws = wb['Tickets']
for row in tickets_ws.iter_rows(values_only=True):
    priority = row['Priority Tier']
    rule = rules.get(priority, {})
    # Use rule values for validation
    if row['Open Age Hours'] > rule.get('Max Hours', 999):
        sla_breach = 1
```

### Conditional Flags Based on Lookup Values

When error conditions depend on both row data AND lookup table values:

```python
# SLA Breach: compare actual value against threshold from lookup
sla_breach = 1 if row['Open Age Hours'] > rules[row['Priority Tier']]['Max Hours'] else 0

# Missing Escalation: only flag if escalation is required per lookup table
escalation_required = rules[row['Priority Tier']]['Escalation Required'] == 'Y'
missing_escalation = 1 if escalation_required and row['Escalation Code'] is None else 0
```

### Compound Conditions with Lookup Values

When a flag requires multiple conditions including a lookup threshold:

```python
# Build role-based rules lookup
rules = {}
for row in rules_ws.iter_rows(values_only=True):
    if row[0] == 'Role':  # skip header
        continue
    rules[row[0]] = {
        'min_break_minutes': row[1],
        'overtime_threshold': row[2]
    }

# Break Deficit: single condition against lookup threshold
break_deficit = 1 if row['Break Minutes'] < rules[row['Role']]['min_break_minutes'] else 0

# Approval Missing: compound condition - hours exceed threshold AND no approval code
hours_exceed_threshold = row['Hours Worked'] > rules[row['Role']]['overtime_threshold']
approval_missing = 1 if hours_exceed_threshold and row['Approval Code'] is None else 0
```

## Event Status Validation

When validating that events have reached a required terminal status:

```python
# Define which statuses count as "completed"
TERMINAL_STATUSES = {'COMPLETED', 'CLOSED', 'FINALIZED'}

# Build set of completed events
event_status = {}  # (Return ID, Line ID) -> status
for row in event_rows:
    key = (row['Return ID'], row['Line ID'])
    event_status[key] = row['Event Status']

# Flag missing terminal events
for row in plan_rows:
    key = (row['Return ID'], row['Line ID'])
    status = event_status.get(key)
    missing_final = 0 if status in TERMINAL_STATUSES else 1
```

### Pattern: Status-Specific Error Messages

```python
def get_status_error(status):
    if status is None:
        return 'No Event Record'
    elif status == 'PENDING':
        return 'Event Pending'
    elif status == 'VOID':
        return 'Event Voided'
    elif status not in TERMINAL_STATUSES:
        return f'Unexpected Status: {status}'
    return None
```

### Pattern: Filter by Status Before Building Lookup

When you need to match plan records against events with a specific status (e.g., only LOADED scans):

```python
# Build lookup of only LOADED scans by composite key
loaded_scans = {}
for row in scan_rows:
    row_dict = dict(zip(scan_headers, row))
    if row_dict['Status'] == 'LOADED':
        key = (row_dict['Shipment ID'], row_dict['Carton ID'])
        loaded_scans[key] = {
            'Scanned Zone': row_dict['Scanned Zone'],
            'Timestamp': row_dict['Scan Timestamp']
        }

# Check each plan row for missing load scan
for row in plan_rows:
    row_dict = dict(zip(plan_headers, row))
    key = (row_dict['Shipment ID'], row_dict['Carton ID'])
    missing_scan = 0 if key in loaded_scans else 1
```

### Pattern: Handling Duplicate Keys in Event Data

When events may have multiple records for the same key (e.g., multiple scans), decide on a strategy:

```python
# Option 1: Keep most recent (last wins)
loaded_scans = {}
for row in scan_rows:
    row_dict = dict(zip(scan_headers, row))
    if row_dict['Status'] == 'LOADED':
        key = (row_dict['Shipment ID'], row_dict['Carton ID'])
        loaded_scans[key] = row_dict['Scanned Zone']

# Option 2: Keep first occurrence only
loaded_scans = {}
for row in scan_rows:
    row_dict = dict(zip(scan_headers, row))
    if row_dict['Status'] == 'LOADED':
        key = (row_dict['Shipment ID'], row_dict['Carton ID'])
        if key not in loaded_scans:  # only set if not already present
            loaded_scans[key] = row_dict['Scanned Zone']

# Option 3: Track all values and flag duplicates
from collections import defaultdict
all_scans = defaultdict(list)
for row in scan_rows:
    row_dict = dict(zip(scan_headers, row))
    if row_dict['Status'] == 'LOADED':
        key = (row_dict['Shipment ID'], row_dict['Carton ID'])
        all_scans[key].append(row_dict['Scanned Zone'])

# Then check for multiple different zones
duplicate_zone_issue = {}
for key, zones in all_scans.items():
    if len(set(zones)) > 1:  # multiple different zones
        duplicate_zone_issue[key] = zones
```

## Alias Normalization Pattern

When comparing values that may have multiple valid representations (aliases, synonyms, case variations):

```python
# Build alias lookup from mapping file
alias_map = {}
for row in alias_ws.iter_rows(values_only=True):
    if row[0] == 'Alias':
        continue
    alias_map[row[0]] = row[1]  # alias -> standard

# Case-insensitive alias lookup
def normalize(value, alias_map):
    if value is None:
        return None
    # Try exact match first
    if value in alias_map:
        return alias_map[value]
    # Try case-insensitive match
    upper_key = value.upper()
    for alias, standard in alias_map.items():
        if alias.upper() == upper_key:
            return standard
    return value  # return original if no alias found

# Compare normalized values
planned_norm = normalize(row['Planned Disposition'], alias_map)
actual_norm = normalize(row['Final Disposition'], alias_map)
mismatch = 0 if planned_norm == actual_norm else 1
```

## Date Window Validation

Check if a date falls within a valid range (e.g., sale date within promo period):

```python
from datetime import datetime

def is_in_window(sale_date_str, start_date_str, end_date_str):
    """Check if sale_date is within [start_date, end_date] inclusive."""
    sale = datetime.strptime(sale_date_str, '%Y-%m-%d')
    start = datetime.strptime(start_date_str, '%Y-%m-%d')
    end = datetime.strptime(end_date_str, '%Y-%m-%d')
    return start <= sale <= end

# Usage in calculated column:
window_error = 0 if is_in_window(row['Sale Date'], row['Promo Start Date'], row['Promo End Date']) else 1
```

For ISO-format dates (YYYY-MM-DD), string comparison also works:
```python
# Simpler approach when dates are already YYYY-MM-DD strings
in_window = (row['Promo Start Date'] <= row['Sale Date'] <= row['Promo End Date'])
```

## Price Mismatch Detection

Flag when actual price differs from expected:

```python
price_error = 0 if row['Register Price'] == row['Promo Price'] else 1

# For floating-point prices, use tolerance:
price_error = 0 if abs(row['Register Price'] - row['Promo Price']) < 0.01 else 1
```

## Error Summary Text Generation

Combine multiple error flags into readable text:

```python
def error_summary(price_err, window_err):
    errors = []
    if price_err:
        errors.append('Price Error')
    if window_err:
        errors.append('Window Error')
    return ', '.join(errors) if errors else 'None'
```

## Group Aggregation with Totals

Aggregate data by multiple keys and add grand totals:

```python
from collections import defaultdict

# Group by (SKU, Store)
groups = defaultdict(lambda: {'Price Errors': 0, 'Window Errors': 0, 'Total Errors': 0})

for row in data_rows:
    key = (row['SKU'], row['Store ID'])
    groups[key]['Price Errors'] += row['Price Error']
    groups[key]['Window Errors'] += row['Window Error']
    groups[key]['Total Errors'] += row['Total Errors']

# Convert to sorted list and add grand total
summary_rows = []
grand_total = {'Price Errors': 0, 'Window Errors': 0, 'Total Errors': 0}

for (sku, store), counts in sorted(groups.items()):
    summary_rows.append({'SKU': sku, 'Store ID': store, **counts})
    for k in grand_total:
        grand_total[k] += counts[k]

# Add grand total row
summary_rows.append({'SKU': 'Grand Total', 'Store ID': '-', **grand_total})
```

## Filtering Rows with Errors

Select only rows where any error flag is non-zero:

```python
error_rows = [row for row in data_rows if row['Total Errors'] > 0]
```

## Multi-Sheet Audit Report Structure

Typical structure for audit reports:

1. **RawData**: Exact copy of source data (preserves original for reference)
2. **Formatted Data**: Source columns + calculated error flags + error summary text
3. **Summary**: Aggregated counts by key dimensions (SKU, Store, etc.) with grand total

```python
sheet_configs = [
    {'name': 'RawData', 'headers': source_headers, 'rows': source_rows},
    {'name': 'Formatted Data', 'headers': extended_headers, 'rows': formatted_rows},
    {'name': 'Summary', 'headers': summary_headers, 'rows': summary_rows}
]
```

## Template Preservation Pattern

When using a template workbook that has sheets to preserve (e.g., Overview, Instructions):

```python
from openpyxl import load_workbook
from copy import copy

# Load template
wb = load_workbook('/path/to/template.xlsx')

# Identify sheets to preserve vs replace
preserve_sheets = {'Overview', 'Instructions'}

# Clear and repopulate data sheets
for sheet_name in wb.sheetnames:
    if sheet_name not in preserve_sheets:
        ws = wb[sheet_name]
        # Clear existing content
        for row in ws.iter_rows():
            for cell in row:
                cell.value = None
        # Write new data
        ws.append(new_headers)
        for row in new_rows:
            ws.append(row)

# Or remove and recreate sheets entirely
for sheet_name in list(wb.sheetnames):
    if sheet_name not in preserve_sheets:
        wb.remove(wb[sheet_name])

# Add new sheets
ws_raw = wb.create_sheet('RawData')
ws_formatted = wb.create_sheet('Formatted Data')
ws_summary = wb.create_sheet('Summary')

wb.save('/path/to/output.xlsx')
```

## Handling None Values

Excel cells may contain None (empty cells). Handle explicitly:

```python
# Check for missing/empty values
if row['Approval Code'] is None or row['Approval Code'] == '':
    missing_approval = 1

# Provide defaults for None when building lookup dicts
rules[row['Role']] = {
    'threshold': row[1] if row[1] is not None else 0
}
```

## Filtering Source Sheets

When source workbooks contain informational sheets that should not be processed:

```python
# Skip non-data sheets
skip_sheets = {'Notes', 'Instructions', 'README'}
for sheet_name in wb.sheetnames:
    if sheet_name in skip_sheets:
        continue
    # process sheet
```

## Cycle Count Variance Audit Pattern

When auditing cycle count records against event logs for missing counts and approval gaps:

```python
from openpyxl import load_workbook

# Read plan data
wb_plan = load_workbook('/path/to/Cycle_Plan.xlsx')
plan_ws = wb_plan.active
plan_data = list(plan_ws.iter_rows(values_only=True))
plan_headers = plan_data[0]
plan_rows = plan_data[1:]

# Read event log
wb_events = load_workbook('/path/to/Count_Event_Log.xlsx')
events_ws = wb_events.active
events_data = list(events_ws.iter_rows(values_only=True))
event_headers = events_data[0]
event_rows = events_data[1:]

# Build lookup: (Facility, Session ID, Bin ID) -> list of events
event_lookup = {}
for row in event_rows:
    row_dict = dict(zip(event_headers, row))
    key = (row_dict['Facility'], row_dict['Session ID'], row_dict['Bin ID'])
    if key not in event_lookup:
        event_lookup[key] = []
    event_lookup[key].append(row_dict)

# Process each plan row
for row in plan_rows:
    row_dict = dict(zip(plan_headers, row))
    key = (row_dict['Facility'], row_dict['Session ID'], row_dict['Bin ID'])
    events = event_lookup.get(key, [])
    
    # Find FINAL event with valid quantity
    final_event = None
    for evt in events:
        if evt['Event Type'] == 'FINAL' and evt['Count Qty'] is not None:
            final_event = evt
            break
    
    # Missing Final Count: no FINAL event with valid quantity
    missing_final = 1 if final_event is None else 0
    
    # Approval Gap: approval needed AND variance exceeds threshold AND no approval code
    approval_gap = 0
    if row_dict['Approval Needed'] == 'YES' and final_event is not None:
        expected = row_dict['Expected Qty']
        actual = final_event['Count Qty']
        allowed = row_dict['Allowed Variance']
        variance_exceeds = abs(expected - actual) > allowed
        has_approval = final_event['Approval Code'] is not None
        # Only flag if variance exceeds AND no approval code present
        approval_gap = 1 if variance_exceeds and not has_approval else 0
    
    # For rows with missing final count, approval gap is N/A (set to 0)
    # unless business rules require flagging both
```

### Critical: Approval Code Validation Logic

A common error is flagging approval gaps when an approval code IS present. The correct logic:

```python
# WRONG: Flags approval gap even when approval code exists
approval_gap = 1 if approval_needed == 'YES' and variance_exceeds else 0

# CORRECT: Only flag when approval needed, variance exceeds, AND no approval code
approval_gap = 1 if (approval_needed == 'YES' and variance_exceeds and approval_code is None) else 0
```

**Verification step**: After calculating approval gaps, verify that no rows with approval codes are flagged:

```python
# Sanity check: no row with approval code should have approval_gap = 1
for row in formatted_rows:
    if row['Approval Code'] is not None and row['Approval Gap'] == 1:
        print(f"ERROR: Row has approval code but flagged as gap: {row}")
```

### Pattern: Valid Final Event Check

When checking for valid final counts, ensure both the event exists AND has a valid quantity:

```python
# Build lookup of valid final events only
valid_final_events = {}
for row in event_rows:
    row_dict = dict(zip(event_headers, row))
    if row_dict['Event Type'] == 'FINAL' and row_dict['Count Qty'] is not None:
        key = (row_dict['Facility'], row_dict['Session ID'], row_dict['Bin ID'])
        valid_final_events[key] = row_dict

# Check for missing final count
for row in plan_rows:
    row_dict = dict(zip(plan_headers, row))
    key = (row_dict['Facility'], row_dict['Session ID'], row_dict['Bin ID'])
    missing_final = 0 if key in valid_final_events else 1
```

## Common Audit Logic Errors

| Error | Symptom | Fix |
|-------|----------|-----|
| Flagging rows that have approval codes | Approval gap = 1 for rows with Approval Code | Add `and approval_code is None` to condition |
| Missing final count includes VOID events | Counting voided events as valid finals | Filter by `Event Type == 'FINAL'` only |
| None quantity treated as valid count | Missing final not flagged when Count Qty is None | Check `Count Qty is not None` explicitly |
| Using first event instead of latest | Stale data used for variance calc | Sort by timestamp, use last event per key |
| Wrong key composition | Events not matching plan rows | Verify composite key matches across both files |
