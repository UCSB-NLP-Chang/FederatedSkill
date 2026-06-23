# Computed Column Examples

This reference provides concrete computed column patterns used in audit tasks.

## SLA Breach Detection (Service Queue)

Flag when open age exceeds priority-specific threshold from rules sheet:

```python
# Load SLA rules into lookup dict
sla_rules = {
    'P1': {'Max Open Hours': 4, 'Escalation Required': 'Y'},
    'P2': {'Max Open Hours': 8, 'Escalation Required': 'Y'},
    'P3': {'Max Open Hours': 16, 'Escalation Required': 'N'},
    'P4': {'Max Open Hours': 24, 'Escalation Required': 'N'},
}

def sla_breach(row):
    tier = row['Priority Tier']
    max_hours = sla_rules.get(tier, {}).get('Max Open Hours', float('inf'))
    return 1 if row['Open Age Hours'] > max_hours else 0

df['SLA Breach'] = df.apply(sla_breach, axis=1)
```

## Missing Escalation Detection (Service Queue)

Flag when escalation is required but code is missing:

```python
def missing_escalation(row):
    tier = row['Priority Tier']
    escalation_required = sla_rules.get(tier, {}).get('Escalation Required', 'N')
    if escalation_required == 'Y':
        code = row.get('Escalation Code')
        if pd.isna(code) or str(code).strip() == '':
            return 1
    return 0

df['Missing Escalation'] = df.apply(missing_escalation, axis=1)
```

## Price Error Detection (Promotional Register)

Flag when register price differs from promotional price:

```python
df['Price Error'] = (df['Register Price'] != df['Promo Price']).astype(int)
```

## Window Error Detection (Promotional Register)

Flag when sale date falls outside promotional window:

```python
def window_error(row):
    sale = row['Sale Date']
    start = row['Promo Start Date']
    end = row['Promo End Date']
    # Handle both string and datetime comparisons
    if isinstance(sale, str):
        from datetime import datetime
        sale = datetime.strptime(sale, '%Y-%m-%d').date() if isinstance(sale, str) else sale
    if isinstance(start, str):
        start = datetime.strptime(start, '%Y-%m-%d').date() if isinstance(start, str) else start
    if isinstance(end, str):
        end = datetime.strptime(end, '%Y-%m-%d').date() if isinstance(end, str) else end
    return 1 if sale < start or sale > end else 0

df['Window Error'] = df.apply(window_error, axis=1)
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

## Total Errors Column

Sum multiple error flags:

```python
df['Total Errors'] = df['Price Error'] + df['Window Error']
# Or for detention audits:
# df['Total Errors'] = df['Detention Overrun'] + df['Seal Error']
# Or for SLA audits:
# df['Total Errors'] = df['SLA Breach'] + df['Missing Escalation']
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

Group by Queue and Region, include all groups with errors:

```python
# Aggregate
summary = df.groupby(['Queue', 'Region']).agg({
    'SLA Breach': 'sum',
    'Missing Escalation': 'sum',
    'Total Errors': 'sum'
}).reset_index()

# Filter to rows with errors (optional - include all or filter)
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

## Handling Null Values in Source Data

Source Excel files may contain null/NaN values that need special handling:

```python
# Check for null before string comparison
if pd.notna(row['Seal Status']) and row['Seal Status'] == 'VERIFIED':
    # Verified status
    pass

# Or use fillna for simpler comparisons
df['Seal Status'] = df['Seal Status'].fillna('')

# For escalation codes, check both None and empty string
code = row.get('Escalation Code')
if pd.isna(code) or str(code).strip() == '':
    # Missing escalation
    pass
```

## Top-N Items by Exception Count

Identify highest-priority items for executive brief:

```python
from collections import Counter

# Count total errors per SKU
sku_errors = df.groupby('SKU')['Total Errors'].sum()
top_skus = sku_errors.nlargest(2)  # Get top 2
print(f"Top SKUs: {list(top_skus.items())}")

# Count total errors per Queue
queue_errors = df.groupby('Queue')['Total Errors'].sum()
top_queues = queue_errors.nlargest(2)
print(f"Top Queues: {list(top_queues.items())}")
```

## Loading Rules from Separate Sheet

When thresholds are defined in a separate sheet:

```python
def load_sla_rules(wb, sheet_name='SLA_Rules'):
    """Load SLA rules into dict keyed by Priority Tier."""
    sla_sheet = wb[sheet_name]
    sla_rules = {}
    headers = [cell.value for cell in sla_sheet[1]]
    
    for row in sla_sheet.iter_rows(min_row=2, values_only=True):
        if row[0] is not None:
            rule = dict(zip(headers, row))
            tier = rule['Priority Tier']
            sla_rules[tier] = {
                'Max Open Hours': rule['Max Open Hours'],
                'Escalation Required': rule['Escalation Required']
            }
    return sla_rules
```
