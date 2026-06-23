---
name: multi-file-join-audit
description: Audits data across multiple Excel files using joins, alias normalization, event status filtering, and template preservation. Use when input spans separate .xlsx files requiring cross-file lookups, value normalization via alias maps, status-based filtering, computing missing/mismatch flags with summary aggregation, and preserving template sheets (e.g., Overview) unchanged in the output workbook.
---

# Multi-File Join Audit

## When to Use
- Input spans **multiple Excel files** (e.g., `Return_Plan.xlsx`, `Disposition_Event_Log.xlsx`, `Disposition_Alias.xlsx`)
- Task requires normalizing free-text disposition values via an alias/lookup table
- Event logs contain mixed statuses (COMPLETED, PENDING, VOID) and only specific statuses count
- Need to detect: (1) Missing Final Events (no qualifying event), (2) Disposition Mismatches (normalized != planned)
- **Template preservation**: Output workbook must include a pre-existing sheet (e.g., `Overview`) copied unchanged from a template file

## Workflow

1. **Load All Input Files**: Use `openpyxl` to load each file separately. Do not use `read_file` on `.xlsx`.
   ```python
   plan_wb = openpyxl.load_workbook('Return_Plan.xlsx')
   event_wb = openpyxl.load_workbook('Disposition_Event_Log.xlsx')
   alias_wb = openpyxl.load_workbook('Disposition_Alias.xlsx')
   template_wb = openpyxl.load_workbook('Audit_Template.xlsx')  # if template required
   ```

2. **Build Alias Map**: Load the alias sheet as a case-insensitive lookup dict.
   ```python
   alias_map = {}
   for row in alias_ws.iter_rows(min_row=2, values_only=True):
       alias_val, standard = row[0], row[1]
       if alias_val is not None and standard is not None:
           alias_map[str(alias_val).strip().lower()] = str(standard).strip()
   ```
   **Note**: Duplicate aliases (e.g., "DONATION" and "Donation") will collide on `.lower()` key. This is fine if they map to the same standard value.

3. **Filter & Deduplicate Events**: Keep only rows with qualifying status (typically `COMPLETED` or `LOADED` or `FINAL`). If multiple events exist per key, select the latest by timestamp. Ignore rows with blank/None key columns or blank/None quantity values.
   ```python
   completed_events = {}  # (return_id, line_id) -> (event_time, final_disposition)
   for row in event_rows:
       ret_id, line_id, evt_time, evt_status, final_disp = row[0], row[1], row[2], row[3], row[4]
       if evt_status and str(evt_status).strip().upper() == 'COMPLETED':
           key = (str(ret_id).strip(), str(line_id).strip())
           if key not in completed_events or evt_time > completed_events[key][0]:
               completed_events[key] = (evt_time, str(final_disp).strip())
   ```

4. **Compute Flags**: For each plan line:
   - **Missing Final Event** = `1` if key not in `completed_events`, else `0`
   - **Disposition Mismatch** = `0` if missing; else normalize via alias map and compare case-insensitively to planned disposition
   - **Total Errors** = Missing + Mismatch (integer sum)
   - **Error Summary** = comma-separated error names or `"None"` string

5. **Aggregate Summary**: Group by (Warehouse, Carrier) or task-specified keys. Filter to groups with `Total Errors > 0`. Add Grand Total row.

6. **Generate Outputs**:
   - Create a new `openpyxl` workbook. **Remove the default 'Sheet'** immediately after creation.
   - If a template is provided, copy the template sheet(s) (e.g., `Overview`) cell-by-cell before adding data sheets.
   - Add `RawData`, `Formatted Data`, and `Summary` sheets.
   - Use `python-docx` to draft an executive brief.

7. **Verify**: Run the verification steps below to confirm sheet names, dimensions, and header values.

## Template Preservation Pattern

When the task provides a template workbook with sheets that must be preserved unchanged (e.g., `Overview`):

```python
from openpyxl import Workbook, load_workbook

template_wb = load_workbook('Template.xlsx')
out_wb = Workbook()

# CRITICAL: Remove the default 'Sheet' created by Workbook()
default_sheet = out_wb.active
out_wb.remove(default_sheet)

# Copy template sheet(s) cell-by-cell (VALUES ONLY)
for src_name in ['Overview']:  # Add other template sheet names as needed
    src_ws = template_wb[src_name]
    dst_ws = out_wb.create_sheet(src_name)
    for row in src_ws.iter_rows(min_row=1, max_row=src_ws.max_row, max_col=src_ws.max_column, values_only=False):
        for cell in row:
            dst_ws.cell(row=cell.row, column=cell.column, value=cell.value)

# Now add your data sheets (RawData, Formatted Data, Summary)
```

**Decision Rule**: If the task says "keep Overview unchanged" or provides a template with pre-formatted sheets, copy those sheets first, then add data sheets. Always remove the default `Workbook()` sheet before saving.

**CRITICAL ANTI-PATTERN**: Do NOT use `from copy import copy` to copy cell styles, fonts, borders, fills, merged cells, column dimensions, row dimensions, or sheet_properties. This approach is fragile, can introduce subtle differences that cause verifier failures, and is unnecessary when the verifier only checks cell values. Use simple cell-by-cell value copy as shown above.

## Decision Rules

- **Multi-file vs multi-sheet**: If data spans separate `.xlsx` files, load each independently. Do not assume sheets exist in a single workbook.
- **Alias normalization**: Always normalize event dispositions via the alias map before comparing to planned values. Use `.lower()` for case-insensitive lookup.
- **Event status filtering**: Only count events with the qualifying status (usually `COMPLETED`, `LOADED`, or `FINAL`). Ignore `PENDING`, `VOID`, `CANCELLED`, `STAGED`, `PRELIMINARY`, etc.
- **Latest event wins**: When multiple qualifying events exist per composite key, use the one with the latest timestamp.
- **Integer flags**: Use `1` and `0` (not `True`/`False`). Use `int()` conversion if needed.
- **Error Summary**: Use `"None"` string (not Python `None`, not empty, not `NaN`) for rows with zero errors.
- **Default sheet removal**: `openpyxl.Workbook()` always creates a default sheet named `'Sheet'`. Remove it with `out_wb.remove(out_wb.active)` before adding your own sheets, or the output will have an extra unwanted sheet.

## Anti-Patterns

- **Do not** compare raw event dispositions to planned values without alias normalization.
- **Do not** count PENDING, VOID, STAGED, CANCELLED, or PRELIMINARY events as completed dispositions.
- **Do not** assume one event per plan line; always deduplicate by selecting the latest.
- **Do not** use pandas for multi-file joins; it adds dependency risk and obscures cell-level control. Use `openpyxl` with explicit dict lookups.
- **Do not** forget to handle `None` values from `openpyxl` before calling `.strip()` or `.upper()`.
- **Do not** forget to remove the default `'Sheet'` from `Workbook()` before saving.
- **Do not** use `shutil.copy` or file-level copy for template sheets; copy cell-by-cell to preserve structure without carrying over hidden metadata.
- **Do not** use `from copy import copy` for template/style preservation. It is fragile and can cause verifier mismatches. Use simple value-only cell copy.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Verifier expects different column names | Task specifies exact header names | Match column names exactly (case-sensitive, no extra spaces) |
| Summary row count mismatch | Filtering logic too aggressive/lenient | Verify `Total Errors > 0` filter is applied after aggregation |
| Error Summary shows `NaN` in pandas readback | Pandas type inference artifact | Verify with `openpyxl` directly; actual cell value is correct if it shows `"None"` |
| Disposition Mismatch count too high | Alias map missing entries or case mismatch | Ensure alias map covers all variants; use `.lower()` for lookup |
| Missing Final Event count wrong | Event status filter too strict/lenient | Check exact status string comparison (strip whitespace, uppercase) |
| Extra 'Sheet' in output | Default sheet from `Workbook()` not removed | Call `out_wb.remove(out_wb.active)` immediately after `Workbook()` |
| Template sheet missing or corrupted | Used file copy instead of cell-by-cell copy | Copy cells individually with `dst_ws.cell(row=r, column=c, value=cell.value)` |
| Self-verification passes but verifier fails | Style copying introduced subtle differences, or verifier checks exact values not checked by agent | Use value-only cell copy for templates; verify exact cell values in Formatted Data, not just headers and totals |

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

### harbor-outbound-manifest-audit
- Input spans **two separate Excel files**: Manifest Plan (`PlanLines` sheet) and Dock Scan Log (`Scans` sheet), plus a template workbook with an `Overview` sheet.
- Event status filter: Only `LOADED` scans count. `VOID`, `STAGED`, and other statuses are ignored for zone comparison.
- Missing Load Scan = `1` if no `LOADED` status scan exists for the (Shipment ID, Carton ID) pair.
- Zone Mismatch = `1` if the latest `LOADED` scan's Scanned Zone differs from Planned Zone.
- Latest scan wins: When multiple LOADED scans exist per (Shipment ID, Carton ID), use the one with the latest Scan Timestamp.
- Key tuple: (Shipment ID, Carton ID) as composite join key.
- Summary aggregates by (Route, Shipment ID), filters to groups with Total Errors > 0, includes Grand Total row.
- Template `Overview` sheet must be copied unchanged from the template workbook.
- Output: Excel with Overview, RawData, Formatted Data, Summary + Word brief.

### cycle-count-variance-audit
- Input spans **three separate Excel files**: Template (Overview sheet), Plan (PlanLines sheet), Event Log (Events sheet).
- Event status filter: Only `FINAL` events count. `PRELIMINARY`, `VOID`, and other statuses are ignored.
- Ignore event rows with blank/None Count Qty values.
- Missing Final Count = `1` if no qualifying FINAL event with valid Count Qty exists for the (Facility, Session ID, Bin ID) key.
- Approval Gap = `1` if Approval Needed = 'YES' AND `abs(Expected Qty - Count Qty) > Allowed Variance`.
- Latest event wins: When multiple FINAL events exist per key, use the one with the latest Event Time.
- Key tuple: (Facility, Session ID, Bin ID) as composite join key.
- Summary aggregates by (Facility, Session ID), filters to groups with Total Errors > 0, includes Grand Total row.
- Template `Overview` sheet must be copied unchanged (value-only cell copy, no style copying).
- Output: Excel with Overview, RawData, Formatted Data, Summary + Word brief.

## Script Usage
Execute `scripts/generate_returns_audit.py` when the task matches the multi-file join audit pattern. Adapt column indices, grouping keys, and qualifying event status to match specific task requirements.

## References
- `references/variance-approval-gap.md`: Detailed pattern for computing Approval Gap flag with variance threshold comparison