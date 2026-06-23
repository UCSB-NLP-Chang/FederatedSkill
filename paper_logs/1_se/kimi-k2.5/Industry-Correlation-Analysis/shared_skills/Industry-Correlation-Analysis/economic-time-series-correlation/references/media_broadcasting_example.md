# Media Broadcasting Correlation Example

Detailed walkthrough for broadcasting carriage receipts vs. advertising placement revenue.

## Data Structure

### Broadcasting Table (table_05)
```
Period label | Domestic total | Memo subtotal
-------------|----------------|--------------
1993.        | 35.15          | 28.82
1994.        | 37.61          | 30.84
...          | ...            | ...
2024.        | 179.64         | 147.30
2025 Q1      | 181.55         | 148.87
Q2           | 189.11         | 155.07      <- continuation row
Q3           | 196.67         | 161.27      <- continuation row
Source note  | NaN            | NaN         <- filter out
```

Key observations:
- Column is `Period label` (not `Year marker`)
- Value column is `Domestic total` (not `Private total` or `Memo subtotal`)
- Quarters marked as "2025 Q1", "Q2", "Q3" (space notation, not colon)
- Source note row has NaN values — must filter out

### Advertising Table (table_12)
Same structure as broadcasting table.

### Deflator Table
```
Calendar Year | Media_Services_Price_2025_Base | Unused_Index
----------------|--------------------------------|--------------
1993            | 0.457482                       | 0.471664
...             | ...                            | ...
2025            | 1.000000                       | 1.031000
```

- Base year is 2025 (index = 1.0)
- Year column is `Calendar Year` (not `Year`)

## Processing Notes

### Year Parsing for Space-Separated Quarters

```python
def parse_year_marker(marker):
    s = str(marker).strip()
    if s.lower().startswith('source'):
        return None
    # Handle "2025 Q1", "2025:I", or "II"
    if ' Q' in s:
        return int(s.split(' Q')[0])  # "2025 Q1" -> 2025
    if ':' in s:
        return int(s.split(':')[0])   # "2025:I" -> 2025
    try:
        return int(float(s))           # "1993." -> 1993
    except ValueError:
        return None                    # "Q2", "Q3" -> forward-fill

df['year'] = df['Period label'].apply(parse_year_marker)
df['year'] = df['year'].ffill().astype(int)
```

### Filter Source Notes

```python
# Critical: drop rows where Domestic total is NaN (source notes)
df = df.dropna(subset=['Domestic total'])
```

### Annual Averaging

```python
# Average Q1-Q3 for 2025
annual = df.groupby('year')['Domestic total'].mean().reset_index()
# Result: 2025 = (181.55 + 189.11 + 196.67) / 3 = 189.11
```

## Verification Checklist

- [ ] Years 1993-2025 inclusive (33 years of data)
- [ ] Source note rows excluded (check for NaN in value column)
- [ ] 2025 computed as average of available quarters
- [ ] Log values positive (all real values > 1)
- [ ] Final correlation ≈ 0.96366 (strong positive)
- [ ] Output file contains only `0.96366` (no tabs, labels, or extra text)