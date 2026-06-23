---
name: dataset-diff
description: Compare two versions of a structured dataset across formats (PDF, Excel, CSV, JSON) to detect added, removed, and modified records with field-level changes. Use when comparing archived vs current data, reconciling cross-format datasets, generating change reports, or analyzing shipping manifests against archived PDFs.
---

# Dataset Diff

Compare structured datasets across file formats to produce a machine-readable diff.

## BLOCKING RULE: compute_diff.py is MANDATORY

**ALWAYS use `scripts/compute_diff.py` for the diff step. NEVER write inline comparison code.**

This is a hard requirement, not a suggestion. The script handles type normalization, float formatting, and deterministic output. Writing inline comparison code will produce incorrect output.

## Quick Start: Prescriptive Workflow

Follow these steps exactly:

```bash
# 1. Extract data from PDF (see Extraction section for multi-page handling)
python3 extract_pdf.py archive.pdf > old.json
python3 extract_excel.py current.xlsx > new.json

# 2. Verify extraction (see Pre-comparison Validation)
python3 -c "import json; o=json.load(open('old.json')); n=json.load(open('new.json')); print(f'old={len(o)} new={len(n)}')"

# 3. Compute diff using the script (MANDATORY)
python scripts/compute_diff.py old.json new.json --key ID

# 4. If task requires domain-specific keys, use script flags:
python scripts/compute_diff.py old.json new.json --key Medication_ID \
  --removed-key deleted_medications \
  --changed-key modified_medications \
  --added-key new_medications
```

## Extraction

### From PDF (Archive/Baseline)
**Use `pdfplumber`**, not `csvkit in2csv` or `pdftotext`.

```python
import pdfplumber
import pandas as pd
import json
import re

with pdfplumber.open('/path/to/archive.pdf') as pdf:
    all_rows = []
    headers = None
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            if not table:
                continue
            if headers is None:
                headers = table[0]
                data_rows = table[1:]
            else:
                data_rows = table[1:] if table[0] == headers else table

            # Filter valid rows (e.g., IDs matching MED\d{5})
            for row in data_rows:
                if row and row[0] and re.match(r'^[A-Z]+\d{5,}$', str(row[0])):
                    all_rows.append(row)

    df = pd.DataFrame(all_rows, columns=headers)
    df.columns = df.columns.str.strip()
    df.to_json('old.json', orient='records')
```

**Anti-pattern**: `csvkit in2csv` requires Java dependencies for PDFs and typically fails with "direct conversion failed".

### From Excel/CSV
```python
import pandas as pd
df = pd.read_excel('/path/to/current.xlsx')
df.columns = df.columns.str.strip()
df.to_json('new.json', orient='records')
```

## Pre-comparison Validation

Before comparing, verify extraction succeeded:

```python
import json
with open('old.json') as f:
    old = json.load(f)
with open('new.json') as f:
    new = json.load(f)

print(f"Old: {len(old)} records, keys: {list(old[0].keys()) if old else 'EMPTY'}")
print(f"New: {len(new)} records, keys: {list(new[0].keys()) if new else 'EMPTY'}")
print(f"Sample old: {old[0] if old else 'N/A'}")
print(f"Sample new: {new[0] if new else 'N/A'}")
```

**Decision rule**: If record counts are unexpected (0, or magnitude difference without reason), check extraction before diffing.

## Output Format & Key Naming

**Critical**: Check `references/domain_mapping.md` before choosing output keys.

Produce deterministic, sorted JSON with typed values:
```json
{
  "removed_ids": ["ID001", "ID002"],
  "added_ids": ["ID005"],
  "changed_records": [
    {"id": "ID003", "field": "Spend", "old_value": 10128, "new_value": 10360}
  ]
}
```

Rules:
- Store numeric fields as JSON numbers, not strings
- Store integer values as JSON integers without `.0`
- Sort arrays by ID for deterministic output
- Strip whitespace from string values before comparison

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Scripts

**`scripts/compute_diff.py`** — Deterministic diff with custom key support.

Usage:
```bash
# Standard keys
python scripts/compute_diff.py old.json new.json --key ID

# Domain keys (check domain_mapping.md for your industry)
python scripts/compute_diff.py old.json new.json --key ID \
  --removed-key deleted_medications \
  --changed-key modified_medications \
  --omit-empty
```

## References

- `references/diff_schema.md` — Full JSON schema for diff output format
- `references/domain_mapping.md` — **Check this first** for domain-specific terminology (medications, servers, departments, assets, containers, etc.)
- `references/pdf_excel_workflow.md` — Complete extraction pattern for PDF vs Excel comparisons

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `python: command not found` | Missing symlink | Use `python3` |
| `pip install` fails "externally managed" | PEP 668 | Add `--break-system-packages` |
| `TypeError: Object of type int64 not JSON serializable` | Numpy types | Use `.item()` or `int()` before `json.dump()` |
| `9284.0` instead of `9284` in output | Float normalization | Check `val.is_integer()` before converting |
| **Verifier fails despite correct data** | Wrong output key names | Check task description for exact keys. See `references/domain_mapping.md` |
| Duplicate headers in extracted data | PDF repeats headers per page | Use regex validation to filter valid ID patterns |
| Empty table from PDF | Image-based PDF or multi-page layout | Iterate all pages, check `pdf.pages` |

## Pre-Output Verification Checklist

Before finalizing output:
- [ ] **Used compute_diff.py**: Ran the script (never wrote inline comparison)
- [ ] **Domain keys checked**: Consulted `references/domain_mapping.md` for industry-specific terminology
- [ ] **Task requirements scanned**: Searched task description for exact output field names
- [ ] **Keys match**: Output keys align with task requirements or domain mapping
- [ ] **Type correctness**: Numeric fields are JSON numbers, integers lack `.0`
- [ ] **Determinism**: Arrays sorted by ID
- [ ] **Spot-check**: Verified 2-3 changes manually against source files

## Known invariants (by sub-task)

### portfolio-comparison
- Output arrays must be sorted by ID for deterministic output.
- Numeric fields must be JSON numbers, not quoted strings.
- Integer values should not have `.0` suffix in output.

### medication-reconciliation
- Check `references/domain_mapping.md` for medication-specific key names.
- Common keys: `deleted_medications`, `modified_medications`, `new_medications`.

### shipping-container-manifest-diff
- Container IDs typically follow pattern `CNT` followed by digits (e.g., `CNT0001`).
- Use `missing_containers` for removed IDs, `changed_containers` for modifications.
- Weight fields extracted from PDF come as strings (e.g., `"45.8"`) while Excel has floats—normalization happens automatically via compute_diff.py.
- Check `references/domain_mapping.md` for shipping/logistics terminology.