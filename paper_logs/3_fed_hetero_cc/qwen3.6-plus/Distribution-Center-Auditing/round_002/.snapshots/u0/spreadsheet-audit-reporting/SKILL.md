---
name: spreadsheet-audit-reporting
description: Use when tasked with reading tabular data from Excel, computing derived metrics (variances, flags, error counts), and producing a multi-sheet audit workbook alongside an executive Word brief. Covers openpyxl and python-docx workflows.
---

# Spreadsheet Audit & Report Generation

## Workflow
1. **Install dependencies**: `pip install openpyxl python-docx`
2. **Inspect source data**: Load the source `.xlsx`, print sheet names, headers, and 3-5 sample rows to confirm column names and data types.
3. **Compute derived metrics**:
   - Calculate variances (e.g., `Expected - Received`).
   - Flag categorical errors (e.g., `Temp Status != 'OK'`).
   - Aggregate totals per grouping key (e.g., Item Code + Supplier).
4. **Generate audit workbook**:
   - Create `RawData` sheet: exact copy of source rows.
   - Create `Formatted Data` sheet: source columns + computed columns.
   - Create `Summary` sheet: aggregated counts/totals + Grand Total row.
   - **CRITICAL**: `openpyxl.Workbook()` initializes with a default `'Sheet'`. Delete it immediately: `del wb['Sheet']` before saving.
5. **Generate executive brief**: Use `python-docx` to write definitions, totals, high-priority items, and recommendations.
6. **Verify outputs**: Reload both files. Confirm sheet names, row counts (header + data), column headers, and that summary totals match row-level sums. Run a quick inline Python verification script before finalizing.

## Anti-Patterns & Troubleshooting

### None vs "None" String (Critical)
Python `None` writes as an empty Excel cell, not the text "None":

**Wrong**:
```python
df['Error Summary'] = None  # Results in empty cell
```

**Correct**:
```python
df['Error Summary'] = "None"  # Explicit string for literal "None" text
```

- Pandas displays string "None" as NaN; verify with openpyxl `values_only=True` to see actual cell values.
- When the task requires literal "None" text in output, always use the string `"None"`.

### Extra Default Sheet
Always remove or rename the default sheet created by `openpyxl.Workbook()`. Failing to do so leaves an empty `'Sheet'` in the output.

### Multi-key Aggregation & Sorting
- Group rows using composite keys: `groups[(row['Carrier'], row['Yard'])] += 1`
- Sort summary rows explicitly before writing: `sorted(groups.items(), key=lambda x: (x[0][0], x[0][1]))`
- Always append a "Grand Total" row at the end that sums all detail rows.

### Mismatched Totals
Always cross-check `Summary` grand totals against the sum of detail rows. If they differ, check for off-by-one errors in aggregation loops or missing `else` branches in flag logic.

### Header Drift
When copying source data, explicitly map columns by header name rather than index to avoid silent misalignment if source layout changes.

### Word Formatting
Use `python-docx` paragraph and run styling directly. Avoid converting Markdown/HTML to DOCX unless explicitly required; direct API usage yields cleaner, more predictable results.

## Validation Checklist
- [ ] Source headers match expected names.
- [ ] Output workbook contains exactly the required sheets (no default `'Sheet'`).
- [ ] `Formatted Data` row count matches `RawData`.
- [ ] `Summary` grand total equals sum of detail rows.
- [ ] Word brief contains all required sections (definitions, totals, top items, recommendations).
