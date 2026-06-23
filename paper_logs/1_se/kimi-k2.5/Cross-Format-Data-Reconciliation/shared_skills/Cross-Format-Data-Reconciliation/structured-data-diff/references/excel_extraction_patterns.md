# Excel Extraction Patterns

Common patterns for extracting structured data from Excel files using pandas.

## Basic Extraction

```python
import pandas as pd
import json

# Read Excel file
df = pd.read_excel('data.xlsx')

# Preserve types by converting through JSON
records = json.loads(df.to_json(orient='records'))

# Write to JSON for diff script
with open('data.json', 'w') as f:
    json.dump(records, f, indent=2)
```

## Handling Specific Sheets

```python
# Read specific sheet by name
df = pd.read_excel('data.xlsx', sheet_name='Sheet1')

# Read by index
df = pd.read_excel('data.xlsx', sheet_name=0)

# Read all sheets
sheets = pd.read_excel('data.xlsx', sheet_name=None)  # Returns dict of sheet_name: DataFrame
```

## Type Preservation

Pandas often converts integers to floats when NaN values are present. Preserve types:

```python
import pandas as pd
import json

df = pd.read_excel('data.xlsx')

# Method 1: Convert through JSON (recommended)
records = json.loads(df.to_json(orient='records'))

# Method 2: Use nullable Int64 dtype for integer columns
df['ID'] = df['ID'].astype('Int64')
df['StockUnits'] = df['StockUnits'].astype('Int64')

# Method 3: Post-process to clean floats
for record in records:
    for key, val in record.items():
        if isinstance(val, float) and val == int(val):
            record[key] = int(val)
```

## Header Handling

```python
# Skip rows before header
df = pd.read_excel('data.xlsx', header=2)  # Header is on row 3 (0-indexed)

# No header - assign column names
df = pd.read_excel('data.xlsx', header=None, names=['ID', 'Name', 'Value'])

# Multi-level headers
df = pd.read_excel('data.xlsx', header=[0, 1])
```

## Common Issues

| Issue | Solution |
|-------|----------|
| `Read` tool fails on .xlsx | Use `pd.read_excel()` - the Read tool cannot handle binary Excel files |
| Integers become floats | Use `json.loads(df.to_json())` or `astype('Int64')` |
| Dates parsed incorrectly | Use `parse_dates=['date_col']` or `dtype={'date_col': str}` |
| Empty cells as NaN | Pandas default; use `fillna('')` or `dropna()` as needed |
| Column names with spaces | Access via `df['Column Name']` or rename: `df.columns = df.columns.str.strip()` |

## Container Manifest Example

```python
import pandas as pd
import json

# Extract from Excel current state
df = pd.read_excel('container_manifest_current.xlsx')

# Preserve types through JSON conversion
records = json.loads(df.to_json(orient='records'))

# Ensure ID field exists and is string
for record in records:
    record['ID'] = str(record['ID'])

with open('current.json', 'w') as f:
    json.dump(records, f, indent=2)
```
