---
name: dataset-diff
description: Compare two versions of a structured dataset across formats (PDF, Excel, CSV, JSON) to detect added, removed, and modified records with field-level changes. Use when comparing archived vs current data, reconciling cross-format datasets, or generating change reports.
---

# Dataset Diff

Compare structured datasets across file formats to produce a machine-readable diff.

## Pre-requisites

If working in externally-managed Python environments (PEP 668):
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

### From JSON
```python
df = pd.read_json('/path/to/data.json')
```

## Comparison Workflow

1. **Normalize**: Strip whitespace from column names and values
2. **Index**: Set primary key column (e.g., `ID`) as index on both DataFrames
3. **Identify Retired**: `df_old.index.difference(df_new.index)`
4. **Identify New**: `df_new.index.difference(df_old.index)` (if tracking additions)
5. **Compare Fields**: For shared IDs, compare column-by-column with type awareness

```python
changes = []
for idx in df_old.index.intersection(df_new.index):
    for col in df_old.columns:
        old_val = df_old.loc[idx, col]
        new_val = df_new.loc[idx, col]
        # Convert to numeric for comparison if possible, but preserve original for output
        try:
            old_num = float(old_val)
            new_num = float(new_val)
            if old_num != new_num:
                changes.append({
                    "id": idx, "field": col,
                    "old_value": old_num, "new_value": new_num
                })
        except (ValueError, TypeError):
            if str(old_val).strip() != str(new_val).strip():
                changes.append({
                    "id": idx, "field": col,
                    "old_value": old_val, "new_value": new_val
                })
```

## Output Format

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
- Sort arrays by ID for deterministic output
- Strip whitespace from string values before comparison

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Validation Checklist

- [ ] Retired + modified + unchanged = total original records
- [ ] Numeric fields are JSON numbers (not quoted strings)
- [ ] Output arrays sorted by ID
- [ ] Spot-check 2-3 changes manually against source files

## Known invariants (by sub-task)

(No sub-task-specific invariants recorded yet for R0. Update this section when verifier failures reveal task-specific requirements.)

## Scripts

- `scripts/compute_diff.py` — Deterministic diff script taking two JSON files and a key column. Usage: `python scripts/compute_diff.py old.json new.json --key ID`

## References

- `references/diff_schema.md` — Full JSON schema for diff output format

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `in2csv` fails on PDF | Missing Java deps or text-based PDF | Use `pdfplumber` instead |
| `pip install` fails with "externally managed" | PEP 668 restriction | Add `--break-system-packages` or use venv |
| Column mismatch after extraction | Hidden whitespace | `df.columns = df.columns.str.strip()` |
| False positives in comparison | Mixed types ("4.09" vs 4.09) | Normalize to numeric before comparing |
| Empty table extraction | Multi-page tables or images | Iterate all pages: `for page in pdf.pages:` |
