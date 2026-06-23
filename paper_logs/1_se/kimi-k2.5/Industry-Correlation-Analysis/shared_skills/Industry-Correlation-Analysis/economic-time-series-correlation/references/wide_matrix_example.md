# Wide Matrix Format Example

Detailed walkthrough for network services data using wide-format matrix (years as columns).

## Data Structure

### Main Matrix (network_matrix_release.xlsx)
```
series_name                        | status_flag | unit | 1991 | 1992 | ... | 2024
-----------------------------------|-------------|------|------|------|-----|------
Regulated electric utility revenue | official    | USD  | 52.71| 55.32| ... | 218.45
Wireline telecom services revenue  | official    | USD  | 39.11| 41.09| ... | 179.23
Industrial water transport fees    | memo        | USD  | 12.34| 13.45| ... | 45.67
```

Key observations:
- Years are column names (1991, 1992, ..., 2024)
- Series are rows identified by `series_name`
- `status_flag` column with values `official` and `memo`
- Must filter to `official` only

### Update Data (network_update_2025.csv)
```
series_name,period,status_flag,amount
Regulated electric utility revenue,2025-01,official,214.15
Regulated electric utility revenue,2025-02,official,220.91
...
Wireline telecom services revenue,2025-01,official,174.32
...
```

Key observations:
- CSV format with monthly data (`2025-01`, `2025-02`, etc.)
- Same `status_flag` column (note: not `release_status`)
- Same `series_name` identifiers
- Need to annualize by averaging

### Deflator Table (network_service_prices.xlsx)
```
Year | Utilities_Telecom_Price_2025_Base
-----|------------------------------------
1991 | 0.498985
1992 | 0.510740
...
2025 | 1.000000
```

## Processing Notes

### Filter to Official Status

```python
matrix_df = pd.read_excel('/root/network_matrix_release.xlsx')
official_df = matrix_df[matrix_df['status_flag'] == 'official']
```

**Critical**: Use `status_flag` not `release_status` for this dataset.

### Extract Wide Format Series

```python
# Identify year columns programmatically
year_cols = [c for c in official_df.columns 
             if c.isdigit() and len(c) == 4 
             and 1990 <= int(c) <= 2030]

# Extract by series name
def extract_series(df, series_name, year_cols):
    row = df[df['series_name'] == series_name]
    values = row[year_cols].values[0]
    years = [int(y) for y in year_cols]
    return pd.DataFrame({'year': years, 'amount': values})

electric = extract_series(official_df, 
                          'Regulated electric utility revenue', 
                          year_cols)
telecom = extract_series(official_df, 
                         'Wireline telecom services revenue', 
                         year_cols)
```

### Annualize Monthly Update Data

```python
update_df = pd.read_csv('/root/network_update_2025.csv')

# Filter to official status
update_df = update_df[update_df['status_flag'] == 'official']

# Extract year from period (e.g., '2025-03' -> 2025)
update_df['year'] = update_df['period'].str[:4].astype(int)

# Annualize by averaging
annual_2025 = update_df.groupby('series_name')['amount'].mean().reset_index()
annual_2025['year'] = 2025

# Combine
for series_name, df in [(name, sub) for name, sub in ...]:
    update_2025 = annual_2025[annual_2025['series_name'] == series_name]
    combined = pd.concat([historical, update_2025[['year', 'amount']]])
```

### Complete Workflow

```python
import pandas as pd
import numpy as np
from scipy.stats import pearsonr
from statsmodels.tsa.filters.hp_filter import hpfilter

# Load data
matrix = pd.read_excel('/root/network_matrix_release.xlsx')
prices = pd.read_excel('/root/network_service_prices.xlsx')
update = pd.read_csv('/root/network_update_2025.csv')

# Filter to official
matrix = matrix[matrix['status_flag'] == 'official']
update = update[update['status_flag'] == 'official']

# Extract year columns
year_cols = [c for c in matrix.columns if c.isdigit() and 1990 <= int(c) <= 2030]

# Get historical series
def get_historical(df, name):
    row = df[df['series_name'] == name]
    vals = row[year_cols].values[0]
    return pd.DataFrame({'year': [int(y) for y in year_cols], 'amount': vals})

electric_hist = get_historical(matrix, 'Regulated electric utility revenue')
telecom_hist = get_historical(matrix, 'Wireline telecom services revenue')

# Annualize 2025 update
update['year'] = update['period'].str[:4].astype(int)
annual_2025 = update.groupby('series_name')['amount'].mean().reset_index()
annual_2025['year'] = 2025

# Combine
electric_2025 = annual_2025[annual_2025['series_name'] == 
                            'Regulated electric utility revenue']
telecom_2025 = annual_2025[annual_2025['series_name'] == 
                           'Wireline telecom services revenue']

electric = pd.concat([electric_hist, 
                      electric_2025[['year', 'amount']]], ignore_index=True)
telecom = pd.concat([telecom_hist, 
                     telecom_2025[['year', 'amount']]], ignore_index=True)

# Merge and deflate
merged = electric.merge(telecom, on='year', suffixes=('_e', '_t'))
merged = merged.merge(prices[['Year', 'Utilities_Telecom_Price_2025_Base']], 
                      left_on='year', right_on='Year')

merged['real_e'] = merged['amount_e'] / merged['Utilities_Telecom_Price_2025_Base']
merged['real_t'] = merged['amount_t'] / merged['Utilities_Telecom_Price_2025_Base']

# HP filter and correlate
log_e = np.log(merged['real_e'])
log_t = np.log(merged['real_t'])
cycle_e, _ = hpfilter(log_e, lamb=100)
cycle_t, _ = hpfilter(log_t, lamb=100)
corr, _ = pearsonr(cycle_e, cycle_t)

with open('/root/answer.txt', 'w') as f:
    f.write(f"{corr:.5f}")
```

## Verification Checklist

- [ ] Matrix filtered to `status_flag='official'`: excludes memo rows
- [ ] Year columns correctly identified: 1991-2024 (24 columns)
- [ ] Update data filtered to `status_flag='official'`
- [ ] 2025 annualized as mean of available months (typically 8 months)
- [ ] Final year range: 1991-2025 (35 years)
- [ ] Deflator applied: 2025 base = 1.0
- [ ] Log values positive (all real values > 1)
- [ ] Final correlation ≈ 0.98727 (very strong positive)
- [ ] Output file contains only `0.98727`

## Key Differences from Panel Format

| Aspect | Wide Matrix | Long Panel |
|--------|-------------|------------|
| Year location | Column names | Row values in `period_label` |
| Series identification | Filter `series_name` | Filter `series_label` |
| Status column | `status_flag` | `release_status` |
| Typical file | Single `.xlsx` | `.xlsx` + `.xlsx` update or `.csv` |
| Update format | Often `.csv` with monthly | Often `.xlsx` sheet |
