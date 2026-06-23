# PDF Text Parsing Patterns

Patterns for extracting structured data from PDFs where the data is embedded as formatted text rather than extractable tables.

## When to Use This Instead of Table Extraction

Use text parsing when:
- `page.extract_tables()` returns empty or malformed results
- The PDF displays data in a structured list/format but not as a table object
- Data appears as labeled fields (e.g., "ID: CRS0001, Course: Applied Statistics 101")

## Basic Pattern: Labeled Field Extraction

```python
import pdfplumber
import re
import json

with pdfplumber.open('document.pdf') as pdf:
    text = "\n".join(page.extract_text() for page in pdf.pages)

# Pattern for labeled fields: "ID: VALUE, Field: VALUE, ..."
pattern = r'ID:\s*(\S+)\s*,\s*Course:\s*([^,]+)\s*,\s*Department:\s*([^,]+)\s*,\s*Credits:\s*(\d+)\s*,\s*Instructor:\s*([^\n]+)'

records = []
for match in re.finditer(pattern, text):
    records.append({
        'ID': match.group(1).strip(),
        'Course': match.group(2).strip(),
        'Department': match.group(3).strip(),
        'Credits': int(match.group(4)),
        'Instructor': match.group(5).strip()
    })
```

## Pattern: Structured List with Headers

```python
import pdfplumber
import re
import json

with pdfplumber.open('document.pdf') as pdf:
    text = "\n".join(page.extract_text() for page in pdf.pages)

# Find section between headers
# Example: data between "Course Catalog 2024" and "End of Catalog"
section_match = re.search(r'Course Catalog 2024\s*\n(.*?)(?:End of Catalog|Page \d+ of \d+)', text, re.DOTALL)
if section_match:
    section = section_match.group(1)
    
    # Parse individual records - adjust pattern to match your format
    # This example matches: "CRS0001 - Applied Statistics 101 (Mathematics, 3 credits, Dr. Malik)"
    record_pattern = r'(\w+)\s*-\s*([^\(]+)\s*\(([^,]+),\s*(\d+)\s*credits?,\s*([^\)]+)\)'
    
    records = []
    for match in re.finditer(record_pattern, section):
        records.append({
            'ID': match.group(1).strip(),
            'Course': match.group(2).strip(),
            'Department': match.group(3).strip(),
            'Credits': int(match.group(4)),
            'Instructor': match.group(5).strip()
        })
```

## Pattern: Tabular Text Layout

```python
import pdfplumber
import re
import json

with pdfplumber.open('document.pdf') as pdf:
    text = "\n".join(page.extract_text() for page in pdf.pages)

# Split into lines and parse fixed-width or delimited format
lines = text.split('\n')

# Skip header lines until data starts
records = []
for line in lines:
    # Skip empty lines and headers
    if not line.strip() or 'ID' in line and 'Course' in line:
        continue
    
    # Try to parse as: ID  Course  Department  Credits  Instructor
    # Use split with multiple spaces or specific positions
    parts = re.split(r'\s{2,}', line.strip())  # Split on 2+ spaces
    if len(parts) >= 5:
        records.append({
            'ID': parts[0].strip(),
            'Course': parts[1].strip(),
            'Department': parts[2].strip(),
            'Credits': int(parts[3]) if parts[3].isdigit() else parts[3],
            'Instructor': parts[4].strip()
        })
```

## Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| Regex too rigid for slight format variations | Use more flexible patterns with `\s*` for whitespace, `[^,]+` for field values |
| Multi-line records | Use `re.DOTALL` flag and match across newlines, or parse line-by-line with state machine |
| Inconsistent field ordering | Extract all key-value pairs first, then normalize to standard schema |
| IDs with varying formats (CRS0001 vs CRS-0001) | Normalize: `id.replace('-', '')` before comparison |
| Numeric values extracted as strings | Explicit conversion: `int(val) if val.isdigit() else val` |
| Missing optional fields | Use `.get()` with defaults: `record.get('Credits', 0)` |

## Validation Steps

After text extraction, always verify:

```python
# Check record count is reasonable
print(f"Extracted {len(records)} records")

# Verify all records have required ID field
missing_ids = [r for r in records if not r.get('ID')]
if missing_ids:
    print(f"Warning: {len(missing_ids)} records missing ID")

# Check for duplicate IDs
from collections import Counter
id_counts = Counter(r['ID'] for r in records)
duplicates = {id_: count for id_, count in id_counts.items() if count > 1}
if duplicates:
    print(f"Warning: Duplicate IDs found: {duplicates}")

# Sample output for manual verification
print("Sample records:")
for r in records[:3]:
    print(r)
```

## Course Catalog Example

```python
import pdfplumber
import re
import json

# Extract from PDF archive (2024 catalog)
with pdfplumber.open('course_catalog_2024.pdf') as pdf:
    text = "\n".join(page.extract_text() for page in pdf.pages)

# Parse structured text format: "ID: CRS0001, Course: Applied Statistics 101, ..."
pattern = r'ID:\s*(CRS\d+)\s*,\s*Course:\s*([^,]+?)\s*,\s*Department:\s*([^,]+?)\s*,\s*Credits:\s*(\d+)\s*,\s*Instructor:\s*([^\n]+)'

archive_records = []
for match in re.finditer(pattern, text):
    archive_records.append({
        'ID': match.group(1),
        'Course': match.group(2).strip(),
        'Department': match.group(3).strip(),
        'Credits': int(match.group(4)),
        'Instructor': match.group(5).strip()
    })

# Save for comparison
with open('archive.json', 'w') as f:
    json.dump(archive_records, f, indent=2)
```
