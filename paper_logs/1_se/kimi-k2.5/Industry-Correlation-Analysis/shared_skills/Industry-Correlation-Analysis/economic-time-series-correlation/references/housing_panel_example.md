# Housing Panel Data Example

Detailed walkthrough for residential renovation spending vs building materials dealer shipments correlation using panel data structure.

## Data Structure

### AnnualPanel Sheet
```
series_label                    | period_label | period_kind | release_status | amount
--------------------------------|--------------|-------------|----------------|--------
Residential renovation spending | 1996         | annual      | prelim         | 41.90
Building materials dealer ship  | 2014         | annual      | prelim         | 118.96
...                             | ...          | ...         | ...            | ...
```

Key observations:
- Long format: series stacked vertically with `series_label` identifying each series
- `release_status` column with values `'prelim'` and `'final'`
- `period_kind` indicates frequency ('annual' vs 'monthly')
- Must filter to `'final'` status only

### Update2025 Sheet
```
series_label                    | month    | release_status | amount
--------------------------------|----------|----------------|--------
Residential renovation spending | 2025-06  | final          | 192.47
Building materials dealer ship  | 2025-07  | final          | 236.39
...                             | ...      | ...            | ...
```

Key observations:
- Monthly data for incomplete final year
- Same `series_label` and `release_status` structure
- `month` column in `YYYY-MM` format
- Need to annualize by averaging

### Deflator Table
```
Year | Construction_Input_Price_2025_Base
-----|------------------------------------
1995 | 0.467641
...  | ...
2025 | 1.000000
```

## Processing Notes

### Filter to Final Releases

```python
panel_df = pd.read_excel('/root/housing_materials_panel.xlsx', sheet_name='AnnualPanel')
panel_final = panel_df[panel_df['release_status'] == 'final']
# Result: 60 rows (30 years × 2 series)
```

### Annualize Monthly Update Data

```python
update_df = pd.read_excel('/root/update_2025.xlsx', sheet_name='Update2025')
update_final = update_df[update_df['release_status'] == 'final']

# Average 8 months of data for each series
annual_2025 = update_final.groupby('series_label')['amount'].mean().reset_index()
annual_2025['period_label'] = 2025
```

### Combine Sources

```python
# Add series-specific columns for merging
series_a_historical = panel_final[panel_final['series_label'] == 
                                  'Residential renovation spending'][['period_label', 'amount']]
series_b_historical = panel_final[panel_final['series_label'] == 
                                  'Building materials dealer shipments'][['period_label', 'amount']]

# Append 2025 annualized data
series_a_2025 = annual_2025[annual_2025['series_label'] == 
                            'Residential renovation spending'][['period_label', 'amount']]
series_b_2025 = annual_2025[annual_2025['series_label'] == 
                            'Building materials dealer shipments'][['period_label', 'amount']]

series_a = pd.concat([series_a_historical, series_a_2025], ignore_index=True)
series_b = pd.concat([series_b_historical, series_b_2025], ignore_index=True)
```

### Deflate and Correlate

Same pattern as other examples: merge on year, deflate using `Construction_Input_Price_2025_Base`, log-transform, HP filter with λ=100, compute Pearson correlation.

## Verification Checklist

- [ ] AnnualPanel filtered to `release_status='final'`: 60 rows expected
- [ ] Update2025 filtered to `release_status='final'`: 16 rows expected (8 months × 2 series)
- [ ] 2025 annualized values computed as mean of 8 monthly observations
- [ ] Final year range: 1995-2025 (31 years after combining)
- [ ] Log values positive (all real values > 1)
- [ ] Final correlation ≈ 0.93601 (strong positive)
- [ ] Output file contains only `0.93601` (no tabs, labels, or extra text)
