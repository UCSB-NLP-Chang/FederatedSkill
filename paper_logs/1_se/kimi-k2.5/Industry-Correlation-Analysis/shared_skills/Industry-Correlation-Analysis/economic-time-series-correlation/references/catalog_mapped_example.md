# Catalog-Mapped Multi-File Example

Detailed walkthrough for freight brokerage revenue vs warehouse equipment outlays using a catalog-driven data structure.

## Data Structure

### series_catalog.csv (Mapping File)
```
requested_series,history_sheet,history_code,current_sheet,current_code,deflator_column
Freight brokerage revenue,AnnualSeries,BROKER_REV,QuarterlyUpdate,BR_REV_25,Transport_Services_Price_2025_Base
Warehouse equipment outlays,AnnualSeries,WHSE_EQUIP,QuarterlyUpdate,WH_EQP_25,Warehouse_Equipment_Price_2025_Base
```

Key observations:
- Catalog maps logical series names to file-specific codes
- `history_code`: column name in historical file
- `current_code`: series identifier in current/quarterly file
- `deflator_column`: series-specific price index (different deflators per series)

### Historical Data (logistics_history.xlsx)
```
calendar_year | BROKER_REV | WHSE_EQUIP | DISTRACTOR_SERIES
--------------|------------|------------|------------------
1993          | 31.46      | 23.84      | 33.03
1994          | 33.15      | 24.98      | 34.81
...           | ...        | ...        | ...
2024          | 119.75     | 94.28      | 125.83
```

- Wide format with multiple series as columns
- Year column is `calendar_year` (not `Year` or `Period label`)
- Contains distractor columns that must be ignored

### Current Release (logistics_current_release.xlsx)
```
series_code | subperiod | version  | value
------------|-----------|----------|-------
BR_REV_25   | 2025-Q2   | prelim   | 132.82
WH_EQP_25   | 2025-Q3   | revised  | 102.24
WH_EQP_25   | 2025-Q2   | revised  | 101.25
BR_REV_25   | 2025-Q2   | revised  | 127.71
```

Key observations:
- Long/stacked format: multiple series in same table
- `version` column with values `'revised'` and `'prelim'` — **CRITICAL FILTER**
- `subperiod` in `YYYY-QN` format (e.g., `2025-Q1`)
- Must filter to `version == 'revised'` to exclude preliminary estimates
- Different from `release_status`/`status_flag` used in other datasets

### Price Data (logistics_price_book.xlsx)
```
Year | Transport_Services_Price_2025_Base | Warehouse_Equipment_Price_2025_Base
-----|------------------------------------|------------------------------------
1993 | 0.503246                           | 0.537879
1994 | 0.515784                           | 0.549906
...  | ...                                | ...
2025 | 1.000000                           | 1.000000
```

Key observations:
- Multiple deflator columns (one per series type)
- Both share base year 2025 (index = 1.0)
- Must apply correct deflator to each series

## Processing Notes

### Read Catalog First
```python
catalog = pd.read_csv('/root/series_catalog.csv')
# Extract mapping for each series
freight_info = catalog[catalog['requested_series'] == 'Freight brokerage revenue'].iloc[0]
warehouse_info = catalog[catalog['requested_series'] == 'Warehouse equipment outlays'].iloc[0]
```

### Extract Historical by Column Code
```python
history = pd.read_excel('/root/logistics_history.xlsx')
# Use history_code from catalog
freight_hist = history[['calendar_year', freight_info['history_code']]].copy()
freight_hist.columns = ['year', 'nominal_value']
```

### Filter Current Release by Version
```python
current = pd.read_excel('/root/logistics_current_release.xlsx')
# CRITICAL: Filter to 'revised' version (not 'prelim')
current_revised = current[current['version'] == 'revised']

# Extract series using current_code from catalog
freight_2025 = current_revised[current_revised['series_code'] == freight_info['current_code']]
```

### Annualize Quarterly Data
```python
# Average available quarters for 2025
annual_2025 = freight_2025['value'].mean()  # (118.95 + 127.71 + 128.97) / 3 = 125.21
```

### Apply Series-Specific Deflators
```python
prices = pd.read_excel('/root/logistics_price_book.xlsx')

# Each series uses its own deflator column from catalog
freight_deflator_col = freight_info['deflator_column']
warehouse_deflator_col = warehouse_info['deflator_column']

# Merge and deflate separately
freight_merged = freight_series.merge(
    prices[['Year', freight_deflator_col]], 
    left_on='year', right_on='Year'
)
freight_merged['real_value'] = freight_merged['nominal_value'] / freight_merged[freight_deflator_col]
```

## Key Differences from Other Patterns

| Aspect | Catalog-Mapped | Wide Matrix | Long Panel |
|--------|---------------|-------------|------------|
| Series identification | Via catalog mapping | `series_name` column | `series_label` column |
| Status/version filter | `version` (`revised`/`prelim`) | `status_flag` | `release_status` |
| Deflator handling | Multiple columns, series-specific | Usually single column | Usually single column |
| Historical file layout | Multiple series as columns | Single series per row or years as columns | Long/stacked format |
| Current file layout | Long format with `series_code` | Often CSV with monthly | Often separate sheet |

## Critical Decision Rules

1. **Always check for catalog file first** — Look for `catalog`, `mapping`, or `series_*.csv` files
2. **Version filter vs Status filter** — If you see `version` column with `revised`/`prelim`, use that; if you see `status_flag` or `release_status`, use those instead
3. **Multiple deflators** — Check if deflator table has multiple price columns; if so, use catalog mapping or match by series type
4. **Ignore distractor columns** — Historical files may contain extra series not in the catalog

## Verification Checklist

- [ ] Catalog file read and parsed correctly
- [ ] Historical years: typically 1990s-2024 (check catalog for range)
- [ ] Version filter applied: only `revised` rows retained for 2025
- [ ] 2025 annualized from available quarters (typically Q1-Q3)
- [ ] Correct deflator column matched to each series
- [ ] Final year range: check catalog or data (commonly 1993-2025 = 33 years)
- [ ] Log values positive (all real values > 1)
- [ ] Final correlation in expected range (this example: ~0.95 for related logistics series)
- [ ] Output file contains only numeric coefficient, 5 decimal places
