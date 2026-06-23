# Excel Data Extraction Patterns for Capacity Planning

Common input layouts for production planning Excel files and how to read them.

## Pattern 1: Column-Based Weeks (Standard)

**Layout**: Each row is a period, columns are week/demand pairs.

```
| Week | Demand | Week | Demand | ...
|    4 |   100  |    5 |    80  | ...
```

**Read with**:
```python
import pandas as pd
df = pd.read_excel('input.xlsx', sheet_name='Data')
weeks = df.iloc[:, 0::2].values.flatten()  # Even columns
demands = df.iloc[:, 1::2].values.flatten()  # Odd columns
```

## Pattern 2: Row-Based Labels (Transposed)

**Layout**: Column 0 has labels, columns 1-N contain week data.

```
| Label          | 4    | 5    | 6    | ... (week numbers in row 2)
| Some Data      | ...  | ...  | ...  |
| MIG Demand     | 100  |  80  | 120  | ... (row 9)
```

**Read with**:
```python
import pandas as pd
df = pd.read_excel('input.xlsx', sheet_name='Weld')

# Extract week numbers from row 2 (index 2), columns 1-49
weeks = []
demands = []
for col_idx in range(1, 50):  # Columns 1-49 for weeks 4-52
    week_val = df.iloc[2, col_idx]      # Row with week numbers
    demand_val = df.iloc[9, col_idx]    # Row with demand data
    if pd.notna(week_val):
        try:
            week_num = int(float(week_val))
            weeks.append(week_num)
            demands.append(float(demand_val) if pd.notna(demand_val) else 0.0)
        except (ValueError, TypeError):
            pass

demand_by_week = dict(zip(weeks, demands))
```

**Key indices to check**:
- Row 2 (index 2): Week numbers
- Row 9 (index 9): MIG Weld Demand Total (common label)
- Verify by printing `df.iloc[:, 0]` to see row labels

## Pattern 3: Structured Table

**Layout**: Clean table with named columns.

```
| Week | Demand | Capacity | ...
|    4 |    100 |      120 | ...
```

**Read with**:
```python
df = pd.read_excel('input.xlsx')
weeks = df['Week'].tolist()
demands = df['Demand'].tolist()
```

## Pattern 4: Duplicate Periods in Input

**Layout**: Same period/phase appears multiple times with different demand values.

```
| Phase | Demand | Priority |
|    10 |   71.72 | PRIORITY_10 |
|    10 |  120.00 | PRIORITY_10 |
|    18 |   63.58 | PRIORITY_18 |
|    18 |   95.00 | PRIORITY_18 |
```

**Handle with**:
```python
import pandas as pd
df = pd.read_excel('input.xlsx', sheet_name='Assembly')

# Check for duplicate periods
duplicates = df[df.duplicated(subset=['Phase'], keep=False)]
if not duplicates.empty:
    print(f"Duplicate phases found: {duplicates['Phase'].unique().tolist()}")
    # Aggregate by summing demands
    df = df.groupby('Phase', as_index=False).agg({
        'Demand': 'sum'
        # Preserve other columns as needed
    })
```

**Why this happens**: Multiple work orders or line items for the same production period.

## Detection Strategy

When encountering an unknown Excel layout:

1. **First**: Try `pd.read_excel()` and inspect `df.head()` and `df.shape`
2. **If wide and short** (many columns, few rows): Likely Pattern 2 (row-based)
3. **If narrow and long** (few columns, many rows): Likely Pattern 1 or 3
4. **Inspect column 0**: If it contains string labels like "Week", "Demand", "MIG Weld", it's Pattern 2
5. **Check row 2**: If it contains week numbers (4, 5, 6...), confirm Pattern 2
6. **Check for duplicates**: Run `df.duplicated(subset=['Phase'], keep=False)` to detect Pattern 4

## Common Gotchas

- **Merged cells**: `openpyxl` may return `None` for merged cell values; use `data_only=True` and check for `None`
- **String week numbers**: Cast through `float()` then `int()` to handle "4.0" → 4
- **Total column**: Often column 50 (index 50) contains "Total" - exclude it with `range(1, 50)` not `range(1, 51)`
- **Sheet names**: Common names are "Weld", "Data", "Plan", "Schedule", "Assembly" - check task prompt for exact name
- **Duplicate periods**: Always check for and aggregate duplicate phase/week numbers before processing