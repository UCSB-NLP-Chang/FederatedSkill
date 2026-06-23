# Computed Column Examples

This reference provides concrete computed column patterns used in audit tasks.

## Role-Based Threshold Lookup (Timesheet/Break Rules)

Build a lookup dictionary from a reference sheet keyed by Role, then compare actual values against role-specific thresholds:

```python
import pandas as pd

# Load break rules into a lookup dictionary keyed by Role
rules_df = pd.read_excel(source, sheet_name='BreakRules')
break_rules = {row['Role']: {'min_break': row['Min Break Minutes'], 
                            'overtime_thresh': row['Overtime Threshold']} 
               for _, row in rules_df.iterrows()}

# Flag break deficit (actual break < required for role)
def break_deficit(row):
    role = row['Role']
    min_required = break_rules.get(role, {}).get('min_break', 0)
    if row['Break Minutes'] < min_required:
        return 1
    return 0

df['Break Deficit'] = df.apply(break_deficit, axis=1)

# Flag missing approval (overtime hours without approval code)
def approval_missing(row):
    role = row['Role']
    overtime_thresh = break_rules.get(role, {}).get('overtime_thresh', float('inf'))
    if row['Hours Worked'] > overtime_thresh and pd.isna(row['Approval Code']):
        return 1
    return 0

df['Approval Missing'] = df.apply(approval_missing, axis=1)
```

## SLA Breach Detection (with Lookup Table)

Flag when a value exceeds a threshold from a reference/lookup table:

```python
import pandas as pd

# Load SLA rules into a lookup dictionary
rules_df = pd.read_excel(source, sheet_name='SLA_Rules')
sla_lookup = {row['Priority Tier']: row['Max Open Hours'] for _, row in rules_df.iterrows()}

# Flag SLA breach
def sla_breach(row):
    max_hours = sla_lookup.get(row['Priority Tier'])
    if max_hours is not None and row['Open Age Hours'] > max_hours:
        return 1
    return 0

df['SLA Breach'] = df.apply(sla_breach, axis=1)
```

## Missing Required Field (Conditional Null Check)

Flag when a field is required based on a condition but is null/missing:

```python
import pandas as pd

def missing_escalation(row, sla_lookup):
    # Check if escalation is required for this priority tier
    tier = row['Priority Tier']
    escalation_required = sla_lookup.get(tier, {}).get('Escalation Required', 'N')
    
    # If required, check if Escalation Code is missing
    if str(escalation_required).upper() == 'Y':
        if pd.isna(row['Escalation Code']):
            return 1
    return 0

df['Missing Escalation'] = df.apply(lambda r: missing_escalation(r, sla_lookup), axis=1)
```

## Detention Overrun Detection

Flag when actual hold time exceeds allowed threshold:

```python
df['Detention Overrun'] = (df['Actual Hold Hours'] > df['Allowed Hold Hours']).astype(int)
```

## Seal Compliance Error

Flag when seal is required but not verified:

```python
def seal_error(row):
    if row['Seal Required'] == 'YES':
        # Seal Status may be null/NaN for non-sealed shipments
        if pd.isna(row['Seal Status']) or row['Seal Status'] != 'VERIFIED':
            return 1
    return 0

df['Seal Error'] = df.apply(seal_error, axis=1)
```

## Price Mismatch Detection

Flag when register price differs from promotional price:

```python
df['Price Error'] = (df['Register Price'] != df['Promo Price']).astype(int)
```

For float comparisons where rounding differences matter, use tolerance:

```python
import numpy as np
df['Price Error'] = (~np.isclose(df['Register Price'], df['Promo Price'], rtol=1e-5)).astype(int)
```

## Date Window Validation

Flag when a date falls outside a valid range. For ISO-format date strings:

```python
def window_error(row):
    sale_date = row['Sale Date']
    start_date = row['Promo Start Date']
    end_date = row['Promo End Date']
    # ISO format strings compare correctly
    if sale_date < start_date or sale_date > end_date:
        return 1
    return 0

df['Window Error'] = df.apply(window_error, axis=1)
```

For non-ISO date formats, parse to datetime first:

```python
import pandas as pd

df['Sale Date'] = pd.to_datetime(df['Sale Date'])
df['Promo Start Date'] = pd.to_datetime(df['Promo Start Date'])
df['Promo End Date'] = pd.to_datetime(df['Promo End Date'])

df['Window Error'] = (
    (df['Sale Date'] < df['Promo Start Date']) |
    (df['Sale Date'] > df['Promo End Date'])
).astype(int)
```

## Total Errors Column

Sum multiple error flags:

```python
df['Total Errors'] = df['Price Error'] + df['Window Error']
# Or for SLA audits:
# df['Total Errors'] = df['SLA Breach'] + df['Missing Escalation']
# Or for detention audits:
# df['Total Errors'] = df['Detention Overrun'] + df['Seal Error']
# Or for timesheet audits:
# df['Total Errors'] = df['Break Deficit'] + df['Approval Missing']
```

## Error Summary Text Column

Build human-readable error summary from multiple error flags:

```python
def build_error_summary(row):
    errors = []
    if row.get('Price Error', 0) == 1:
        errors.append('Price Error')
    if row.get('Window Error', 0) == 1:
        errors.append('Window Error')
    if row.get('Detention Overrun', 0) == 1:
        errors.append('Detention Overrun')
    if row.get('Seal Error', 0) == 1:
        errors.append('Seal Error')
    if row.get('SLA Breach', 0) == 1:
        errors.append('SLA Breach')
    if row.get('Missing Escalation', 0) == 1:
        errors.append('Missing Escalation')
    if row.get('Break Deficit', 0) == 1:
        errors.append('Break Deficit')
    if row.get('Approval Missing', 0) == 1:
        errors.append('Approval Missing')
    if row.get('Missing Final Event', 0) == 1:
        errors.append('Missing Final Event')
    if row.get('Disposition Mismatch', 0) == 1:
        errors.append('Disposition Mismatch')
    return ', '.join(errors) if errors else 'None'

df['Error Summary'] = df.apply(build_error_summary, axis=1)
```

## Summary Aggregation by Multiple Keys

Group by carrier and yard with totals:

```python
summary = df.groupby(['Carrier', 'Yard']).agg({
    'Detention Overrun': 'sum',
    'Seal Error': 'sum',
    'Total Errors': 'sum'
}).reset_index()

# Add Grand Total row
grand_total = pd.DataFrame({
    'Carrier': ['Grand Total'],
    'Yard': ['-'],
    'Detention Overrun': [df['Detention Overrun'].sum()],
    'Seal Error': [df['Seal Error'].sum()],
    'Total Errors': [df['Total Errors'].sum()]
})
summary = pd.concat([summary, grand_total], ignore_index=True)
```

## Summary Aggregation for Promo Register (Filtered)

Group by SKU and Store ID, filter to errors only, sort, then add Grand Total:

```python
# Aggregate
summary = df.groupby(['SKU', 'Store ID']).agg({
    'Price Error': 'sum',
    'Window Error': 'sum',
    'Total Errors': 'sum'
}).reset_index()

# Filter to rows with errors
summary = summary[summary['Total Errors'] > 0]

# Sort by SKU then Store ID
summary = summary.sort_values(['SKU', 'Store ID'])

# Add Grand Total
grand_total = pd.DataFrame({
    'SKU': ['Grand Total'],
    'Store ID': ['-'],
    'Price Error': [df['Price Error'].sum()],
    'Window Error': [df['Window Error'].sum()],
    'Total Errors': [df['Total Errors'].sum()]
})
summary = pd.concat([summary, grand_total], ignore_index=True)
```

## Summary Aggregation for SLA Audit (Queue + Region)

Group by Queue and Region, filter to errors only:

```python
# Aggregate
summary = df.groupby(['Queue', 'Region']).agg({
    'SLA Breach': 'sum',
    'Missing Escalation': 'sum',
    'Total Errors': 'sum'
}).reset_index()

# Filter to rows with errors
summary = summary[summary['Total Errors'] > 0]

# Sort by Queue then Region
summary = summary.sort_values(['Queue', 'Region'])

# Add Grand Total
grand_total = pd.DataFrame({
    'Queue': ['Grand Total'],
    'Region': ['-'],
    'SLA Breach': [df['SLA Breach'].sum()],
    'Missing Escalation': [df['Missing Escalation'].sum()],
    'Total Errors': [df['Total Errors'].sum()]
})
summary = pd.concat([summary, grand_total], ignore_index=True)
```

## Summary Aggregation for Timesheet Audit (Employee + Week)

Group by Employee ID and Week Ending, filter to errors only:

```python
# Aggregate
summary = df.groupby(['Employee ID', 'Week Ending']).agg({
    'Break Deficit': 'sum',
    'Approval Missing': 'sum',
    'Total Errors': 'sum'
}).reset_index()

# Filter to rows with errors
summary = summary[summary['Total Errors'] > 0]

# Sort by Employee ID then Week Ending
summary = summary.sort_values(['Employee ID', 'Week Ending'])

# Add Grand Total
grand_total = pd.DataFrame({
    'Employee ID': ['Grand Total'],
    'Week Ending': ['-'],
    'Break Deficit': [df['Break Deficit'].sum()],
    'Approval Missing': [df['Approval Missing'].sum()],
    'Total Errors': [df['Total Errors'].sum()]
})
summary = pd.concat([summary, grand_total], ignore_index=True)
```

## Multi-File Join with Composite Key

When audit data spans multiple files, join on composite keys:

```python
import pandas as pd

# Load primary data
plan_df = pd.read_excel('Return_Plan.xlsx', sheet_name='PlanLines')

# Load event log
events_df = pd.read_excel('Disposition_Event_Log.xlsx', sheet_name='Events')

# Build lookup dictionary for O(1) access
event_lookup = {}
for _, row in events_df.iterrows():
    key = (row['Return ID'], row['Line ID'])
    event_lookup[key] = row['Final Disposition']

# Apply lookup to primary data
def get_final_disposition(row):
    key = (row['Return ID'], row['Line ID'])
    return event_lookup.get(key)  # Returns None if not found

plan_df['Final Disposition'] = plan_df.apply(get_final_disposition, axis=1)
```

## Alias/Normalization Lookup

When comparing values that may have multiple representations (aliases), normalize before comparison:

```python
# Load alias mapping
alias_df = pd.read_excel('Disposition_Alias.xlsx', sheet_name='AliasMap')

# Build lookup: alias -> standard value (case-insensitive keys)
alias_lookup = {}
for _, row in alias_df.iterrows():
    alias_lookup[row['Alias'].upper()] = row['Standard Disposition'].upper()

# Normalize a value using the lookup
def normalize_disposition(raw_value):
    if pd.isna(raw_value):
        return None
    return alias_lookup.get(raw_value.upper(), raw_value.upper())

# Compare normalized values
planned_std = normalize_disposition(row['Planned Disposition'])
actual_std = normalize_disposition(row['Final Disposition'])
if planned_std != actual_std:
    return 1  # Mismatch
```

## Missing Final Event Detection

Flag when no COMPLETED event exists for a composite key. Use dict membership check, NOT null check:

```python
# Build lookup of COMPLETED events keyed by composite key
event_lookup = {}
for _, row in events_df.iterrows():
    if row['Event Status'] == 'COMPLETED':
        key = (row['Return ID'], row['Line ID'])
        event_lookup[key] = row['Final Disposition']

# Check via dict membership — key not in lookup means no COMPLETED event
def missing_final_event(row, completed_events_lookup):
    key = (row['Return ID'], row['Line ID'])
    # CRITICAL: use dict membership, NOT pd.isna() or null check
    return 0 if key in completed_events_lookup else 1

df['Missing Final Event'] = df.apply(
    lambda row: missing_final_event(row, event_lookup), axis=1
)
```

## Handling Null Values in Source Data

Source Excel files may contain null/NaN values that need special handling:

```python
# Check for null before string comparison
if pd.notna(row['Seal Status']) and row['Seal Status'] == 'VERIFIED':
    # Verified status
    pass

# Or use fillna for simpler comparisons
df['Seal Status'] = df['Seal Status'].fillna('')
```

## Event Type Filtering (Cycle Count / Returns Audits)

When matching events to plan lines, filter for the correct event type before building lookup dictionaries. PRELIMINARY, VOID, or other intermediate statuses should typically be excluded:

```python
# Build lookup from FINAL events only
final_events = {}
for _, row in events_df.iterrows():
    if row['Event Type'] == 'FINAL':
        key = (row['Facility'], row['Session ID'], row['Bin ID'])
        final_events[key] = row['Count Qty']
```

## NULL Count Quantities in Cycle Count Audits

When processing FINAL count events, a `Count Qty` of `None`/null indicates an incomplete/missing count, not a zero count. Exclude NULL quantities when building the lookup:

```python
# Load valid FINAL events - exclude NULL quantities
final_events = {}
for row in event_rows:
    if row['Event Type'] == 'FINAL' and pd.notna(row['Count Qty']):
        key = (row['Facility'], row['Session ID'], row['Bin ID'])
        final_events[key] = row['Count Qty']

# Check for missing final count via dict membership
def missing_final_count(row, final_events):
    key = (row['Facility'], row['Session ID'], row['Bin ID'])
    return 0 if key in final_events else 1

df['Missing Final Count'] = df.apply(lambda r: missing_final_count(r, final_events), axis=1)
```

## Variance Threshold Calculations (Cycle Count Audits)

Approval Gap detection requires comparing absolute variance against allowed threshold:

```python
def approval_gap(row, final_events):
    key = (row['Facility'], row['Session ID'], row['Bin ID'])
    if key not in final_events:
        return 0  # Missing final count is separate error
    
    final_qty = final_events[key]
    expected = row['Expected Qty']
    allowed = row['Allowed Variance']
    approval_needed = str(row['Approval Needed']).upper() == 'YES'
    
    # Calculate absolute variance
    variance = abs(final_qty - expected)
    
    # Gap exists if variance exceeds allowed AND approval was required but missing
    if variance > allowed and approval_needed:
        approval_code = row.get('Approval Code')
        if pd.isna(approval_code) or str(approval_code).strip() == '':
            return 1
    return 0

df['Approval Gap'] = df.apply(lambda r: approval_gap(r, final_events), axis=1)
```

## Top-N Items by Exception Count

Identify highest-priority items for executive brief:

```python
from collections import Counter

# Count total errors per SKU
sku_errors = df.groupby('SKU')['Total Errors'].sum()
top_skus = sku_errors.nlargest(2)  # Get top 2
print(f"Top SKUs: {list(top_skus.items())}")

# For timesheet audits: count errors per employee across all weeks
employee_errors = df.groupby('Employee ID')['Total Errors'].sum()
top_employees = employee_errors.nlargest(2)
print(f"Top Employees: {list(top_employees.items())}")
```

## Building Lookup Dictionaries from Reference Sheets

When source workbooks contain separate reference/lookup sheets:

```python
import pandas as pd

# Load the reference sheet
rules_df = pd.read_excel(source, sheet_name='SLA_Rules')

# Build a simple lookup dictionary
sla_lookup = {row['Priority Tier']: row['Max Open Hours'] for _, row in rules_df.iterrows()}

# Or build a nested dictionary for multiple fields
sla_lookup = {}
for _, row in rules_df.iterrows():
    sla_lookup[row['Priority Tier']] = {
        'Max Open Hours': row['Max Open Hours'],
        'Escalation Required': row['Escalation Required']
    }

# Use in apply functions
def check_sla(row):
    max_hours = sla_lookup.get(row['Priority Tier'], {}).get('Max Open Hours', 0)
    return 1 if row['Open Age Hours'] > max_hours else 0

df['SLA Breach'] = df.apply(check_sla, axis=1)
```