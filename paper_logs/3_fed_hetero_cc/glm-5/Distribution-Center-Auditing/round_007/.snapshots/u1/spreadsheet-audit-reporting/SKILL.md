---
name: spreadsheet-audit-reporting
description: Use when tasked with reading tabular data from Excel, computing derived metrics (variances, flags, error counts), and producing a multi-sheet audit workbook alongside an executive Word brief. Covers openpyxl and python-docx workflows. Triggers include tasks named *-audit, SLA compliance checks, exception reporting, multi-sheet Excel analysis with summary aggregation, and multi-file joins with lookup/alias tables.
---

# Spreadsheet Audit & Report Generation

## Workflow
1. **Install dependencies**: `pip install openpyxl python-docx pandas`
2. **Inspect source data**: Load the source `.xlsx`, print sheet names, headers, and 3-5 sample rows to confirm column names and data types.
3. **Clean column names**: Strip whitespace from headers immediately after loading—pandas preserves leading/trailing spaces which break groupby operations:
   ```python
   df.columns = [col.strip() for col in df.columns]
   ```
4. **Load lookup/reference tables** (if present): Many audit tasks include a separate sheet or file with thresholds, rules, mappings, or aliases. Build a dictionary for efficient lookups:
   ```python
   rules_df = pd.read_excel(source, sheet_name='SLA_Rules')
   sla_lookup = {row['Priority Tier']: {'Max Hours': row['Max Open Hours'], 'Escalation': row['Escalation Required']} 
                 for _, row in rules_df.iterrows()}
   ```
5. **Multi-file joins** (if present): When audit requires joining data across multiple files:
   - Use merge or dictionary lookups on composite keys (e.g., Return ID + Line ID)
   - Prefer left join from primary data to preserve all rows even if lookup data is missing
   - Build lookup dictionaries for O(1) access: `event_lookup = {(row['Return ID'], row['Line ID']): row['Final Disposition'] for _, row in events_df.iterrows()}`
6. **Normalize values via alias lookup** (if present): When comparing values that may have multiple representations:
   ```python
   alias_df = pd.read_excel(source, sheet_name='AliasMap')
   alias_lookup = {row['Alias'].upper(): row['Standard Disposition'].upper() 
                   for _, row in alias_df.iterrows()}
   normalized = alias_lookup.get(raw_value.upper(), raw_value.upper())
   ```
7. **Compute derived metrics**:
   - Calculate variances (e.g., `Expected - Received`).
   - Flag categorical errors (e.g., `Temp Status != 'OK'`).
   - For SLA/threshold audits: compare values against lookup thresholds.
   - For conditional null checks: flag when a field is required but missing.
   - For event status filtering: flag when status is not COMPLETED.
   - Aggregate totals per grouping key (e.g., Item Code + Supplier, or Carrier + Yard).
8. **Generate audit workbook**:
   - Create `RawData` sheet: exact copy of source rows.
   - Create `Formatted Data` sheet: source columns + computed columns.
   - Create `Summary` sheet: aggregated counts/totals + Grand Total row.
   - **CRITICAL**: `openpyxl.Workbook()` initializes with a default `'Sheet'`. Delete it immediately: `del wb['Sheet']` before saving.
9. **Generate executive brief**: Use `python-docx` to write definitions, totals, high-priority items, and recommendations.
10. **Verify outputs**: Reload both files. Confirm sheet names, row counts (header + data), column headers, and that summary totals match row-level sums. Run a quick inline Python verification script before finalizing.

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

### String Formatting in Word Documents
When inserting IDs or codes into Word document text, ensure the full value is used. String slicing or formatting errors can truncate identifiers (e.g., showing "E" instead of "E660"). Always verify inserted values match source data exactly.

### Multi-File Join Data Loss
When joining data from multiple files, verify row counts before and after join. A failed join can silently drop rows:
- Use left join to preserve all primary rows: `df.merge(lookup_df, on=['Key1', 'Key2'], how='left')`
- Check for unexpected nulls in joined columns after merge
- Build dictionaries for explicit control: `lookup.get(key)` returns None for missing keys

### Case Sensitivity in Value Comparison
When comparing values that may differ in case, normalize both sides:
```python
if planned.upper() != actual.upper():
    return 1  # Mismatch
```

### Timestamp & Type Checking
Excel timestamps or dates may be read as strings or `datetime` objects depending on the library and cell formatting. Always check `type()` before applying comparison operators (`<`, `>`) or arithmetic. Ensure you are comparing against compatible scalar types, not tuples or dicts.

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

See `references/computed-column-examples.md` for more patterns including SLA breach detection and missing escalation checks.

## Validation Checklist
- [ ] Source headers match expected names after stripping whitespace.
- [ ] Output workbook contains exactly the required sheets (no default `'Sheet'`).
- [ ] `Formatted Data` row count matches `RawData`.
- [ ] `Summary` grand total equals sum of detail rows.
- [ ] Error Summary column contains literal string `"None"` (not Python `None` or empty cell).
- [ ] Word brief contains all required sections (definitions, totals, top items, recommendations).
- [ ] Multi-file joins: verify row counts preserved after join operations.

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

### harbor-promo-register-audit
- Output workbook must contain exactly 3 sheets: `RawData`, `Formatted Data`, `Summary`.
- Error Summary column must contain literal string `"None"` for clean rows.
- Summary sheet groups by SKU and Store ID, with Grand Total row using `-` placeholder for Store ID.
- Computed columns: `Price Error` (Register Price != Promo Price), `Window Error` (Sale Date outside promo period), `Total Errors`, `Error Summary`.
- Date comparison: source dates are ISO-format strings (e.g., `'2026-03-01'`). String comparison works for ISO format; convert to datetime if format differs.
- Window Error logic: `Sale Date < Promo Start Date OR Sale Date > Promo End Date`.
- Summary sheet includes all groups (including zero-error groups) unless task specifies filtering.

### harbor-service-queue-sla-audit
- Source workbook contains multiple sheets: data sheet (e.g., `Tickets`) and lookup sheet (e.g., `SLA_Rules`).
- Build lookup dictionary from SLA_Rules for threshold comparisons.
- Computed columns: `SLA Breach` (Open Age Hours > Max Open Hours for priority tier), `Missing Escalation` (Escalation Required but Escalation Code is null), `Total Errors`, `Error Summary`.
- Summary sheet groups by Queue and Region, with Grand Total row using `-` placeholder for Region.
- Escalation Code may be null/NaN—use `pd.isna()` check for missing escalation detection.
- Summary sheet includes only groups with errors (filter where Total Errors > 0 before appending Grand Total).

### harbor-timesheet-policy-audit
- Source workbook contains multiple sheets: data sheet (e.g., `Entries`) and lookup sheet (e.g., `BreakRules`).
- Build lookup dictionary from BreakRules keyed by Role for threshold comparisons:
  ```python
  rules_df = pd.read_excel(source, sheet_name='BreakRules')
  break_rules = {row['Role']: {'min_break': row['Min Break Minutes'], 
                               'overtime_thresh': row['Overtime Threshold']} 
                 for _, row in rules_df.iterrows()}
  ```
- Computed columns: `Break Deficit` (Break Minutes < Min Break Minutes for role), `Approval Missing` (Hours Worked > Overtime Threshold AND Approval Code is null), `Total Errors`, `Error Summary`.
- Summary sheet groups by Employee ID and Week Ending, with Grand Total row using `-` placeholder for Week Ending.
- Approval Code may be null/NaN—use `pd.isna()` check for missing approval detection.
- Summary sheet includes only groups with errors (filter where Total Errors > 0 before appending Grand Total).
- For Word brief high-priority section: aggregate Total Errors by Employee ID across all weeks, sort descending, take top N employees.

### harbor-returns-disposition-audit
- Source data spans multiple files: plan file, event log file, and alias/lookup file.
- Join plan data with event log on composite key (Return ID + Line ID).
- Build alias lookup dictionary to normalize disposition values before comparison:
  ```python
  alias_lookup = {row['Alias'].upper(): row['Standard Disposition'].upper() 
                  for _, row in alias_df.iterrows()}
  ```
- Computed columns: `Missing Final Event` (Event Status != 'COMPLETED'), `Disposition Mismatch` (normalized planned != normalized actual), `Total Errors`, `Error Summary`.
- Only compare dispositions for COMPLETED events; non-COMPLETED events have Missing Final Event flagged instead.
- Summary sheet groups by Warehouse and Carrier, with Grand Total row using `-` placeholder for Carrier.
- Summary sheet includes only groups with errors (filter where Total Errors > 0 before appending Grand Total).

### harbor-outbound-manifest-audit
- Source contains `Manifest_Plan.xlsx` (plan lines), `Dock_Scan_Log.xlsx` (scan events), and `Outbound_Audit_Template.xlsx` (template with `Overview`, `RawData`, `Formatted Data`, `Summary` sheets).
- Match events to plan lines using composite key `(Shipment ID, Carton ID)`.
- Error Flags: `Missing Load Scan` (no `LOADED` status event exists for the key—check via `key not in loaded_events`), `Zone Mismatch` (Planned Zone != Scanned Zone, only for rows with `LOADED` events).
- Summary sheet groups by Route and Shipment ID, with Grand Total row using `-` placeholder for Shipment ID.
- Summary sheet includes only groups with errors (filter where Total Errors > 0 before appending Grand Total).
- Preserve `Overview` sheet exactly from the template; do not modify or overwrite it.