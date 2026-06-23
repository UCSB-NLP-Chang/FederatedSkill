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

## Verification

Always verify resolved codes exist in the target files:
```python
assert hist_code in hist_df.columns, f"{hist_code} not in {hist_df.columns.tolist()}"
assert curr_code in curr_df['series_code'].values, f"{curr_code} not found in current data"
```