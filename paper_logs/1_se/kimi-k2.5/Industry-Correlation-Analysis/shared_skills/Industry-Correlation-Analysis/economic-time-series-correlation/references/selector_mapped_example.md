# Selector-Mapped Multi-Source Example

Detailed walkthrough for temperature-controlled storage fees vs urban last-mile parcel charges using a selector-driven multi-source data structure.

## Data Structure

### coldchain_series_register.csv (Mapping File)
```
requested_series,history_code,history_status,current_code,deflator_column
Temperature-controlled storage fees,CC_STOR,benchmark,CC_STOR_25,Cold_Storage_Price_2025_Base
Urban last-mile parcel charges,LM_PARCEL,benchmark,LM_PARCEL_25,Last_Mile_Services_Price_2025_Base
```

Key observations:
- Catalog maps logical series names to file-specific codes
- `history_code`: series identifier in historical file
- `current_code`: series identifier in update files
- `history_status`: filter value for historical data (`benchmark`)
- `deflator_column`: series-specific price index (different deflators per series)

### Historical Data (coldchain_archive.xlsx, sheet 'HistoryMatrix')
```
series_code | status_bucket | unit | 1994 | 1995 | ... | 2024
------------|---------------|------|------|------|-----|------
LM_PARCEL   | benchmark     | usd_bn | 24.83 | 25.61 | ... | 132.41
AIR_LIFT    | benchmark     | usd_bn | 21.01 | 21.69 | ... | 106.61
LM_PARCEL   | memo          | usd_bn | 24.38 | 25.15 | ... | 130.03
CC_STOR     | benchmark     | usd_bn | 29.80 | 30.72 | ... | 144.78
CC_STOR     | memo          | usd_bn | 30.34 | 31.28 | ... | 147.39
```

Key observations:
- Wide format: years as columns (1994-2024)
- `status_bucket` column with values `benchmark` and `memo` — **CRITICAL FILTER**
- `series_code` identifies series (matches `history_code` from register)
- Both series have `benchmark` (official) and `memo` (alternative) rows

### Selector Workbook (coldchain_update_selector.xlsx, sheet 'UseThese')
```
series_code  | month    | preferred_source | preferred_version
-------------|----------|------------------|------------------
CC_STOR_25   | 2025-01  | A                | city-release
CC_STOR_25   | 2025-02  | B                | central-release
CC_STOR_25   | 2025-03  | A                | city-release
...          | ...      | ...              | ...
LM_PARCEL_25 | 2025-01  | B                | central-release
LM_PARCEL_25 | 2025-02  | A                | city-release
...          | ...      | ...              | ...
```

Key observations:
- `preferred_source`: 'A' or 'B' maps to `coldchain_updates_a.csv` or `coldchain_updates_b.csv`
- `preferred_version`: specific version to match (e.g., 'city-release', 'central-release', 'draft-release')
- `month`: YYYY-MM format for monthly observations
- Series code matches `current_code` from register
- **CRITICAL**: Must use selector to choose correct source and version for each month

### Update Files (coldchain_updates_a.csv, coldchain_updates_b.csv)
```
# updates_a.csv
series_code,month,version,amount
LM_PARCEL_25,2025-02,draft-release,139.77
LM_PARCEL_25,2025-08,draft-release,146.9
CC_STOR_25,2025-07,draft-release,156.6
...

# updates_b.csv
LM_PARCEL_25,2025-06,central-release,145.84
CC_STOR_25,2025-05,central-release,157.03
...
```

Key observations:
- Same structure in both files
- `version` column with values like 'draft-release', 'city-release', 'central-release'
- Multiple versions may exist for same series/month across files
- Some `amount` values may be blank/missing
- Must match `preferred_source` → file and `preferred_version` → row

### Price Data (coldchain_price_book.xlsx, sheet 'Indices')
```
Calendar Year | Cold_Storage_Price_2025_Base | Last_Mile_Services_Price_2025_Base
--------------|------------------------------|-----------------------------------
1994          | 0.503246                     | 0.456925
1995          | 0.515784                     | 0.470164
...           | ...                          | ...
2025          | 1.000000                     | 1.000000
```

Key observations:
- Multiple deflator columns (one per series type)
- Year column is `Calendar Year` (not `Year`)
- Both share base year 2025 (index = 1.0)
- Must apply correct deflator to each series

## Processing Notes

### Read Register First
```python
register = pd.read_csv('/root/coldchain_series_register.csv')
# Extract mapping for each series
stor_info = register[register['requested_series'] == 
                     'Temperature-controlled storage fees'].iloc[0]
parcel_info = register[register['requested_series'] == 
                       'Urban last-mile parcel charges'].iloc[0]
```

### Extract Historical with Status Filter
```python
archive = pd.read_excel('/root/coldchain_archive.xlsx', sheet_name='HistoryMatrix')

# CRITICAL: Filter to benchmark status only
benchmark = archive[archive['status_bucket'] == 'benchmark']

# Extract series using history_code from register
stor_hist = benchmark[benchmark['series_code'] == stor_info['history_code']]
parcel_hist = benchmark[benchmark['series_code'] == parcel_info['history_code']]

# Extract year columns and values
year_cols = [c for c in archive.columns if c.isdigit() and len(c) == 4]
years = [int(y) for y in year_cols]
stor_values = stor_hist[year_cols].values[0]
parcel_values = parcel_hist[year_cols].values[0]
```

### Apply Selector for 2025 Update Data
```python
selector = pd.read_excel('/root/coldchain_update_selector.xlsx', sheet_name='UseThese')
updates_a = pd.read_csv('/root/coldchain_updates_a.csv')
updates_b = pd.read_csv('/root/coldchain_updates_b.csv')

def get_selector_annual(selector_df, updates_a, updates_b, series_code):
    """Get annual value by applying selector rules."""
    sel = selector_df[selector_df['series_code'] == series_code]
    values = []
    
    for _, row in sel.iterrows():
        # Choose source file based on preferred_source
        source_df = updates_a if row['preferred_source'] == 'A' else updates_b
        
        # Match series, month, and preferred_version
        match = source_df[
            (source_df['series_code'] == row['series_code']) &
            (source_df['month'] == row['month']) &
            (source_df['version'] == row['preferred_version'])
        ]
        
        # Only include if found and amount is not null
        if len(match) > 0 and not pd.isna(match['amount'].iloc[0]):
            values.append(match['amount'].iloc[0])
    
    # Annualize by averaging valid months
    return np.mean(values) if values else np.nan

stor_2025 = get_selector_annual(selector, updates_a, updates_b, 'CC_STOR_25')
parcel_2025 = get_selector_annual(selector, updates_a, updates_b, 'LM_PARCEL_25')
# Result: 8 months for storage, 7 months for parcel (one blank excluded)
```

### Apply Series-Specific Deflators
```python
prices = pd.read_excel('/root/coldchain_price_book.xlsx', sheet_name='Indices')

# Combine historical and 2025 data
stor_combined = pd.DataFrame({
    'year': list(range(1994, 2025)) + [2025],
    'nominal': list(stor_values) + [stor_2025]
})
parcel_combined = pd.DataFrame({
    'year': list(range(1994, 2025)) + [2025],
    'nominal': list(parcel_values) + [parcel_2025]
})

# Merge with deflators
stor_merged = stor_combined.merge(
    prices[['Calendar Year', 'Cold_Storage_Price_2025_Base']],
    left_on='year', right_on='Calendar Year'
)
parcel_merged = parcel_combined.merge(
    prices[['Calendar Year', 'Last_Mile_Services_Price_2025_Base']],
    left_on='year', right_on='Calendar Year'
)

# Deflate
stor_merged['real'] = stor_merged['nominal'] / stor_merged['Cold_Storage_Price_2025_Base']
parcel_merged['real'] = parcel_merged['nominal'] / parcel_merged['Last_Mile_Services_Price_2025_Base']
```

### HP Filter and Correlate
```python
from statsmodels.tsa.filters.hp_filter import hpfilter
from scipy.stats import pearsonr

log_stor = np.log(stor_merged['real'])
log_parcel = np.log(parcel_merged['real'])

cycle_stor, _ = hpfilter(log_stor, lamb=100)
cycle_parcel, _ = hpfilter(log_parcel, lamb=100)

corr, _ = pearsonr(cycle_stor, cycle_parcel)
# Result: 0.92431

with open('/root/answer.txt', 'w') as f:
    f.write(f"{corr:.5f}")
```

## Key Differences from Other Patterns

| Aspect | Selector-Mapped | Catalog-Mapped | Alias-Mapped | Wide Matrix |
|--------|-----------------|----------------|--------------|-------------|
| Series identification | Via register mapping | Via catalog mapping | Multiple aliases | `series_name`/`series_code` |
| Status/version filter | `status_bucket` for historical; `preferred_version` in selector | `version` (`revised`/`prelim`) | `record_type` (`official`/`memo`) | `status_flag`/`status_bucket` |
| Multi-source handling | Selector specifies A/B file per month | Usually single source | Usually single source | Usually single source |
| Deduplication | Selector rules (explicit) | None usually | `priority` column | None usually |
| Update data | Monthly with version selection | Quarterly with version filter | Annual with priority | Monthly with status filter |
| Deflator handling | Multiple columns, series-specific | Multiple columns, series-specific | Usually single column | Usually single column |

## Critical Decision Rules

1. **Check for register/catalog file first** — Look for `*_register.csv`, `catalog.csv`, or `series_*.csv` files
2. **Check for selector file** — Look for `*_selector.xlsx` with `preferred_source` and `preferred_version` columns
3. **Filter historical by status_bucket** — If present, use `'benchmark'` to exclude `'memo'` rows
4. **Match selector columns exactly** — Verify actual column names (e.g., `preferred_source` not `source_file`)
5. **Handle blank amounts** — Exclude null values from annual average
6. **Parse year from month column** — Use `str[:4]` or `str.split('-')[0]` for YYYY-MM format

## Verification Checklist

- [ ] Register file read and parsed correctly
- [ ] Historical data filtered by `status_bucket='benchmark'`
- [ ] Year columns correctly identified: 1994-2024 (31 columns)
- [ ] Selector file read with correct columns: `preferred_source`, `preferred_version`, `month`
- [ ] Both update files (A and B) read successfully
- [ ] Selector rules applied: correct source file chosen for each month
- [ ] Version matching applied: `preferred_version` matched in source file
- [ ] Blank/missing amounts excluded from annual average
- [ ] 2025 annualized from valid months (8 storage, 7 parcel in this example)
- [ ] Correct deflator column matched to each series
- [ ] Final year range: 1994-2025 (32 years)
- [ ] Log values positive (all real values > 1)
- [ ] Final correlation in expected range (this example: ~0.924)
- [ ] Output file contains only numeric coefficient, 5 decimal places
