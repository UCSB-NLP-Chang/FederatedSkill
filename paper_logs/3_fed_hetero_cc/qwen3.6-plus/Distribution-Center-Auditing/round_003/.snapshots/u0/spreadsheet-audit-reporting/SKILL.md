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

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### harbor-receiving-exception-audit
- 3 sheets: `RawData`, `Formatted Data`, `Summary`. No extra `'Sheet'`.
- Error Summary uses literal `"None"` string for clean rows.
- Grand Total uses `'-'` placeholder for secondary grouping key.

### harbor-trailer-detention-audit
- Strip column names before any operations (headers may have whitespace).
- Seal Error: check `pd.isna(Seal Status)` when Seal Required='NO' or null.
- Summary grouped by (Carrier, Yard), Grand Total uses `'-'` for Yard.

### promo-register-audit
- Price Error: `Register Price != Promo Price` (1 if mismatch).
- Window Error: `Sale Date < Promo Start Date` OR `Sale Date > Promo End Date`.
- Summary grouped by (SKU, Store ID), filtered to `Total Errors > 0`.
- Grand Total uses `'-'` for Store ID column.

## Validation Checklist
- [ ] Source headers match expected names.
- [ ] Output workbook contains exactly the required sheets (no default `'Sheet'`).
- [ ] `Formatted Data` row count matches `RawData`.
- [ ] `Summary` grand total equals sum of detail rows.
- [ ] Word brief contains all required sections (definitions, totals, top items, recommendations).
