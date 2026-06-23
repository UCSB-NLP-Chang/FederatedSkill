# Alias-Mapped Data Example

Detailed walkthrough for wholesale distribution vs packaging shipments using alias-based series identification with priority deduplication.

## Data Structure

### series_aliases.csv (Mapping File)
```
requested_series,accepted_alias
Merchant wholesale turnover,Merchant wholesale turnover
Merchant wholesale turnover,merchant-wholesale-turnover
Merchant wholesale turnover,merchant wholesale net turnover
Packaging converters shipments,Packaging converters shipments
Packaging converters shipments,packaging-plants shipments
Packaging converters shipments,packaging converters domestic shipments
```

Key observations:
- Multiple accepted aliases per canonical series name
- Aliases may differ in case, spacing, and word order
- Must match case-insensitively

### Annual Data (distribution_packaging_release.xlsx)
```
target_alias                     | year_label | record_type | priority | amount
---------------------------------|------------|-------------|----------|--------
merchant wholesale net turnover  | FY-1998    | official    | 2        | 57.42
packaging-plants shipments       | FY-1995    | official    | 4        | 36.83
merchant-wholesale-turnover      | FY-2015    | official    | 2        | 129.51
...
```

Key observations:
- `target_alias` contains accepted aliases (may have duplicates across files)
- `year_label` uses `FY-YYYY` format (e.g., `FY-1998`)
- `record_type` with values `official` and `memo` — **CRITICAL FILTER**
- `priority` column for deduplication — lower values preferred
- Multiple rows may exist for same year/series with different priority

### 2025 Update Data (distribution_packaging_2025.xlsx)
```
target_alias                    | subperiod | record_type | priority | amount
--------------------------------|-----------|-------------|----------|--------
Packaging converters shipments  | 2025-Q1   | official    | 1        | 136.48
Merchant wholesale turnover     | 2025-Q1   | official    | 2        | 201.14
Packaging converters shipments  | 2025-Q2   | official    | 1        | 145.10
...
```

Key observations:
- Same `target_alias`, `record_type`, `priority` structure
- `subperiod` in `YYYY-QN` format (e.g., `2025-Q1`)
- Must filter to `record_type == 'official'` and deduplicate by priority
- Then annualize by averaging quarters

### Deflator Table (distribution_packaging_prices.xlsx)
```
Year | Distribution_Packaging_Price_2025_Base
-----|----------------------------------------
1990 | 0.433456
1991 | 0.445208
...
2025 | 1.000000
```

- Base year is 2025 (index = 1.0)
- Same deflator applies to both series

## Processing Notes

### Read and Parse Aliases
```python
import pandas as pd

# Read alias catalog
aliases_df = pd.read_csv('/root/series_aliases.csv')

# Build lookup: canonical name -> set of accepted aliases (lowercase)
series_aliases = {}
for name in aliases_df['requested_series'].unique():
    accepted = aliases_df[aliases_df['requested_series'] == name]['accepted_alias']
    series_aliases[name] = set(a.lower() for a in accepted)

# Result:
# {
#   'Merchant wholesale turnover': {'merchant wholesale turnover', 
#                                   'merchant-wholesale-turnover',
#                                   'merchant wholesale net turnover'},
#   'Packaging converters shipments': {'packaging converters shipments',
#                                      'packaging-plants shipments',
#                                      'packaging converters domestic shipments'}
# }
```

### Filter and Deduplicate Annual Data
```python
annual_df = pd.read_excel('/root/distribution_packaging_release.xlsx')

# Filter to official records only
official = annual_df[annual_df['record_type'] == 'official']

# Parse FY-prefixed years
official['year'] = official['year_label'].str.replace('FY-', '').astype(int)

# Extract series by alias matching (case-insensitive)
for series_name, alias_set in series_aliases.items():
    matched = official[official['target_alias'].str.lower().isin(alias_set)]
    
    # CRITICAL: Deduplicate by keeping minimum priority per year
    if matched.duplicated(subset=['year']).any():
        matched = matched.loc[matched.groupby('year')['priority'].idxmin()]
    
    # Sort by year
    series_data = matched.sort_values('year')[['year', 'amount']]
```

### Process 2025 Update Data
```python
update_df = pd.read_excel('/root/distribution_packaging_2025.xlsx')

# Filter to official
update_official = update_df[update_df['record_type'] == 'official']

# Extract year from subperiod (e.g., '2025-Q1' -> 2025)
update_official['year'] = update_official['subperiod'].str[:4].astype(int)

# Deduplicate by priority per series per quarter
for series_name, alias_set in series_aliases.items():
    matched = update_official[update_official['target_alias'].str.lower().isin(alias_set)]
    
    # Keep minimum priority per subperiod
    deduped = matched.loc[matched.groupby('subperiod')['priority'].idxmin()]
    
    # Annualize by averaging quarters
    annual_2025 = deduped['amount'].mean()
    print(f"{series_name} 2025: {annual_2025:.2f}")
```

### Complete Workflow
```python
import pandas as pd
import numpy as np
from scipy.stats import pearsonr
from statsmodels.tsa.filters.hp_filter import hpfilter

# Load data
aliases_df = pd.read_csv('/root/series_aliases.csv')
annual_df = pd.read_excel('/root/distribution_packaging_release.xlsx')
update_df = pd.read_excel('/root/distribution_packaging_2025.xlsx')
prices = pd.read_excel('/root/distribution_packaging_prices.xlsx')

# Build alias sets
series_aliases = {}
for name in aliases_df['requested_series'].unique():
    accepted = aliases_df[aliases_df['requested_series'] == name]['accepted_alias']
    series_aliases[name] = set(a.lower() for a in accepted)

# Process annual data
official = annual_df[annual_df['record_type'] == 'official'].copy()
official['year'] = official['year_label'].str.replace('FY-', '').astype(int)

series_data = {}
for series_name, alias_set in series_aliases.items():
    matched = official[official['target_alias'].str.lower().isin(alias_set)]
    deduped = matched.loc[matched.groupby('year')['priority'].idxmin()]
    series_data[series_name] = deduped.sort_values('year')[['year', 'amount']]

# Process 2025 update
update_official = update_df[update_df['record_type'] == 'official'].copy()

annual_2025_values = {}
for series_name, alias_set in series_aliases.items():
    matched = update_official[update_official['target_alias'].str.lower().isin(alias_set)]
    deduped = matched.loc[matched.groupby('subperiod')['priority'].idxmin()]
    annual_2025_values[series_name] = deduped['amount'].mean()

# Combine and deflate
for series_name in series_aliases:
    hist = series_data[series_name]
    update_row = pd.DataFrame({'year': [2025], 'amount': [annual_2025_values[series_name]]})
    combined = pd.concat([hist, update_row], ignore_index=True)
    series_data[series_name] = combined

# Merge series and deflator
merged = series_data['Merchant wholesale turnover'].merge(
    series_data['Packaging converters shipments'], 
    on='year', suffixes=('_w', '_p')
)
merged = merged.merge(prices, on='Year')

merged['real_w'] = merged['amount_w'] / merged['Distribution_Packaging_Price_2025_Base']
merged['real_p'] = merged['amount_p'] / merged['Distribution_Packaging_Price_2025_Base']

# HP filter and correlate
log_w = np.log(merged['real_w'])
log_p = np.log(merged['real_p'])
cycle_w, _ = hpfilter(log_w, lamb=100)
cycle_p, _ = hpfilter(log_p, lamb=100)
corr, _ = pearsonr(cycle_w, cycle_p)

with open('/root/answer.txt', 'w') as f:
    f.write(f"{corr:.5f}")
```

## Key Differences from Other Patterns

| Aspect | Alias-Mapped | Catalog-Mapped | Wide Matrix | Long Panel |
|--------|-------------|---------------|-------------|------------|
| Series identification | Multiple aliases in CSV | Codes mapped across files | `series_name` column | `series_label` column |
| Status/version filter | `record_type` (`official`/`memo`) | `version` (`revised`/`prelim`) | `status_flag` | `release_status` |
| Deduplication | `priority` column (min value) | Usually none needed | Usually none needed | Usually none needed |
| Year format | `FY-YYYY` prefix | Various | Column names or various | Various |
| Update data | Separate `.xlsx` with quarters | Separate `.xlsx` with quarters | Often `.csv` monthly | Often `.xlsx` sheet |

## Critical Decision Rules

1. **Check for alias file first** — Look for `series_aliases.csv`, `aliases.csv`, or files with `alias` in name
2. **Case-insensitive matching** — Always lowercase both aliases and target values before matching
3. **Priority deduplication** — After filtering by `record_type`, always check for `priority` column and deduplicate
4. **FY year parsing** — Replace `FY-` prefix before converting to integer year
5. **Multiple status columns** — Alias-mapped uses `record_type`, not `version` or `release_status`

## Verification Checklist

- [ ] Alias file read and parsed correctly (case-insensitive matching)
- [ ] Historical years: typically 1990-2024 (check actual data)
- [ ] Record type filter applied: only `official` rows retained
- [ ] Priority deduplication applied: one row per year per series
- [ ] FY prefix removed from year labels before conversion
- [ ] 2025 annualized from available quarters (Q1-Q3 in this example)
- [ ] Final year range: 1990-2025 (36 years in this example)
- [ ] Log values positive (all real values > 1)
- [ ] Final correlation in expected range (this example: ~0.976)
- [ ] Output file contains only numeric coefficient, 5 decimal places
