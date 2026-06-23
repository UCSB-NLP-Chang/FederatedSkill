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

## Internal Spaces in SKU Codes

**Symptom**: SKUs appear identical but don't match between PDF catalog and Excel inventory (e.g., "ABC 123" vs "ABC123").

**Diagnosis**: Check raw values:
```python
print(repr(df['SKU'].iloc[0]))  # Shows spaces explicitly
```

**Fix**: Remove internal spaces only if confirmed as formatting inconsistency:
```python
df['SKU'] = df['SKU'].str.replace(' ', '')
```
**Caution**: Only do this if join fails. Some SKU formats legitimately contain spaces.

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

## Test File Not Found Initially

**Symptom**: `ls test*.py` returns nothing at start of task.

**Cause**: Test files may be created dynamically, placed in subdirectories, or named non-standardly.

**Fix**: 
1. Search recursively: `find . -name "*test*.py"`
2. Check after generating output (some verifiers create tests post-hoc)
3. Run pytest discovery: `pytest --collect-only`
4. Look for hidden files: `ls -la`

**Rule**: Even if no test files are visible initially, always attempt `pytest -v` after generating output.

## Self-Validation Passes But Tests Fail

**Symptom**: Manual checks look correct but test suite fails.

**Cause**: Tests have specific expectations about output format, file path, column names, or sheet names.

**Fix**: Run the actual test suite if provided (e.g., `pytest test_output.py`). Check test file for exact expected values.

**Critical**: Do not rely on manual verification. Only pytest passing counts as success.

## Value Tier Classification Errors

**Symptom**: `VALUE_TIER` column produces wrong categories (low/medium/high).

**Cause**: Boundary conditions or threshold logic inverted.

**Fix**: Use explicit bins:
```python
# Wrong: chained conditionals
df['TIER'] = 'low'
df.loc[df['VALUE'] > 5000, 'TIER'] = 'medium'
df.loc[df['VALUE'] > 20000, 'TIER'] = 'high'

# Correct: ensure boundaries
conditions = [
    df['VALUE'] < 5000,
    (df['VALUE'] >= 5000) & (df['VALUE'] < 20000),
    df['VALUE'] >= 20000
]
choices = ['low', 'medium', 'high']
df['TIER'] = np.select(conditions, choices)
```
