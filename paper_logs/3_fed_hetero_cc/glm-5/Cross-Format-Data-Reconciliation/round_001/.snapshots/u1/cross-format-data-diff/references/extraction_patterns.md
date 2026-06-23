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

## JSON Serialization for Numpy Types

```python
import json
import numpy as np
import pandas as pd

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if pd.isna(obj):
            return None
        return super().default(obj)

json.dump(data, f, cls=NumpyEncoder, indent=2)
```
