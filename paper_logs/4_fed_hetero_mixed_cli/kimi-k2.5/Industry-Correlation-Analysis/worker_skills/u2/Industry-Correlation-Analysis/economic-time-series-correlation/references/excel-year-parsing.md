# Parsing Year Markers from Economic Statistical Tables

Common formatting patterns found in BEA, Census Bureau, and Federal Reserve Excel releases.

## Trailing Dots

Published tables often format years with trailing dots to indicate annual data:
- Pattern: `'1994.'`, `'1995.'`, `'2024.'`
- Cause: Typesetting convention in statistical publications
- Solution:
  ```python
  # Method 1: Strip character
  df['Year'] = df['Year'].astype(str).str.rstrip('.').astype(int)

  # Method 2: Float conversion (robust to dots)
  df['Year'] = df['Year'].astype(str).astype(float).astype(int)
  ```

## Mixed Annual and Quarterly Markers

Recent years often include quarterly breakdowns in annual tables.

### Roman Numeral Formats
- Prefixed: `'2025:I'`, `'2025:II'`, `'2025:III'`, `'2025:IV'`
- Roman continuation: `'I'`, `'II'`, `'III'`, `'IV'` (in rows immediately following annual year)

### Arabic Numeral Formats
- Prefixed with space: `'2025 Q1'`, `'2025 Q2'`, `'2025 Q3'`, `'2025 Q4'`
- Continuation without year: `'Q1'`, `'Q2'`, `'Q3'`, `'Q4'` (rows following a prefixed quarter)

**Detection**: Check for non-numeric characters after stripping dots:
```python
# Detect any quarterly marker pattern
mask = df['Year'].astype(str).str.contains(r'[:\-IVQ]|Q[1-4]', regex=True, na=False)
```

**Handling**:
1. Separate annual rows (parseable as integers) from quarterly rows
2. For prefixed quarters: extract year and quarter, groupby year, mean()
3. For continuation rows: forward-fill year from above, then groupby year

Example implementation:
```python
def parse_year_marker(val, last_year=None):
    s = str(val).strip()

    # Handle '2025:I' or '2025:II' format (Roman with colon)
    if ':' in s:
        year, q = s.split(':')
        return int(year), q

    # Handle '2025 Q1' format (Arabic with space)
    if ' Q' in s.upper():
        parts = s.split()
        year = int(parts[0])
        quarter = parts[1]  # 'Q1', 'Q2', etc.
        return year, quarter

    # Handle standalone Roman numerals (continuation)
    if s in ['I', 'II', 'III', 'IV']:
        return last_year, s

    # Handle standalone Q1, Q2, Q3, Q4 (continuation)
    if s.upper() in ['Q1', 'Q2', 'Q3', 'Q4']:
        return last_year, s

    # Handle trailing dots
    if '.' in s:
        return int(float(s)), None

    # Standard year
    return int(s), None
```

## Fiscal Year Notation

Some tables use fiscal year markers:
- Pattern: `'FY1994'`, `'1994/95'`, `'1994-95'`
- Solution: Extract first 4-digit sequence:
  ```python
  df['Year'] = df['Year'].str.extract(r'(\d{4})').astype(int)
  ```

## Panel/Long Format Data

Many BEA and Census releases use a "long" format with multiple series in one table:

### Structure
```
series_label, period_label, period_kind, release_status, amount
Residential renovation spending, 1995, annual, final, 38.43
Building materials dealer shipments, 1995, annual, final, 56.56
...
```

### Handling
```python
# Filter for specific series
renov = df[df['series_label'] == 'Residential renovation spending']

# Filter for final data only (preliminary may be revised)
renov_final = renov[renov['release_status'] == 'final']

# Pivot to wide format if needed
df_wide = df.pivot(index='period_label', columns='series_label', values='amount')
```

### Release Status
- `final`: Completed period, values are stable
- `prelim`: Preliminary estimate, subject to revision
- Best practice: Use `final` for historical analysis; be aware `prelim` may change

## Clean Quarterly Panel Format

Some statistical releases provide quarterly updates in a clean panel format with separate columns:

### Structure
```
series_code, subperiod, version, value
BR_REV_25, 2025-Q1, revised, 118.95
BR_REV_25, 2025-Q1, prelim, 123.71
BR_REV_25, 2025-Q2, revised, 127.71
BR_REV_25, 2025-Q2, prelim, 132.82
WH_EQP_25, 2025-Q1, revised, 94.30
WH_EQP_25, 2025-Q2, revised, 101.25
WH_EQP_25, 2025-Q3, revised, 102.24
...
```

### Handling
```python
# Filter for specific series and revised values only
df_series = df[(df['series_code'] == 'BR_REV_25') & (df['version'] == 'revised')]

# Parse subperiod column: '2025-Q1' -> year and quarter
df_series['year'] = df_series['subperiod'].str[:4].astype(int)
df_series['quarter'] = df_series['subperiod'].str.split('-Q').str[1].astype(int)

# Annualize by averaging all available quarters
annual_2025 = df_series['value'].mean()
```

### Version Column Values
- `revised`: Updated values, use for analysis
- `prelim`: Preliminary estimate, may be revised in future releases
- Best practice: Filter for `revised` only; if no revised values exist for a period, `prelim` may be used with caution

## Wide-Format Matrices

Some statistical releases provide data in wide format with years as columns:

### Structure
```
series_name, status_flag, unit, 1991, 1992, 1993, ..., 2024
Regulated electric utility revenue, official, billions, 52.71, 55.32, ...
Wireline telecom services revenue, official, billions, 39.11, 41.09, ...
```

### Handling
```python
# Identify year columns (4-digit strings)
year_cols = [c for c in df.columns if c.isdigit() and len(c) == 4]

# Filter for specific series and status
df_series = df[(df['series_name'] == 'Series Name') & 
              (df['status_flag'] == 'official')]

# Extract values as array
values = df_series[year_cols].values.flatten()
years = [int(c) for c in year_cols]
```

### Status Flags
- `official`: Finalized values for completed periods
- `memo`: Preliminary, supplementary, or informational values
- Best practice: Use `official` for analysis; `memo` values may be incomplete or revised

## Combining Historical Annual with Current-Year Monthly

A common pattern: complete annual data through year N-1, with monthly updates for year N:

### Historical Annual (Wide Format)
```python
# Extract years 1991-2024 from wide-format matrix
year_cols = [c for c in df.columns if c.isdigit() and len(c) == 4]
df_series = df[(df['series_name'] == 'Series Name') & 
                (df['status_flag'] == 'official')]
historical_values = df_series[year_cols].values.flatten()
```

### Current Year Monthly (Long Format)
```python
# Average monthly 'official' values for current year
monthly_2025 = df_monthly[(df_monthly['series_name'] == 'Series Name') & 
                          (df_monthly['status_flag'] == 'official')]
annual_2025 = monthly_2025['amount'].mean()
```

### Combine
```python
full_series = np.append(historical_values, annual_2025)
years = list(range(1991, 2026))  # 1991-2025
```

## Monthly Data in Update Sheets

Recent data often comes in a separate sheet with monthly granularity:

### Structure
```
series_name, period, status_flag, amount
Regulated electric utility revenue, 2025-01, official, 214.15
Regulated electric utility revenue, 2025-01, memo, 216.72
...
```

### Monthly-to-Annual Conversion
```python
# Filter for official values only
monthly_official = df_monthly[df_monthly['status_flag'] == 'official']

# Group by series and compute annual average
annual_2025 = monthly_official.groupby('series_name')['amount'].mean()
```

### Multiple Status Values Per Month
Some months have both `official` and `memo` values. Filter appropriately:
```python
# Use only official values
official_only = df[df['status_flag'] == 'official']
```

## Verification Checklist

Before analysis:
- [ ] Print `df['Year'].unique()` to spot non-numeric markers
- [ ] Verify year range continuity (no gaps)
- [ ] Confirm latest year handling (partial year quarters/months averaged or excluded consistently)
- [ ] Check for duplicate years post-parsing
- [ ] Ensure header rows (e.g., 'Period label') are excluded before parsing year columns
- [ ] Verify status_flag/release_status/version filtering (official/final/revised vs memo/prelim) is intentional
- [ ] For panel data, confirm series are correctly separated before merging
- [ ] For wide-format data, verify year columns are correctly identified as 4-digit strings
- [ ] For clean quarterly panel format, verify subperiod parsing and version filtering
