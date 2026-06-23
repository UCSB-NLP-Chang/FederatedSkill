# Exception Rule Patterns

Common exception calculation patterns for different audit domains.

## Logistics / Receiving Audit

```python
exception_rules = [
    {
        'name': 'Qty Variance',
        'condition': df['Expected Qty'] != df['Received Qty']
    },
    {
        'name': 'Cold Chain Error',
        'condition': df['Storage Class'].isin(['CHILLED', 'FROZEN']) & 
                    (df['Temp Status'] != 'OK')
    }
]
```

## Trailer Detention Audit

```python
exception_rules = [
    {
        'name': 'Detention Overrun',
        'condition': df['Actual Hold Hours'] > df['Allowed Hold Hours']
    },
    {
        'name': 'Seal Error',
        'condition': (df['Seal Required'] == 'YES') & 
                    (~df['Seal Status'].isin(['VERIFIED']))
    }
]
```

## Outbound Manifest / Event-Log Reconciliation

Audit planned shipments against scan events. Critical: filter to latest LOADED status per item.

```python
# Load sources
manifest = pd.read_excel('Manifest_Plan.xlsx')
scans = pd.read_excel('Dock_Scan_Log.xlsx')

# Filter to target status, get latest per Shipment+Carton
loaded = scans[scans['Status'] == 'LOADED'].copy()
loaded['Scan Timestamp'] = pd.to_datetime(loaded['Scan Timestamp'])
latest = (loaded
    .sort_values('Scan Timestamp')
    .groupby(['Shipment ID', 'Carton ID'])
    .last()
    .reset_index())

# Merge: left join preserves all planned items
merged = manifest.merge(
    latest[['Shipment ID', 'Carton ID', 'Scanned Zone']],
    on=['Shipment ID', 'Carton ID'],
    how='left'
)

# Calculate exceptions
exception_rules = [
    {
        'name': 'Missing Load Scan',
        'condition': merged['Scanned Zone'].isna()
    },
    {
        'name': 'Zone Mismatch',
        'condition': merged['Planned Zone'] != merged['Scanned Zone']
    }
]

# Group by Route and Shipment for summary
group_cols = ['Route', 'Shipment ID']
error_cols = ['Missing Load Scan', 'Zone Mismatch', 'Total Errors']
```

**Key pattern**: Filter events to final status (LOADED), sort by timestamp, take last per key. Left join ensures unprocessed items are flagged as exceptions.

## Cycle Count / Inventory Variance Audit

Audit planned inventory counts against event logs with variance threshold checking and approval validation.

```python
# Load sources
plan = pd.read_excel('Cycle_Plan.xlsx')
events = pd.read_excel('Count_Event_Log.xlsx')

# Create composite key for matching
plan['Key'] = plan['Facility'] + '|' + plan['Session ID'] + '|' + plan['Bin ID']
events['Key'] = events['Facility'] + '|' + events['Session ID'] + '|' + events['Bin ID']

# Filter to FINAL events only, drop incomplete records
final_events = events[events['Event Type'] == 'FINAL'].copy()
final_events = final_events.dropna(subset=['Count Qty'])

# Get latest FINAL per key (handles re-counts)
final_events['Event Time'] = pd.to_datetime(final_events['Event Time'])
latest = (final_events
    .sort_values('Event Time')
    .groupby('Key')
    .last()
    .reset_index())

# Merge: left join to preserve all planned items
merged = plan.merge(
    latest[['Key', 'Count Qty', 'Approval Code']],
    on='Key',
    how='left'
)

# Calculate exceptions
merged['Missing Final Count'] = merged['Count Qty'].isna().astype(int)

# Variance calculation with threshold check
merged['Qty Variance'] = (merged['Count Qty'] - merged['Expected Qty']).abs()
merged['Variance Exceeds Threshold'] = (merged['Qty Variance'] > merged['Allowed Variance']).astype(int)

# Approval gap: approval required AND (variance exceeded OR missing count)
approval_required = merged['Approval Needed'] == 'YES'
variance_or_missing = merged['Variance Exceeds Threshold'] | merged['Missing Final Count']
no_approval = merged['Approval Code'].isna() | (merged['Approval Code'] == '')
merged['Approval Gap'] = (approval_required & variance_or_missing & no_approval).astype(int)

# Group by Facility and Session for summary
group_cols = ['Facility', 'Session ID']
error_cols = ['Missing Final Count', 'Approval Gap', 'Total Errors']
```

**Key patterns**:
- Filter events to `FINAL` status; ignore `PRELIMINARY` and `VOID`
- Drop records with null `Count Qty` before taking latest
- Use composite key when natural key spans multiple columns
- Approval gap combines threshold logic with approval code presence
- Left join ensures bins without any final count are flagged

## HR / Timesheet Compliance Audit

Checks break-time adherence and overtime approval requirements using role-specific thresholds from a reference table.

```python
# Load timesheet entries and break rules
entries = pd.read_excel(input_path, sheet_name='Entries')
rules = pd.read_excel(input_path, sheet_name='BreakRules')

# Merge to bring thresholds into entries
df = entries.merge(rules[['Role', 'Min Break Minutes', 'Overtime Threshold']], 
                   on='Role', how='left')

# Calculate exceptions
exception_rules = [
    {
        'name': 'Break Deficit',
        'condition': df['Break Minutes'] < df['Min Break Minutes']
    },
    {
        'name': 'Approval Missing',
        'condition': (df['Hours Worked'] > df['Overtime Threshold']) & 
                    (df['Approval Code'].isna() | (df['Approval Code'] == ''))
    }
]

# Group by Employee ID and Week Ending for summary
group_cols = ['Employee ID', 'Week Ending']
error_cols = ['Break Deficit', 'Approval Missing', 'Total Errors']
```

**Key pattern**: Merge reference data before calculating exceptions. This avoids hardcoding thresholds and handles role-based policy variations.

## Promotional Pricing / Register Audit

Common in retail/compliance audits. Checks price mismatches and date window violations.

```python
# Ensure dates are parsed as datetime
df['Promo Start Date'] = pd.to_datetime(df['Promo Start Date'])
df['Promo End Date'] = pd.to_datetime(df['Promo End Date'])
df['Sale Date'] = pd.to_datetime(df['Sale Date'])

exception_rules = [
    {
        'name': 'Price Error',
        'condition': df['Register Price'] != df['Promo Price']
    },
    {
        'name': 'Window Error',
        'condition': (df['Sale Date'] < df['Promo Start Date']) | 
                    (df['Sale Date'] > df['Promo End Date'])
    }
]

# Group by SKU and Store for summary
group_cols = ['SKU', 'Store ID']
error_cols = ['Price Error', 'Window Error', 'Total Errors']
```

**Critical**: Parse dates with `pd.to_datetime()` before comparison. String comparisons will fail silently or produce wrong results.

## Financial / Invoice Audit

```python
exception_rules = [
    {
        'name': 'Amount Mismatch',
        'condition': abs(df['Invoice Amount'] - df['PO Amount']) > 0.01
    },
    {
        'name': 'Late Payment',
        'condition': df['Days Past Due'] > 0
    }
]
```

## Compliance / Data Quality

```python
exception_rules = [
    {
        'name': 'Missing Required Field',
        'condition': df['Required Field'].isna() | (df['Required Field'] == '')
    },
    {
        'name': 'Invalid Format',
        'condition': ~df['Email'].str.contains(r'@', na=False)
    }
]
```

## Pattern Notes

- Always cast boolean results to `int` for summation: `.astype(int)`
- Use `~` for negation in pandas boolean indexing
- Use `isin()` for multiple value matching
- Use `isna()` / `notna()` for null checks
- For string containment: `.str.contains(pattern, na=False)`
- For date comparisons: ensure columns are `datetime` type first with `pd.to_datetime()`
- For threshold-based rules: merge reference tables before calculating exceptions
- For event-log reconciliation: filter to final status, sort by timestamp, take last per key, use left join
- For composite keys: create explicit key column with separator (e.g., `'|'.join([col1, col2, col3])`)
