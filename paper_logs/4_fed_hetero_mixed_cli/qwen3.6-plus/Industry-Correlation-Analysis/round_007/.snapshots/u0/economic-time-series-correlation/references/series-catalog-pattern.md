# Series Catalog Mapping Pattern

Many economic data tasks provide a `series_catalog.csv` (or similar) that maps human-readable series names to database-specific codes, file locations, and deflator columns.

## Catalog Structure

Typical columns:
- `requested_series`: Human-readable name (e.g., "Freight brokerage revenue")
- `history_sheet`: Excel sheet name for historical data (e.g., "AnnualSeries")
- `history_code`: Column code in historical file (e.g., "BROKER_REV")
- `current_sheet`: Sheet name for current/update data
- `current_code`: Code in current release file (e.g., "BR_REV_25")
- `deflator_column`: Price index column name for deflation

## Usage Pattern

```python
import pandas as pd

# 1. Read catalog
catalog = pd.read_csv('series_catalog.csv')

# 2. Lookup codes for a series
row = catalog[catalog['requested_series'] == 'Freight brokerage revenue'].iloc[0]
hist_code = row['history_code']      # 'BROKER_REV'
curr_code = row['current_code']      # 'BR_REV_25'
deflator = row['deflator_column']    # 'Transport_Services_Price_2025_Base'

# 3. Read historical data (wide format)
hist_df = pd.read_excel('history.xlsx', sheet_name=row['history_sheet'])
hist_values = hist_df[hist_code]     # Use code from catalog, not series name

# 4. Read current data (long format) and filter by code
curr_df = pd.read_excel('current.xlsx', sheet_name=row['current_sheet'])
curr_series = curr_df[curr_df['series_code'] == curr_code]

# 5. Get deflator
deflator_df = pd.read_excel('prices.xlsx')
price_index = deflator_df.set_index('Year')[deflator]
```

## Benefits

- **Robustness**: Column codes often differ between historical and current files
- **Deflator mapping**: Each series may use a different price index
- **Sheet routing**: Different series may live in different Excel sheets
- **Automation**: Loop through catalog rows to process multiple series consistently

## Alias Mapping Pattern

When series names vary across data sources, use an alias mapping to normalize to canonical names:

```python
# Alias mapping: variant names -> canonical name
alias_map = {
    'Merchant wholesale turnover': 'Merchant wholesale turnover',
    'merchant-wholesale-turnover': 'Merchant wholesale turnover',
    'merchant wholesale net turnover': 'Merchant wholesale turnover',
    'Packaging converters shipments': 'Packaging converters shipments',
    'packaging-plants shipments': 'Packaging converters shipments',
    'packaging converters domestic shipments': 'Packaging converters shipments',
}

# Apply mapping
df['series'] = df['series_name'].map(alias_map)

# Check for unmapped values
unmapped = df[df['series'].isna()]['series_name'].unique()
if len(unmapped) > 0:
    print(f"Warning: Unmapped series names: {unmapped}")
```

## Priority-Based Deduplication

When multiple records exist for the same (series, period) combination, deduplicate by keeping the record with the smallest priority value:

```python
# Sort by priority (ascending) then keep first per group
df_dedup = df.sort_values('priority').groupby(['series', 'period'], as_index=False).first()

# Verify deduplication
assert len(df_dedup) == len(df_dedup[['series', 'period']].drop_duplicates()), "Deduplication failed"
```

### Priority Semantics
- Lower priority value = higher precedence (use this record)
- Higher priority value = lower precedence (fallback or alternative source)
- Common pattern: priority 1 = primary source, priority 2+ = secondary sources

## Verification

Always verify resolved codes exist in the target files:
```python
assert hist_code in hist_df.columns, f"{hist_code} not in {hist_df.columns.tolist()}"
assert curr_code in curr_df['series_code'].values, f"{curr_code} not found in current data"
```

Verify alias mapping covers all series:
```python
assert df['series'].notna().all(), f"Unmapped series: {df[df['series'].isna()]['series_name'].unique()}"
```

Verify deduplication produces one record per (series, period):
```python
assert df_dedup.groupby(['series', 'period']).size().max() == 1, "Multiple records per (series, period) after deduplication"
```
