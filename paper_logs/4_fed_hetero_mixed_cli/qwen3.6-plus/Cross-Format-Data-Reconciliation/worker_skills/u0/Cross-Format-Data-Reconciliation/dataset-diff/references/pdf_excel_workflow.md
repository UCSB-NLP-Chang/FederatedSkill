# PDF to Excel Diff Workflow

Complete working pattern for comparing an archived PDF table against a current Excel/CSV dataset.

## When to use this

- Baseline data is locked in a PDF report (e.g., annual snapshot)
- Current data is in Excel/CSV (e.g., exported from a system)
- You need to detect retired records, new records, and field-level changes

## Full Script Pattern

```python
import pdfplumber
import pandas as pd
import json

def format_output(val):
    """Convert float whole numbers to int for clean JSON output."""
    if isinstance(val, float) and val.is_integer():
        return int(val)
    return val

def normalize_for_comparison(val):
    """Normalize for comparison: strip strings, convert numeric strings to float."""
    if pd.isna(val):
        return None
    if isinstance(val, str):
        val = val.strip()
        try:
            return float(val)
        except ValueError:
            return val
    return val

# 1. Extract from PDF (Archive)
with pdfplumber.open('/path/to/archive.pdf') as pdf:
    # Handle multi-page: iterate all pages and concatenate tables
    all_rows = []
    headers = None
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            if not table:
                continue
            if headers is None:
                headers = table[0]
                all_rows.extend(table[1:])
            else:
                # Verify headers match if multiple tables
                all_rows.extend(table[1:])

    df_old = pd.DataFrame(all_rows, columns=headers)

# 2. Extract from Excel/CSV (Current)
df_new = pd.read_excel('/path/to/current.xlsx')
# or: df_new = pd.read_csv('/path/to/current.csv')

# 3. Normalize column names (strip whitespace)
df_old.columns = df_old.columns.str.strip()
df_new.columns = df_new.columns.str.strip()

# 4. Set primary key as index
key_col = 'ID'  # Adjust to your key column
df_old = df_old.set_index(key_col)
df_new = df_new.set_index(key_col)

# 5. Identify retired and added
retired_ids = sorted(df_old.index.difference(df_new.index).tolist())
added_ids = sorted(df_new.index.difference(df_old.index).tolist())

# 6. Compare shared records
changes = []
shared_ids = df_old.index.intersection(df_new.index)

for idx in shared_ids:
    # Get all columns from both datasets
    all_cols = set(df_old.columns) | set(df_new.columns)

    for col in all_cols:
        old_val = df_old.loc[idx, col] if col in df_old.columns else None
        new_val = df_new.loc[idx, col] if col in df_new.columns else None

        # Normalize for comparison
        old_norm = normalize_for_comparison(old_val)
        new_norm = normalize_for_comparison(new_val)

        if old_norm != new_norm:
            changes.append({
                "id": idx,
                "field": col,
                "old_value": format_output(old_norm) if old_norm is not None else None,
                "new_value": format_output(new_norm) if new_norm is not None else None
            })

# 7. Sort changes by ID and field for deterministic output
changes.sort(key=lambda x: (x["id"], x["field"]))

# 8. Build result with domain-specific keys if needed
result = {
    "removed_ids": retired_ids,  # or "retired_schools", "dropped_categories", etc.
    "added_ids": added_ids,
    "changed_records": changes    # or "revised_schools", "adjusted_categories", etc.
}

# 9. Write output
with open('/path/to/output.json', 'w') as f:
    json.dump(result, f, indent=2)

print(json.dumps(result, indent=2))
```

## Critical Implementation Notes

1. **Multi-page PDFs**: The example above iterates all pages. If your PDF has one table split across pages, you'll concatenate rows. If it has multiple separate tables, you may need filtering logic.

2. **Missing columns**: When one dataset has columns the other lacks, the comparison loop handles this by checking `if col in df.columns`.

3. **Null handling**: `pd.isna()` checks handle empty cells. Nulls compare as equal (None == None).

4. **Type coercion**: PDFs extract numbers as strings (e.g., `"7596"`). Excel reads them as floats. Always normalize to float for comparison, then format for output.

5. **Sort for determinism**: Sort `retired_ids`, `added_ids`, and `changes` to ensure consistent output across runs.

## Validation Checklist

- [ ] Row counts: `len(retired_ids) + len(shared_ids) == len(df_old)`
- [ ] Column counts match expected schema after stripping whitespace
- [ ] Spot-check 2-3 changes manually against both source files
- [ ] Verify numeric fields are JSON numbers (unquoted) and integers lack `.0`
