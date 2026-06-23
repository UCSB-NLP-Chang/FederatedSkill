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

If tables are not detected automatically, check `page.extract_text()` to verify content is text-based, not scanned images.

**Important**: PDF extraction returns all values as strings. You must convert numeric fields explicitly:
```python
for row in data:
    row['Spend2024K'] = float(row['Spend2024K']) if row['Spend2024K'] else None
    row['FiveYearCAGR'] = float(row['FiveYearCAGR']) if row['FiveYearCAGR'] else None
```

**Validate extracted IDs**: Multi-page PDF extraction often captures header rows as data rows, introducing invalid IDs (e.g., literal "ID" string). Always filter IDs against the expected pattern:
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

**Type mismatch between formats**: PDFs return all values as strings; Excel/CSV preserve types. Always normalize before comparing:
```python
# PDF gives: {'Spend2024K': '10972', 'CAGR': '4.09'}
# Excel gives: {'Spend2024K': 10972, 'CAGR': 4.09}
# Convert PDF strings to match Excel types before comparison
```

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

## Combined In-Memory Diff Template
Use this when the task requires custom output keys or specific comparison logic. Run as a single script to avoid intermediate file errors and state-sync issues.

```python
import pdfplumber, pandas as pd, json, re

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if pd.isna(obj): return None
        if hasattr(obj, 'item'): return obj.item()
        return super().default(obj)

def extract_pdf(path):
    rows = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table and len(table) > 1:
                headers = [h.strip().lower() for h in table[0]]
                for row in table[1:]:
                    if row[0] and row[0].strip() != headers[0]:
                        rows.append({h: v for h, v in zip(headers, row)})
    return rows

def safe_equal(a, b):
    try: return float(a) == float(b)
    except: return str(a).strip() == str(b).strip()

# 1. Load
pdf_data = extract_pdf('old.pdf')
df_new = pd.read_excel('new.xlsx')
df_new.columns = df_new.columns.str.strip().str.lower()

# 2. Index
id_col = 'id'
old_ids = {r[id_col].strip() for r in pdf_data if id_col in r}
new_ids = set(df_new[id_col].astype(str).str.strip())

# 3. Compare
removed = sorted(old_ids - new_ids)
added = sorted(new_ids - old_ids)
revised = []
for r in pdf_data:
    rid = r.get(id_col, '').strip()
    if rid in new_ids:
        new_row = df_new[df_new[id_col].astype(str).str.strip() == rid].iloc[0]
        for k, v in r.items():
            if k in new_row.index and not safe_equal(v, new_row[k]):
                revised.append({"id": rid, "field": k, "old_value": v, "new_value": new_row[k]})

# 4. Output with task-specific keys
result = {"removed_courses": removed, "revised_courses": revised}
with open('diff.json', 'w') as f:
    json.dump(result, f, indent=2, cls=NumpyEncoder)
```