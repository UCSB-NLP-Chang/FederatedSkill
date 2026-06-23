---
name: dataset-diff
description: Compare two versions of a structured dataset across formats (PDF, Excel, CSV, JSON) to detect added, removed, and modified records with field-level changes. Use when comparing archived vs current data, reconciling cross-format datasets, or generating change reports.
---

# Dataset Diff

Compare structured datasets across file formats to produce a machine-readable diff.

## Quick Start: End-to-End Workflow

```python
import pdfplumber
import pandas as pd
import json

# 1. Extract from PDF (archive/baseline)
with pdfplumber.open('archive.pdf') as pdf:
    table = pdf.pages[0].extract_tables()[0]
    df_old = pd.DataFrame(table[1:], columns=table[0])

# 2. Extract from Excel/CSV (current)
df_new = pd.read_excel('current.xlsx')

# 3. Normalize column names
df_old.columns = df_old.columns.str.strip()
df_new.columns = df_new.columns.str.strip()

# 4. Convert to JSON for diff script
df_old.to_json('old.json', orient='records')
df_new.to_json('new.json', orient='records')

# 5. Run diff (or compare manually in Python)
# python scripts/compute_diff.py old.json new.json --key ID
```

## Pre-requisites

- Always use `python3` (not `python`) for execution.
- If `pip install` fails with "externally managed", use `pip install --break-system-packages <package>`.

```bash
pip install --break-system-packages pdfplumber pandas openpyxl
```

## Extraction

### From PDF (Archive/Baseline)
**Use `pdfplumber`**, not `csvkit in2csv` or `pdftotext`.

```python
import pdfplumber
import pandas as pd

with pdfplumber.open('/path/to/archive.pdf') as pdf:
    page = pdf.pages[0]
    table = page.extract_tables()[0]  # Assumes first table on first page
    df_old = pd.DataFrame(table[1:], columns=table[0])
```

**Anti-pattern**: `csvkit in2csv` requires Java dependencies for PDFs and typically fails with "direct conversion failed" or extracts unstructured text.

### From Excel/CSV
```python
df_new = pd.read_excel('/path/to/current.xlsx')
# or
df_new = pd.read_csv('/path/to/current.csv')
```

For Excel, `pandas` (`pd.read_excel`) is preferred for bulk operations. `openpyxl` is a valid lightweight alternative when you need direct cell access or pandas is unavailable.

### From JSON
```python
df = pd.read_json('/path/to/data.json')
```

## Pre-comparison Validation

Before comparing, verify extraction succeeded:

```python
print(f"PDF shape: {df_old.shape}, Columns: {list(df_old.columns)}")
print(f"Excel shape: {df_new.shape}, Columns: {list(df_new.columns)}")
print(df_old.head(2))
print(df_new.head(2))
```

**Decision rule**: If shapes are unexpected (0 rows, wrong column count), check for multi-page tables or extraction failures before proceeding.

## PDF Row Validation

PDF extraction often returns header rows on every page, footers, or noise rows. Filter extracted rows using a regex pattern matched against the primary key column:

```python
import re

# Example: filter rows where ID matches pattern like SVR0001, SVR0125
valid_rows = []
for row in extracted_rows:
    if row and row[0] and re.match(r'^[A-Z]+\d{4}$', row[0]):  # Adjust pattern to your ID format
        valid_rows.append(row)
```

This prevents duplicate headers or footer text from polluting your dataset.

## Type Handling

When comparing numeric fields from different sources:
- **Excel/CSV**: Pandas reads as `int64` or `float64`
- **PDF**: Extracts as strings (e.g., `"9284"`)

**Comparison rule**: Normalize to float for accurate comparison (handles `"4.09" == 4.09`).
**Output rule**: Convert float whole numbers back to integers to avoid `9284.0` in JSON output.

```python
def format_output(val):
    """Convert float whole numbers to int for clean JSON output."""
    if isinstance(val, float) and val.is_integer():
        return int(val)
    return val

# When recording changes, apply to normalized values:
old_norm = float(old_val) if not pd.isna(old_val) else old_val
new_norm = float(new_val) if not pd.isna(new_val) else new_val

if old_norm != new_norm:
    changes.append({
        "id": idx, "field": col,
        "old_value": format_output(old_norm),
        "new_value": format_output(new_norm)
    })
```

**JSON serialization**: Pandas values are numpy types (`np.int64`, `np.float64`) which are not JSON serializable. Always convert to native Python types before `json.dump()`:

```python
def to_python(val):
    """Convert numpy types to native Python types for JSON serialization."""
    if hasattr(val, 'item'):  # numpy scalar
        return val.item()
    if isinstance(val, float) and val.is_integer():
        return int(val)
    return val

# Apply before json.dump()
result = {"changes": [{k: to_python(v) for k, v in rec.items()} for rec in changes]}
json.dump(result, f)
```

## Output Format

**Critical**: Check task requirements for exact output key names. If the task description mentions specific terminology (e.g., "decommissioned servers", "retired assets"), use those exact strings as JSON keys.

Produce deterministic, sorted JSON with typed values:
```json
{
  "removed_ids": ["ID001", "ID002"],
  "added_ids": ["ID005"],
  "changed_records": [
    {"id": "ID003", "field": "Spend", "old_value": 10128, "new_value": 10360},
    {"id": "ID004", "field": "Owner", "old_value": "Old Team", "new_value": "New Team"}
  ]
}
```

Rules:
- Store numeric fields as JSON numbers, not strings
- Store integer values as JSON integers without `.0` (e.g., `10128` not `10128.0`)
- Sort arrays by ID for deterministic output
- Strip whitespace from string values before comparison

**Field name adaptation**: Map domain terminology to standard structure while keeping value types consistent. See `references/domain_mapping.md` for common mappings. Use `--removed-key` / `--changed-key` flags in `compute_diff.py` for automatic mapping.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Pre-Output Verification Checklist

Before writing final output:
- [ ] **Keys match requirements**: Search task description for expected output field names (e.g., "decommissioned", "retired", "dropped", "updated"). If found, use those exact keys instead of defaults. **Check `references/domain_mapping.md` first**.
- [ ] **Data accuracy**: Retired + modified + unchanged = total original records
- [ ] **Type correctness**: Numeric fields are JSON numbers (not quoted strings)
- [ ] **Integer formatting**: Integer values do not have `.0` suffix in JSON output
- [ ] **Determinism**: Output arrays sorted by ID
- [ ] **Spot-check**: Verify 2-3 changes manually against source files

## Anti-Patterns

- Do not manually compare large tables row-by-row; use `scripts/compute_diff.py`.
- Do not assume identical column names across files; map them explicitly before diffing.
- Avoid writing custom type-conversion logic for diffing; the script's `normalize()` and `format_output()` functions safely handle string-vs-number mismatches.
- **Do not re-implement comparison logic** when transforming output formats. Run `compute_diff.py` first, then rename/reshape its JSON output to match task requirements.
- Do not manually normalize types before saving JSON; save raw extracted data and let the script's `normalize()` handle it.

## Known invariants (by sub-task)

### portfolio-comparison
- Output arrays must be sorted by ID for deterministic output.
- Numeric fields must be JSON numbers, not quoted strings.
- Integer values should not have `.0` suffix in output.

## Scripts

**Use `compute_diff.py` when**: Both datasets are already in JSON format and you want standardized diff output.

**Write inline code when**: Extracting from PDF/Excel directly, or for simpler one-off comparisons.

- `scripts/compute_diff.py` — Deterministic diff script taking two JSON files and a key column. Supports custom output field names for domain terminology.

Usage:
```bash
# Standard keys (removed_ids, added_ids, changed_records)
python scripts/compute_diff.py old.json new.json --key ID

# Domain-specific keys (e.g., retail categories)
python scripts/compute_diff.py old.json new.json --key ID \
  --removed-key dropped_categories \
  --changed-key adjusted_categories \
  --omit-empty
```

## References

- `references/diff_schema.md` — Full JSON schema for diff output format
- `references/domain_mapping.md` — Common terminology mappings (departments/categories/schools/assets/hardware). **Check this first when task uses domain-specific language.**
- `references/pdf_excel_workflow.md` — Complete working pattern for PDF archive vs Excel/CSV current comparisons

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `python: command not found` | `python` symlink missing | Use `python3` instead |
| `in2csv` fails on PDF | Missing Java deps or text-based PDF | Use `pdfplumber` instead |
| `pip install` fails with "externally managed" | PEP 668 restriction | Add `--break-system-packages` or use venv |
| Column mismatch after extraction | Hidden whitespace | `df.columns = df.columns.str.strip()` |
| False positives in comparison | Mixed types ("4.09" vs 4.09) | Normalize to numeric before comparing |
| Empty table extraction | Multi-page tables or images | Iterate all pages: `for page in pdf.pages:` |
| `9284.0` instead of `9284` in output | Float normalization without integer check | Use `format_output()` pattern or check `val.is_integer()` |
| `TypeError: Object of type int64/float64 is not JSON serializable` | Pandas uses numpy types | Use `to_python()` or `.item()` to convert numpy scalars |
| Duplicate header rows in extracted data | PDFs repeat headers on each page | Use regex validation pattern to filter only valid data rows |
| Verifier fails despite correct data | Wrong output key names | Check task requirements for specific field names (e.g., "decommissioned_servers" vs "removed_ids"). See `references/domain_mapping.md` |