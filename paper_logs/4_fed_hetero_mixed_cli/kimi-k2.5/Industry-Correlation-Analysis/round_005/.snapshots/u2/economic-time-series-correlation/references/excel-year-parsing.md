# Parsing Year Markers from Economic Statistical Tables

Common formatting patterns found in BEA, Census Bureau, and Federal Reserve Excel releases.

## Wide/Matrix Format

Many statistical tables use **wide format** where years are column headers:

```
series_name, status_flag, unit, 1991, 1992, 1993, 1994, ...
Gross Domestic Product, final, billions, 5963, 6520, 6879, 7309, ...
```

**Handling**: No parsing needed. Select year columns directly:
```python
# Identify year columns (4-digit numeric strings)
year_cols = [c for c in df.columns if c.isdigit()]
values = df[df['series_name'] == 'GDP'][year_cols].values[0]
years = [int(c) for c in year_cols]
```

## Trailing Dots

Published tables often format years with trailing dots:
- Pattern: `'1994.'`, `'1995.'`, `'2024.'`
- Solution:
  ```python
  df['Year'] = df['Year'].astype(str).str.rstrip('.').astype(int)
  ```

## Mixed Annual and Quarterly Markers

### Roman Numeral Formats
- Prefixed: `'2025:I'`, `'2025:II'`, `'2025:III'`, `'2025:IV'`
- Continuation: `'I'`, `'II'`, `'III'`, `'IV'`

### Arabic Numeral Formats
- Prefixed: `'2025 Q1'`, `'2025 Q2'`, `'2025 Q3'`, `'2025 Q4'`
- Dash format: `'2025-Q1'`, `'2025-Q2'`
- Continuation: `'Q1'`, `'Q2'`, `'Q3'`, `'Q4'`

**Detection**:
```python
mask = df['Year'].astype(str).str.contains(r'[:\-IVQ]|Q[1-4]', regex=True, na=False)
```

## Panel/Long Format

Structure with multiple series in one table:
```
series_label, period_label, period_kind, release_status, amount
GDP, 1995, annual, final, 7636.2
Consumption, 1995, annual, final, 5147.5
```

**Handling**:
```python
gdp = df[df['series_label'] == 'GDP']
gdp_final = gdp[gdp['release_status'] == 'final']
```

## Monthly Data in Update Sheets

Recent data often comes separately with monthly granularity:
```
series_name, month, status_flag, amount
GDP, 2025-01, official, 21500.3
GDP, 2025-02, official, 21620.1
```

**Monthly-to-Annual**:
```python
monthly_official = df[df['status_flag'] == 'official']
annual_value = monthly_official['amount'].mean()
```

## Verification Checklist

- [ ] Identify format: wide (years as columns) vs long (years as values)
- [ ] Print unique status column values to verify filtering
- [ ] Check year range continuity
- [ ] For combined data: verify latest partial year is averaged correctly
- [ ] Ensure header rows are excluded before parsing
