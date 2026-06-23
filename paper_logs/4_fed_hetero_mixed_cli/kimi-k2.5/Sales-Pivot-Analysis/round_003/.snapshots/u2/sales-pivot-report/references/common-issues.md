# Common Issues in PDF-Excel Integration

## ImportError: cannot import name 'PivotChart'

**Symptom**: Script fails with `ImportError: cannot import name 'PivotChart' from 'openpyxl.chart'`.

**Cause**: openpyxl does not expose a PivotChart class. This is a common misconception.

**Fix**: Remove the import. Use pandas for pivot tables:
```python
# Wrong
from openpyxl.chart import PivotChart

# Correct
pivot = pd.pivot_table(
    df, 
    values='REVENUE', 
    index='CATEGORY', 
    aggfunc='sum'
)
pivot.to_excel(writer, sheet_name='Revenue by Category')
```

## ValueError: Cannot convert tuple to Excel

**Symptom**: `openpyxl` raises `ValueError: Cannot convert ('A', 'B') to Excel` when writing pivot table.

**Cause**: DataFrame has MultiIndex columns from `pd.pivot_table()`.

**Fix**: Flatten columns before writing:
```python
if isinstance(df.columns, pd.MultiIndex):
    df.columns = [c[-1] if isinstance(c, tuple) else str(c) for c in df.columns]
```

## Whitespace in Join Keys

**Symptom**: Merge operations return fewer rows than expected or produce NaN values in joined columns.

**Diagnosis**: Check for hidden whitespace:
```python
print(df['REGION'].unique())  # Look for 'North ' vs 'North'
```

**Fix**: Strip all string columns before merging:
```python
for col in df.select_dtypes(include=['object']).columns:
    df[col] = df[col].str.strip()
```

## PDF Table Extraction Returns None

**Symptom**: `page.extract_table()` returns None despite visible tables.

**Fix**: Try explicit table detection settings:
```python
table = page.extract_table({
    "vertical_strategy": "lines", 
    "horizontal_strategy": "lines"
})
# Or for text-based tables without lines:
table = page.extract_table({
    "vertical_strategy": "text",
    "horizontal_strategy": "text"
})
```

If extraction still fails, fall back to text parsing:
```python
text = page.extract_text()
lines = [line.split() for line in text.split('\n') if line.strip()]
```

## Data Type Mismatches in Joins

**Symptom**: Merge on ID columns produces no matches despite visible matches in data preview.

**Cause**: One source has IDs as strings ("1001"), another as integers (1001), or float vs int.

**Fix**: Explicitly cast join keys:
```python
df1['PRODUCT_ID'] = df1['PRODUCT_ID'].astype(int)
df2['PRODUCT_ID'] = df2['PRODUCT_ID'].astype(int)
```

## Case Sensitivity in Categoricals

**Symptom**: Pivot tables show duplicate categories (e.g., "North" and "north" as separate rows).

**Fix**: Normalize case before aggregation:
```python
df['REGION'] = df['REGION'].str.title()  # north -> North
```

## Self-Validation Passes But Tests Fail

**Symptom**: Manual checks look correct but test suite fails.

**Cause**: Tests have specific expectations about output format, file path, column names, or sheet names.

**Fix**: Run the actual test suite if provided (e.g., `pytest test_output.py`). Check test file for exact expected values.
