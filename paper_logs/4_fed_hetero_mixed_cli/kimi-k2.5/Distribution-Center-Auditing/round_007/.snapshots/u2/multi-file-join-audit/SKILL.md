---
name: multi-file-join-audit
description: Audits data across multiple Excel files using joins, alias normalization, event status filtering, and template preservation. Use when input spans separate .xlsx files requiring cross-file lookups, value normalization via alias maps, status-based filtering, computing missing/mismatch flags with summary aggregation, and preserving template sheets (e.g., Overview) unchanged in the output workbook.
---

# Multi-File Join Audit

## When to Use
- Input spans **multiple Excel files** (e.g., `Return_Plan.xlsx`, `Disposition_Event_Log.xlsx`, `Disposition_Alias.xlsx`, or `Manifest_Plan.xlsx`, `Dock_Scan_Log.xlsx`)
- Task requires normalizing free-text values via an alias/lookup table
- Event logs contain mixed statuses (COMPLETED, PENDING, VOID, LOADED, STAGED) and only specific statuses count
- Need to detect: (1) Missing Events (no qualifying event), (2) Mismatches (normalized != planned)
- **Template preservation**: Output workbook must include a pre-existing sheet (e.g., `Overview`) copied unchanged from a template file

## Environment Prerequisites
```bash
pip install --break-system-packages openpyxl python-docx -q
```

## Workflow

1. **Inspect Inputs**: Use temporary openpyxl scripts to examine all input files (do not use `read_file` on .xlsx).
   - Identify key columns (IDs, quantities, status flags, categories)
   - Note any auxiliary sheets (alias maps, reference data)

2. **Load All Input Files**: Use `openpyxl` to load each file separately.
   ```python
   plan_wb = openpyxl.load_workbook('Plan.xlsx')
   event_wb = openpyxl.load_workbook('Events.xlsx')
   alias_wb = openpyxl.load_workbook('Aliases.xlsx')  # if applicable
   template_wb = openpyxl.load_workbook('Template.xlsx')  # if template required
   ```

3. **Build Alias Map** (if applicable): Load the alias sheet as a case-insensitive lookup dict.
   ```python
   alias_map = {}
   for row in alias_ws.iter_rows(min_row=2, values_only=True):
       alias_val, standard = row[0], row[1]
       if alias_val is not None and standard is not None:
           alias_map[str(alias_val).strip().lower()] = str(standard).strip()
   ```

4. **Filter & Deduplicate Events**: Keep only rows with qualifying status. If multiple events exist per key, select the latest by timestamp.
   ```python
   qualifying_events = {}  # (id1, id2) -> (event_time, value)
   for row in event_rows:
       if row[status_idx] is None:
           continue
       status = str(row[status_idx]).strip().upper()
       if status == qualifying_status:  # 'COMPLETED' or 'LOADED'
           key = (str(row[id1_idx]).strip(), str(row[id2_idx]).strip())
           ts = row[time_idx]
           value = str(row[value_idx]).strip()
           if key not in qualifying_events or ts > qualifying_events[key][0]:
               qualifying_events[key] = (ts, value)
   ```

5. **Compute Flags**: For each plan line:
   - **Missing Event** = `1` if key not in `qualifying_events`, else `0`
   - **Mismatch** = `0` if missing; else normalize via alias map (if applicable) and compare
   - **Total Errors** = Missing + Mismatch (integer sum)
   - **Error Summary** = comma-separated error names or `"None"` string

6. **Aggregate Summary**: Group by task-specified keys. Filter to groups with `Total Errors > 0`. Sort deterministically. Add Grand Total row.

7. **Preserve Template Sheets** (if applicable): Copy template sheets cell-by-cell before adding data sheets.
   ```python
   out_wb = openpyxl.Workbook()
   # Remove default 'Sheet' from Workbook()
   out_wb.remove(out_wb.active)

   # Copy template sheet(s)
   for src_name in ['Overview']:
       src_ws = template_wb[src_name]
       dst_ws = out_wb.create_sheet(src_name)
       for row in src_ws.iter_rows(min_row=1, max_row=src_ws.max_row, max_col=src_ws.max_column, values_only=False):
           for cell in row:
               dst_ws.cell(row=cell.row, column=cell.column, value=cell.value)
   ```
   See `references/template-preservation.md` for full pattern details.

8. **Generate Outputs**: Add `RawData`, `Formatted Data`, and `Summary` sheets. Use `python-docx` to draft an executive brief.

9. **Verify**: Run verification to confirm sheet names, dimensions, flag types, and Error Summary strings.

## Critical Rules

### 1. Filter Events by Qualifying Status Only
Only count events with the specified status (e.g., `COMPLETED`, `LOADED`). Ignore `PENDING`, `VOID`, `CANCELLED`, `STAGED`.

**WRONG**:
```python
if status:  # Accepts any non-empty status
```

**CORRECT**:
```python
if status and str(status).strip().upper() == 'LOADED':
```

### 2. Deduplicate by Latest Timestamp
When multiple qualifying events exist per composite key, select the one with the latest timestamp:
```python
if key not in lookup or current_time > lookup[key][0]:
    lookup[key] = (current_time, value)
```

### 3. Integer Flags and None String
- Missing Event / Mismatch: `1` or `0` (integer, not boolean)
- Error Summary: `"None"` string for rows with zero errors

### 4. Preserve Template Sheets Exactly
When a template file contains sheets that must be preserved unchanged, copy them cell-by-cell. Do not modify content or formatting.

### 5. Remove Default Sheet
`Workbook()` always creates a default `'Sheet'`. Remove with `out_wb.remove(out_wb.active)` before adding your own sheets.

### 6. Alias Normalization (when applicable)
Always normalize event values via the alias map before comparing to planned values. Use `.lower()` for case-insensitive lookup.

## Decision Rules & Anti-Patterns

- **Do not** compare raw event values to planned values without alias normalization (when alias map provided).
- **Do not** count PENDING, VOID, STAGED, or CANCELLED events as qualifying.
- **Do not** assume one event per plan line; always deduplicate by selecting the latest.
- **Do not** use pandas for multi-file joins; it adds dependency risk and obscures cell-level control. Use `openpyxl` with explicit dict lookups.
- **Do not** forget to handle `None` values from `openpyxl` before calling `.strip()` or `.upper()`.
- **Do not** forget to remove the default `'Sheet'` from `Workbook()` before saving.
- **Do not** use `shutil.copy` or file-level copy for template sheets; copy cell-by-cell to preserve structure without carrying over hidden metadata.
- **Do not** include rows with Total Errors = 0 in the Summary sheet (filter to error groups only).
- **Do not** use pandas for verification; it displays NaN for "None" strings. Use openpyxl directly.

## Output Precision
Never round, truncate, or fixed-format numeric values when writing outputs:
- **DO NOT**: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`
- **DO**: `ws.cell(row=r, column=c, value=x)` with x as a raw integer or float
The verifier's tolerance (often 1e-4) decides acceptable precision; provide full precision.

## Known Invariants (by sub-task)

### returns-disposition-audit (B4)
- Input spans **multiple separate Excel files**: Plan, Event Log, Alias Map. Load each with separate `openpyxl.load_workbook()` calls.
- Event status filter: Only `COMPLETED` events count. `PENDING`, `VOID`, `CANCELLED` are ignored.
- Latest event wins: When multiple COMPLETED events exist per (Return ID, Line ID), select the one with the latest Event Time.
- Alias normalization: Case-insensitive `.lower()` lookup before comparing dispositions.
- Key tuple: (Return ID, Line ID) as composite join key.
- Output: Excel with RawData, Formatted Data, Summary + Word brief.

### harbor-outbound-manifest-audit (B5)
- Input spans **two separate Excel files**: Manifest Plan and Dock Scan Log, plus a template workbook with an `Overview` sheet.
- Event status filter: Only `LOADED` scans count. `VOID`, `STAGED`, and other statuses are ignored.
- Missing Load Scan = `1` if no `LOADED` status scan exists for the (Shipment ID, Carton ID) pair.
- Zone Mismatch = `1` if the latest `LOADED` scan's Scanned Zone differs from Planned Zone.
- Latest scan wins: When multiple LOADED scans exist per (Shipment ID, Carton ID), use the one with the latest Scan Timestamp.
- Key tuple: (Shipment ID, Carton ID) as composite join key.
- Summary aggregates by (Route, Shipment ID), filters to groups with Total Errors > 0, includes Grand Total row.
- Template `Overview` sheet must be copied unchanged from the template workbook.
- Output: Excel with Overview, RawData, Formatted Data, Summary + Word brief.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Verifier expects different column names | Task specifies exact header names | Match column names exactly (case-sensitive, no extra spaces) |
| Summary row count mismatch | Filtering logic too aggressive/lenient | Verify `Total Errors > 0` filter is applied after aggregation |
| Error Summary shows `NaN` in pandas readback | Pandas type inference artifact | Verify with `openpyxl` directly; actual cell value is correct if it shows `"None"` |
| Mismatch count too high | Alias map missing entries or case mismatch | Ensure alias map covers all variants; use `.lower()` for lookup |
| Missing Event count wrong | Event status filter too strict/lenient | Check exact status string comparison (strip whitespace, uppercase) |
| Extra 'Sheet' in output | Default sheet from `Workbook()` not removed | Call `out_wb.remove(out_wb.active)` immediately after `Workbook()` |
| Template sheet missing or corrupted | Used file copy instead of cell-by-cell copy | Copy cells individually with `dst_ws.cell(row=r, column=c, value=cell.value)` |
| Summary not sorted correctly | Unsorted keys | Sort summary rows by grouping keys with `sorted(keys)` |

## Script Usage
Execute `scripts/generate_returns_audit.py` for returns disposition tasks or `scripts/generate_outbound_audit.py` for outbound manifest tasks. Adapt column indices, grouping keys, and qualifying event status to match specific task requirements.

## Related Skills
- `excel-audit-reporting`: For single-file multi-sheet audit patterns (receipts, SLA, timesheets). Shares output format conventions and verification steps.
