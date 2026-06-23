# Selector Workbook Pattern

When multiple update files exist with different versions of the same observations, a selector workbook explicitly specifies which source file and version to use for each (series, period) combination.

## When to Use

- Multiple update files (e.g., `updates_a.csv`, `updates_b.csv`) with overlapping observations
- Each file contains different versions (e.g., `city-release`, `central-release`, `draft-release`)
- A separate selector file specifies the preferred source and version for each observation
- Priority-based deduplication is NOT appropriate because selection is explicit, not rule-based

## Selector Workbook Structure

Typical columns:
- `series_code`: Series identifier (e.g., 'CC_STOR_25', 'LM_PARCEL_25')
- `month` or `period`: Time period (e.g., '2025-01', '2025-02')
- `preferred_source`: Which file to use (e.g., 'A', 'B', or file identifier)
- `preferred_version`: Which version within that file (e.g., 'city-release', 'central-release')

Example:
```
series_code,month,preferred_source,preferred_version
CC_STOR_25,2025-01,A,city-release
CC_STOR_25,2025-02,B,central-release
LM_PARCEL_25,2025-01,B,central-release
LM_PARCEL_25,2025-02,A,city-release
```

## Implementation Pattern

```python
import pandas as pd

# Read all update sources
updates_a = pd.read_csv('updates_a.csv')
updates_b = pd.read_csv('updates_b.csv')

# Read selector workbook
selector = pd.read_excel('selector.xlsx', sheet_name='UseThese')

# Build lookup: (series_code, month) -> (source, version)
lookup = {}
for _, row in selector.iterrows():
    lookup[(row['series_code'], row['month'])] = (row['preferred_source'], row['preferred_version'])

# Select observations
selected = []
for (series_code, month), (source, version) in lookup.items():
    if source == 'A':
        df = updates_a
    else:
        df = updates_b
    
    obs = df[(df['series_code'] == series_code) &
             (df['month'] == month) &
             (df['version'] == version)]
    
    if len(obs) == 0:
        print(f"Warning: No observation for {series_code} {month} from source {source} version {version}")
        continue
    
    # Skip blank/NaN amounts
    amount = obs['amount'].iloc[0]
    if pd.isna(amount) or amount == '':
        print(f"Warning: Blank amount for {series_code} {month}, skipping")
        continue
    
    selected.append({
        'series_code': series_code,
        'month': month,
        'amount': amount
    })

df_selected = pd.DataFrame(selected)
```

## Handling Blank Values

When the selected observation has a blank or NaN amount:
1. **Do not** treat as zero (would bias the average)
2. **Do not** fall back to another source/version (selector is explicit)
3. **Do** skip the observation and average only valid months

```python
# Annualize: average only valid months
valid_months = df_selected[df_selected['amount'].notna()]
annual_value = valid_months['amount'].mean()
```

## Difference from Priority-Based Deduplication

| Pattern | When to use | Selection logic |
|---------|-------------|----------------|
| Priority deduplication | Multiple sources with known quality hierarchy | Keep record with smallest priority value |
| Selector workbook | Explicit per-observation selection specified in a file | Use the source/version specified in selector |

Priority deduplication is rule-based (always prefer lower priority). Selector workbook is explicit (each observation has a designated source).

## Verification

After selection, verify:
1. All expected (series, period) combinations have a selected value (or were intentionally skipped due to blanks)
2. No duplicate selections for the same (series, period)
3. The count of valid observations matches expectations (e.g., 8 months expected, 7 valid after skipping blanks)

```python
# Check for expected observations
expected = set(selector['series_code'] + '_' + selector['month'])
actual = set(df_selected['series_code'] + '_' + df_selected['month'])
missing = expected - actual
if missing:
    print(f"Missing observations: {missing}")
```
