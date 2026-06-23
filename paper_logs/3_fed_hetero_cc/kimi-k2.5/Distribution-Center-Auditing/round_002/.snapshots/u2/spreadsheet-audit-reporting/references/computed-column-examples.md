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

## Error Summary Text Column

Build human-readable error summary from multiple error flags:

```python
def build_error_summary(row):
    errors = []
    if row['Detention Overrun'] == 1:
        errors.append('Detention Overrun')
    if row['Seal Error'] == 1:
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
