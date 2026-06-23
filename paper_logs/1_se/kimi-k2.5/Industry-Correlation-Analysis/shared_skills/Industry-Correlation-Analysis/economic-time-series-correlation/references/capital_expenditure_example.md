# Capital Expenditure Correlation Example

Detailed walkthrough for equipment vs. software investment correlation.

## Data Structure

### Capital Tables (equipment, software)
```
Year marker | Private total
------------|-------------
1992.       | 51.02
...         | ...
2024.       | 217.67
2025:I      | 217.86
II          | 229.21   <- continuation row
III         | 233.75   <- continuation row
```

Key observations:
- Final year has partial quarterly data
- Roman numerals without year prefix continue from prior row
- Need to forward-fill the year base

### Deflator Table
```
Year | Capital_Goods_Price_2025_Base
-----|------------------------------
1992 | 0.452573
...  | ...
2025 | 1.000000
```

- Base year is 2025 (index = 1.0)
- Same deflator applies to both equipment and software

## Processing Notes

### Year Parsing Edge Cases

```python
def parse_year_marker(marker):
    s = str(marker)
    if ':' in s:
        return int(s.split(':')[0])  # "2025:I" -> 2025
    try:
        return int(float(s))  # "1992." -> 1992
    except ValueError:
        return None  # "II", "III" will be forward-filled

# Apply and forward-fill
df['year'] = df['Year marker'].apply(parse_year_marker)
df['year'] = df['year'].ffill().astype(int)
```

### Averaging Quarters

With partial 2025 data (Q1-Q3 only):
```python
annual_2025 = (217.86 + 229.21 + 233.75) / 3  # = 226.94
```

This differs from simply taking the last value (233.75) or first value (217.86).

### Real Value Calculation

```python
# Nominal / deflator = real (in 2025 dollars)
real_equip_1992 = 51.02 / 0.452573  # ≈ 112.73
```

No need to multiply by 100; the deflator is already scaled appropriately.

## Verification Checklist

- Years 1992-2025 inclusive (34 years)
- Equipment real values range: ~112 to ~218
- Software real values range: ~74 to ~158
- Log values should be positive (check: all real values > 1)
- Cyclical components should sum to ~0
- Final correlation ≈ 0.60349