# Computed Column Examples

This reference provides concrete computed column patterns used in audit tasks.

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
# Or for detention audits:
# df['Total Errors'] = df['Detention Overrun'] + df['Seal Error']
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

## Top-N Items by Exception Count

Identify highest-priority items for executive brief:

```python
from collections import Counter

# Count total errors per SKU
sku_errors = df.groupby('SKU')['Total Errors'].sum()
top_skus = sku_errors.nlargest(2)  # Get top 2
print(f"Top SKUs: {list(top_skus.items())}")
```