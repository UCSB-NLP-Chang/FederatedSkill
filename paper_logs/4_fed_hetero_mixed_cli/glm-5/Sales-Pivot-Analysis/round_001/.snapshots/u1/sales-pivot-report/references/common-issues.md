# Common Issues in Sales Pivot Reports

## ImportError: cannot import name 'PivotChart'

**Symptom**: Script fails with `ImportError: cannot import name 'PivotChart' from 'openpyxl.chart'`.

**Cause**: openpyxl does not expose a PivotChart class. This is a common misconception.

**Fix**: Remove the import. Use pandas for pivot tables:
```python
# WRONG
from openpyxl.chart import PivotChart

# CORRECT
pivot = pd.pivot_table(df, values='REVENUE', index='CATEGORY', aggfunc='sum')
pivot.to_excel(writer, sheet_name='PivotSummary')
```

## ValueError: Cannot convert ('A', 'B') to Excel

**Symptom**: `openpyxl` raises ValueError when writing DataFrame with MultiIndex columns.

**Cause**: openpyxl cannot serialize tuple column names like `('REVENUE', 'North')`.

**Fix**: Flatten MultiIndex before writing:
```python
if isinstance(df.columns, pd.MultiIndex):
    df.columns = [c[-1] if isinstance(c, tuple) else str(c) for c in df.columns]
```

Or use the helper function:
```python
from scripts.build_pivot_report import flatten_columns
df = flatten_columns(df)
```

## Whitespace in Join Keys

**Symptom**: Merge operations return fewer rows than expected or produce NaN values.

**Diagnosis**: Check for hidden whitespace:
```python
print(df['PRODUCT_ID'].unique())  # Look for '1001 ' vs '1001'
```

**Fix**: Strip all string columns before merging:
```python
for col in df.select_dtypes(include=['object']).columns:
    df[col] = df[col].str.strip()
```

## Data Type Mismatches in Joins

**Symptom**: Merge on ID columns produces no matches despite visible matches in data.

**Cause**: One source has IDs as strings ("1001"), another as integers (1001).

**Fix**: Cast join keys explicitly:
```python
df1['PRODUCT_ID'] = df1['PRODUCT_ID'].astype(int)
df2['PRODUCT_ID'] = df2['PRODUCT_ID'].astype(int)
```

## Case Sensitivity in Categoricals

**Symptom**: Pivot tables show duplicate categories ("North" and "north" as separate rows).

**Fix**: Normalize case before aggregation:
```python
df['REGION'] = df['REGION'].str.title()  # north -> North
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

## Self-Validation Passes But Tests Fail

**Symptom**: Manual checks pass but verifier tests report failures.

**Cause**: The verifier has different expectations than what the agent checked.

**Fix**: Always run the actual test suite:
```bash
pytest test_output.py -v
```

Do not rely solely on self-validation (file existence, row counts) - check exact expected values, sheet names, and column order as specified in tests.