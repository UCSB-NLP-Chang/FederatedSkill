---
name: dataset-diff
description: Compare two versions of a dataset to detect added, removed, and modified records. Use when tasked with finding differences between PDF archives and Excel/CSV current files, comparing snapshots, or generating change reports.
---

# Dataset Diff

Compare two datasets and produce a structured diff report.

## When to Use
- Comparing archived vs current data (PDF vs Excel, old vs new CSV)
- Detecting record additions, removals, and field-level changes
- Generating change logs or migration validation reports

## Workflow

1. **Load both datasets** into comparable structures (pandas DataFrames or dicts keyed by ID)
2. **Identify the key field** that uniquely identifies records (e.g., `ID`, `service_id`)
3. **Detect changes**:
   - **Removed**: Keys in old dataset but not in new
   - **Added**: Keys in new dataset but not in old
   - **Modified**: Keys in both but with different field values
4. **For modified records**, compare each field and record only the changed fields
5. **Output structured diff** in JSON format

## Validation Steps
- Verify the key field exists and is unique in both datasets
- Check for null/empty handling consistency
- Confirm numeric comparisons handle float precision (use tolerance or round)
- Validate output JSON is parseable before writing

## Anti-Patterns
- Do not assume datasets are sorted the same way—always key by ID
- Do not compare floats directly; use `abs(a-b) < tolerance` or round to consistent precision
- Do not ignore case sensitivity in string comparisons unless explicitly required

## Output Format

```json
{
  "removed_ids": ["ID1", "ID2"],
  "added_ids": ["ID3"],
  "changed_records": [
    {"id": "ID4", "field": "FieldName", "old_value": "old", "new_value": "new"}
  ]
}
```

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

_None documented yet — add verifier-discovered invariants here as they emerge._

## Scripts
- `scripts/diff_datasets.py` — Reusable Python script for DataFrame comparison

## References
- `references/diff_schema.md` — Full JSON schema for diff output
