# Extraction Patterns by Format

## Excel (.xlsx)

Do not use `Read` tool on binary Excel files. Use pandas:

```python
import pandas as pd
import json

df = pd.read_excel('/path/to/file.xlsx')
data = df.to_dict('records')
print(f"Columns: {list(df.columns)}")
print(f"Records: {len(data)}")
```

For specific sheets: `pd.read_excel('file.xlsx', sheet_name='Sheet1')`

## PDF Tables

Use `pdfplumber` for structured table extraction:

```python
import pdfplumber

with pdfplumber.open('/path/to/file.pdf') as pdf:
    # Extract first table from first page
    tables = pdf.pages[0].extract_tables()
    if tables:
        table = tables[0]
        headers = table[0]
        rows = table[1:]
        data = [dict(zip(headers, row)) for row in rows]
        print(f"Extracted {len(data)} rows with columns: {headers}")
```

If tables are not detected automatically, check `page.extract_text()` to verify content is text-based, not scanned images.

**Important**: PDF extraction returns all values as strings. You must convert numeric fields explicitly:
```python
for row in data:
    row['Spend2024K'] = float(row['Spend2024K']) if row['Spend2024K'] else None
    row['FiveYearCAGR'] = float(row['FiveYearCAGR']) if row['FiveYearCAGR'] else None
```

**Validate extracted IDs**: PDF extraction can capture header rows as data, introducing invalid IDs (e.g., literal "ID" string). Always filter IDs against the expected pattern:
```python
import re

# Filter to valid IDs only
valid_id_pattern = re.compile(r'SVR\d{4}$')  # Adjust pattern to your ID format
valid_ids = [id for id in all_ids if valid_id_pattern.match(str(id))]
```

## CSV

```python
import pandas as pd
df = pd.read_csv('/path/to/file.csv')
data = df.to_dict('records')
```

## JSON

```python
import pandas as pd
df = pd.read_json('/path/to/file.json')
data = df.to_dict('records')
```

## Data Type Handling

When comparing values, normalize types to avoid false positives:
- Convert numeric strings to floats/integers before comparison
- Strip whitespace from string values
- Handle null representations consistently (None, NaN, empty string)

## Safe Comparison Logic

`pdfplumber` extracts all table cells as strings, while `pandas` reads Excel/CSV as native types. Direct `!=` checks will flag unchanged numeric fields as changed. Use this helper:

```python
def safe_equal(a, b):
    """Compare values safely across string/numeric type boundaries."""
    try:
        return float(a) == float(b)
    except (ValueError, TypeError):
        return str(a).strip() == str(b).strip()

# Usage in diff loop:
if not safe_equal(old_val, new_val):
    changes.append(...)
```

## JSON Serialization

Pandas DataFrames use numpy scalar types (int64, float64) which are not JSON serializable. Convert before writing to JSON:

```python
import numpy as np

def convert_for_json(obj):
    """Recursively convert numpy/pandas types to Python native types."""
    if isinstance(obj, dict):
        return {k: convert_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_for_json(item) for item in obj]
    elif isinstance(obj, (np.integer, np.floating, np.bool_)):
        return obj.item()
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif pd.isna(obj):
        return None
    return obj

# Usage:
json.dump(convert_for_json(data), f, indent=2)
```

Or convert individual values inline when building output structures:
```python
old_val = row[field]
if isinstance(old_val, (np.integer, np.floating)):
    old_val = old_val.item()
```
