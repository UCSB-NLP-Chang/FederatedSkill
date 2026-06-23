---
name: spreadsheet-audit-reporting
description: Use when tasked with reading tabular data from Excel, computing derived metrics (variances, flags, error counts), and producing a multi-sheet audit workbook alongside an executive Word brief. Covers openpyxl and python-docx workflows.
---

# Spreadsheet Audit & Report Generation

## Workflow
1. **Install dependencies**: `pip install openpyxl python-docx pandas`
2. **Inspect source data**: Load the source `.xlsx`, print sheet names, headers, and 3-5 sample rows to confirm column names and data types.
3. **Clean column names**: Strip whitespace from headers immediately after loading—pandas preserves leading/trailing spaces which break groupby operations:
   ```python
   df.columns = [col.strip() for col in df.columns]
   ```
4. **Compute derived metrics**:
   - Calculate variances (e.g., `Expected - Received`).
   - Flag categorical errors (e.g., `Temp Status != 'OK'`).
   - Aggregate totals per grouping key (e.g., Item Code + Supplier, or Carrier + Yard).
5. **Generate audit workbook**:
   - Create `RawData` sheet: exact copy of source rows.
   - Create `Formatted Data` sheet: source columns + computed columns.
   - Create `Summary` sheet: aggregated counts/totals + Grand Total row.
   - **CRITICAL**: `openpyxl.Workbook()` initializes with a default `'Sheet'`. Delete it immediately: `del wb['Sheet']` before saving.
6. **Generate executive brief**: Use `python-docx` to write definitions, totals, high-priority items, and recommendations.
7. **Verify outputs**: Reload both files. Confirm sheet names, row counts (header + data), column headers, and that summary totals match row-level sums. Run a quick inline Python verification script before finalizing.

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

### Column Name Whitespace (Critical for groupby)
Pandas preserves leading/trailing spaces in Excel headers. This causes silent KeyError failures in groupby:

**Wrong**:
```python
df = pd.read_excel('data.xlsx')
df.groupby(['Carrier', 'Yard'])  # KeyError if header was ' Yard'
```

**Correct**:
```python
df = pd.read_excel('data.xlsx')
df.columns = [col.strip() for col in df.columns]
df.groupby(['Carrier', 'Yard'])  # Now safe
```

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

## Seal Error Pattern (Case-Insensitive, Null-Safe)

When flagging seal compliance errors, handle null Seal Status values:

```python
import pandas as pd

def seal_error(row):
    # Case-insensitive check for Seal Required
    if str(row['Seal Required']).upper() == 'YES':
        # Seal Status may be null/NaN for non-sealed shipments
        if pd.isna(row['Seal Status']) or str(row['Seal Status']).upper() != 'VERIFIED':
            return 1
    return 0

df['Seal Error'] = df.apply(seal_error, axis=1)
```

See `references/computed-column-examples.md` for more patterns.

## Validation Checklist
- [ ] Source headers match expected names after stripping whitespace.
- [ ] Output workbook contains exactly the required sheets (no default `'Sheet'`).
- [ ] `Formatted Data` row count matches `RawData`.
- [ ] `Summary` grand total equals sum of detail rows.
- [ ] Error Summary column contains literal string `"None"` (not Python `None` or empty cell).
- [ ] Word brief contains all required sections (definitions, totals, top items, recommendations).

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### harbor-receiving-exception-audit
- Output workbook must contain exactly 3 sheets: `RawData`, `Formatted Data`, `Summary`. No extra default `'Sheet'` from openpyxl.Workbook().
- Error Summary column must contain literal string `"None"` for clean rows, not Python `None`/empty cell.
- Summary sheet Grand Total row uses `-` placeholder for secondary grouping key (Supplier).
- Summary sheet excludes zero-error groups (filter before appending Grand Total).

### harbor-trailer-detention-audit
- Column names may contain leading whitespace (e.g., `' Yard'`). Strip immediately after load.
- Output workbook must contain exactly 3 sheets: `RawData`, `Formatted Data`, `Summary`.
- Error Summary column must contain literal string `"None"` for clean rows.
- Summary sheet groups by Carrier and Yard, with Grand Total row using `-` placeholder for Yard.
- Computed columns: `Detention Overrun` (Actual > Allowed), `Seal Error`, `Total Errors`, `Error Summary`.
- Seal Error logic: case-insensitive check for `Seal Required == 'YES'` AND `Seal Status != 'VERIFIED'`. Seal Status may be null/NaN—use `pd.isna()` check.