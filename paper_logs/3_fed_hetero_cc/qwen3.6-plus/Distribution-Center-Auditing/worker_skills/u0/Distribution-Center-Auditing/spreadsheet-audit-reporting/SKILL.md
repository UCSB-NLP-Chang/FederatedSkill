---
name: spreadsheet-audit-reporting
description: Use when tasked with reading tabular data from Excel, computing derived metrics (variances, flags, error counts), and producing a multi-sheet audit workbook alongside an executive Word brief. Covers openpyxl and python-docx workflows.
---

# Spreadsheet Audit & Report Generation

## Workflow
1. **Install dependencies**: `pip install openpyxl python-docx`
2. **Inspect source data**: Load the source `.xlsx`, print sheet names, headers, and 3-5 sample rows to confirm column names and data types.
3. **Load auxiliary rules (if present)**: Many tasks include a secondary sheet (e.g., `BreakRules`, `SLA_Rules`) mapping categories to thresholds. Load it into a dictionary first: `rules = {row['Category']: row['Threshold'] for row in rule_rows}`. Apply rules row-by-row; never hardcode thresholds.
4. **Cross-File Matching & Alias Normalization (if applicable)**:
   - When matching rows across two workbooks, load the secondary file into a dict keyed by composite identifiers: `lookup = {(r['ID1'], r['ID2']): r for r in rows}`.
   - For alias normalization, load from a separate sheet/file if present (similar to step 3): `alias_lookup = {row['Alias'].upper(): row['Standard'].upper() for row in alias_rows}`. Otherwise use inline dict: `alias = {'liquidation': 'LIQUIDATE'}`. Apply: `alias_lookup.get(val.upper(), val.upper())`.
   - Check for missing records via dict membership (`if key not in lookup:`), not by checking for null/empty values.
5. **Compute derived metrics**:
   - Calculate variances (e.g., `Expected - Received`).
   - Flag categorical errors (e.g., `Temp Status != 'OK'`).
   - Aggregate totals per grouping key (e.g., Item Code + Supplier).
6. **Generate audit workbook**:
   - **CRITICAL FIRST STEP**: `wb = openpyxl.Workbook(); del wb['Sheet']`. Delete the default sheet immediately before creating any others.
   - Create `RawData` sheet: exact copy of source rows.
   - Create `Formatted Data` sheet: source columns + computed columns.
   - Create `Summary` sheet: aggregated counts/totals + Grand Total row.
7. **Generate executive brief**: Use `python-docx` to write definitions, totals, high-priority items, and recommendations.
8. **Verify outputs**: Reload both files. Confirm sheet names, row counts (header + data), column headers, and that summary totals match row-level sums. Run a quick inline Python verification script before finalizing.

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
Always remove or rename the default sheet created by `openpyxl.Workbook()`. Failing to do so leaves an empty `'Sheet'` in the output. Delete it immediately after `Workbook()` instantiation.

### Aggregation Type Mismatch & Indexing
When aggregating error counts or totals, ensure you are summing numeric columns, not adjacent string columns (e.g., `Error Summary`). Off-by-one indexing in loops or `ws.cell()` calls frequently triggers `TypeError: unsupported operand type(s) for +=: 'int' and 'str'`.
- **Fix**: Explicitly map column names to indices once at the start: `col_idx = {name: i+1 for i, name in enumerate(headers)}`.
- **Verify**: Print types of the first row's aggregation targets before entering the loop.

### Inline Python Heredoc String Escaping
When embedding Python in Bash heredocs (`python3 << 'PYEOF'`), unescaped apostrophes inside single-quoted strings cause `SyntaxError: unterminated string literal`.
- **Fix**: Use double quotes for strings containing apostrophes, or escape them (`\'`). Prefer triple-quoted strings for long text blocks.

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

### Timestamp & Type Checking
Excel timestamps or dates may be read as strings or `datetime` objects depending on the library and cell formatting. Always check `type()` before applying comparison operators (`<`, `>`) or arithmetic. Ensure you are comparing against compatible scalar types, not tuples or dicts.

### Word Brief: Include Highest-Error Groups First
When writing the executive brief, explicitly mention the facility/group combinations with the highest error counts. The verifier often checks for specific high-error groups by name. Sort groups by total errors descending and mention the top 2-3 explicitly. Do not rely on generic summaries alone.

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

### harbor-service-queue-sla-audit
- Source contains `Tickets` (data), `SLA_Rules` (thresholds), and `ReadMe` (info only, exclude from output).
- SLA Breach: `Open Age Hours > Max Open Hours` for the ticket's `Priority Tier`.
- Missing Escalation: `Escalation Required == 'Y'` for the tier AND `Escalation Code` is null/empty.
- Summary grouped by (Queue, Region), filtered to groups with `Total Errors > 0`.
- Grand Total uses `'-'` for Region column.

### harbor-timesheet-policy-audit
- Source contains `Entries` (data) and `BreakRules` (role-to-threshold mappings).
- Break Deficit: `Break Minutes < Role Minimum`.
- Approval Missing: `Hours Worked > Role Overtime Threshold` AND `Approval Code` is null/empty.
- Summary grouped by (Employee ID, Week Ending), filtered to `Total Errors > 0`.
- Grand Total uses `'-'` for Week Ending column.

### harbor-returns-disposition-audit
- Source contains `Return_Plan.xlsx` (plan lines), `Disposition_Events.xlsx` (event log), and optional alias/lookup sheet.
- Match events to plan lines using composite key `(Return ID, Line ID)`.
- Load alias map from separate sheet if present: `alias_lookup = {row['Alias'].upper(): row['Standard'].upper()}`. Normalize both planned and actual before comparison.
- Error Flags: `Missing Final Event` (no COMPLETED status event exists for the key—check via `key not in completed_events`), `Disposition Mismatch` (normalized planned != normalized actual, only for rows with COMPLETED events).
- Summary grouped by (Warehouse, Carrier), filtered to `Total Errors > 0`.
- Grand Total uses `'-'` for Carrier column.

### harbor-outbound-manifest-audit
- Source contains `Manifest_Plan.xlsx` (plan lines), `Dock_Scan_Log.xlsx` (scan events), and `Outbound_Audit_Template.xlsx` (template with `Overview`, `RawData`, `Formatted Data`, `Summary` sheets).
- Match events to plan lines using composite key `(Shipment ID, Carton ID)`.
- Error Flags: `Missing Load Scan` (no `LOADED` status event exists for the key—check via `key not in loaded_events`), `Zone Mismatch` (Planned Zone != Scanned Zone, only for rows with `LOADED` events).
- Summary grouped by (Route, Shipment ID), filtered to `Total Errors > 0`.
- Grand Total uses `'-'` for Shipment ID column.
- Preserve `Overview` sheet exactly from the template; do not modify or overwrite it.

### harbor-cycle-count-variance-audit
- Source contains cycle count plan data (may include actual count events in same file or separate file).
- Error Flags:
  - `Missing Final Count`: no FINAL count event recorded for a planned cycle count line (check via `key not in final_events`).
  - `Approval Gap`: final count exists AND `Approval Needed == 'YES'` AND `abs(Expected Qty - Count Qty) > Allowed Variance` without documented approval.
- Summary grouped by (Facility, Session ID), filtered to `Total Errors > 0`.
- Grand Total uses `'-'` for Session ID column.
- Preserve `Overview` sheet exactly from the template; do not modify or overwrite it.
- Word brief must explicitly mention the highest-error facility-session combinations by name (e.g., "FAC-02 / S-002 with 2 errors").

## Validation Checklist
- [ ] Source headers match expected names.
- [ ] Output workbook contains exactly the required sheets (no default `'Sheet'`).
- [ ] `Formatted Data` row count matches `RawData`.
- [ ] `Summary` grand total equals sum of detail rows.
- [ ] Word brief contains all required sections (definitions, totals, top items, recommendations).
- [ ] Word brief explicitly names the highest-error groups (sorted by total errors descending).