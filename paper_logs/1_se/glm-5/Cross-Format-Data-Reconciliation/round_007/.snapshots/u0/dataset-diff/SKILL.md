---
name: dataset-diff
description: Compare structured datasets across different file formats (Excel, PDF, CSV, JSON) and generate a diff output. Use when tasks require identifying added, removed, or changed records between two data sources. Use the bundled script as the primary approach for standard comparisons.
---

# Dataset Diff

Compare two datasets from different file formats and produce a structured diff.

## Quick Decision Tree

1. **Both files accessible on disk?** → Run the CLI script directly:
   ```bash
   python3 scripts/diff_datasets.py old_file.xlsx new_file.pdf --key ID -o diff_report.json
   ```

2. **PDF content from Read tool (base64)?** → Use script as a Python module:
   ```python
   from scripts.diff_datasets import load_pdf_from_base64, load_excel, diff_datasets
   old_records = load_pdf_from_base64(base64_content)
   new_records = load_excel('/path/to/file.xlsx')
   result = diff_datasets(old_records, new_records, key_field='ID')
   ```

3. **Need custom output keys?** → Run script, then post-process the result dict.

4. **Non-tabular PDF or special parsing?** → Custom parsing may be needed.

## Workflow

1. **Identify source formats** - Check file extensions to determine read method
2. **Extract data to common format** - Convert both sources to Python dicts/lists
3. **Compare by primary key** - Use a unique identifier field to match records
4. **Generate diff output** - Structure as retired IDs, new IDs, and changed fields

## Using the Script as a Module

For PDFs read via the Read tool (returns base64), import and use the functions:

```python
from scripts.diff_datasets import load_pdf_from_base64, load_excel, diff_datasets
import json

# Read tool returns base64-encoded PDF content
old_records = load_pdf_from_base64(base64_content)
new_records = load_excel('/path/to/file.xlsx')

# Compare with custom key field
result = diff_datasets(old_records, new_records, key_field='ServerID')

# Post-process output keys if task requires different names
output = {
    'deleted_medications': result['retired_ids'],
    'modified_medications': result['changed_records']
}
with open('/root/output.json', 'w') as f:
    json.dump(output, f, indent=2)
```

## Output Format

The script produces:
```json
{
  "retired_ids": ["ID1", "ID2"],
  "new_ids": ["ID3"],
  "changed_records": [
    {"id": "ID4", "field": "FieldName", "old_value": "x", "new_value": "y"}
  ]
}
```

Post-process to rename keys if the task requires different names (e.g., `missing_containers` instead of `retired_ids`).

## Reading Different Formats

### Binary Excel (.xlsx)
Do NOT use the Read tool on .xlsx files - it will fail with a binary error.

```python
import pandas as pd
df = pd.read_excel('/path/to/file.xlsx')
records = df.to_dict('records')
```

### PDF Files
The Read tool returns base64-encoded PDF content. Use `load_pdf_from_base64()` from the script:

```python
from scripts.diff_datasets import load_pdf_from_base64
records = load_pdf_from_base64(base64_content)
```

Or manually:
```python
import base64, pdfplumber, io
pdf_bytes = base64.b64decode(base64_content)
pdf = pdfplumber.open(io.BytesIO(pdf_bytes))
tables = []
for page in pdf.pages:
    tables.extend(page.extract_tables() or [])
```

**Troubleshooting:** If you get `ImportError: pdfplumber is required`, install it first:
```bash
pip install pdfplumber
```

### CSV and JSON
These can be read directly with the Read tool or via Python:

```python
import json, pandas as pd
# JSON
with open('/path/to/file.json') as f:
    data = json.load(f)
# CSV
df = pd.read_csv('/path/to/file.csv')
```

## JSON Output from Pandas Data

When writing diff results to JSON after using pandas, numpy types (int64, float64, etc.) are not JSON serializable and will raise `TypeError: Object of type int64 is not JSON serializable`.

**Solution:** Convert values to native Python types before JSON serialization:

```python
import json

# Option 1: Custom JSON encoder
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'item'):
            return obj.item()
        return super().default(obj)

json.dumps(result, cls=NumpyEncoder)

# Option 2: Use pandas to convert DataFrame
df = df.astype(object).where(pd.notnull(df), None)
records = df.to_dict('records')
```

## Anti-Patterns

- **Do not** attempt to read .xlsx files with the Read tool - always use Python/pandas
- **Do not** assume PDFs will yield clean text; they may require table extraction
- **Do not** compare without a primary key; field-by-field comparison without ID matching produces false positives
- **Do not** forget to decode base64 when the Read tool returns PDF content
- **Do not** skip installing pdfplumber before attempting PDF parsing
- **Do not** pass pandas/numpy types directly to `json.dumps()` - convert to native Python types first
- **Do not** write custom parsing code when the bundled script handles your use case - use the script first
- **Do not** assume output format - verify required key names match task specification and post-process if needed