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

Use `pdfplumber` for structured table extraction. Do not use Read tool on PDFs containing tables:

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

### Multi-Page PDF Tables

For PDFs with tables spanning multiple pages, iterate over all pages and filter header row artifacts:

```python
import pdfplumber
import pandas as pd

with pdfplumber.open('/path/to/file.pdf') as pdf:
    all_rows = []
    headers = None
    for page in pdf.pages:
        table = page.extract_table()
        if table:
            if headers is None:
                headers = table[0]  # Capture headers from first page
            # Skip header rows that appear mid-data (common in multi-page PDFs)
            for row in table:
                if row[0] != headers[0]:  # Compare first column to header
                    all_rows.append(dict(zip(headers, row)))
    
    df = pd.DataFrame(all_rows)
    print(f"Extracted {len(df)} rows from {len(pdf.pages)} pages")
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

## Cross-Source Type Normalization

When comparing **PDF against Excel/CSV**, note that PDF tables extract as strings while Excel preserves native types:

```python
def normalize_for_comparison(value):
    """Convert string numbers to native types for accurate diff.
    
    PDF extraction returns: '123', '45.67', 'Text'
    Excel extraction returns: 123, 45.67, 'Text'
    Normalize both to native types before comparison.
    """
    if isinstance(value, str):
        val = value.strip()
        # Try integer first
        try:
            return int(val)
        except ValueError:
            # Then float
            try:
                return float(val)
            except ValueError:
                return val
    return value

# Normalize entire dataset before comparison
normalized_data = []
for record in original_data:
    normalized_record = {k: normalize_for_comparison(v) for k, v in record.items()}
    normalized_data.append(normalized_record)
```

## Data Type Handling

When comparing values, normalize types to avoid false positives:
- Convert numeric strings to floats/integers before comparison (critical for PDF vs Excel)
- Strip whitespace from string values
- Handle null representations consistently (None, NaN, empty string)

## JSON Serialization

Pandas DataFrames use numpy scalar types (int64, float64) which are not JSON serializable. Convert before writing to JSON:

```python
import numpy as np
import pandas as pd

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