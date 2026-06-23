---
name: multi-file-join-audit
description: Audits data across multiple Excel files using joins, alias normalization, and event status filtering. Use when input spans separate .xlsx files requiring cross-file lookups, value normalization via alias maps, status-based filtering, and computing missing/mismatch flags with summary aggregation.
---

# Multi-File Join Audit

## When to Use
- Input spans **multiple Excel files** (e.g., `Return_Plan.xlsx`, `Disposition_Event_Log.xlsx`, `Disposition_Alias.xlsx`)
- Task requires normalizing free-text disposition values via an alias/lookup table
- Event logs contain mixed statuses (COMPLETED, PENDING, VOID) and only specific statuses count
- Need to detect: (1) Missing Final Events (no qualifying event), (2) Disposition Mismatches (normalized != planned)

## Workflow

1. **Load All Input Files**: Use `openpyxl` to load each file separately. Do not use `read_file` on `.xlsx`.
   ```python
   plan_wb = openpyxl.load_workbook('Return_Plan.xlsx')
   event_wb = openpyxl.load_workbook('Disposition_Event_Log.xlsx')
   alias_wb = openpyxl.load_workbook('Disposition_Alias.xlsx')
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

3. **Filter & Deduplicate Events**: Keep only rows with qualifying status (typically `COMPLETED`). If multiple events exist per key, select the latest by timestamp.
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

6. **Generate Outputs**: Create Excel (`RawData`, `Formatted Data`, `Summary`) and Word executive brief. Follow the verification steps in `excel-audit-reporting` skill.

## Decision Rules

- **Multi-file vs multi-sheet**: If data spans separate `.xlsx` files, load each independently. Do not assume sheets exist in a single workbook.
- **Alias normalization**: Always normalize event dispositions via the alias map before comparing to planned values. Use `.lower()` for case-insensitive lookup.
- **Event status filtering**: Only count events with the qualifying status (usually `COMPLETED`). Ignore `PENDING`, `VOID`, `CANCELLED`, etc.
- **Latest event wins**: When multiple qualifying events exist per (Return ID, Line ID), use the one with the latest `Event Time`.
- **Integer flags**: Use `1` and `0` (not `True`/`False`). Use `int()` conversion if needed.
- **Error Summary**: Use `"None"` string (not Python `None`, not empty, not `NaN`) for rows with zero errors.

## Anti-Patterns

- **Do not** compare raw event dispositions to planned values without alias normalization.
- **Do not** count PENDING or VOID events as completed dispositions.
- **Do not** assume one event per plan line; always deduplicate by selecting the latest.
- **Do not** use pandas for multi-file joins; it adds dependency risk and obscures cell-level control. Use `openpyxl` with explicit dict lookups.
- **Do not** forget to handle `None` values from `openpyxl` before calling `.strip()` or `.upper()`.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Verifier expects different column names | Task specifies exact header names | Match column names exactly (case-sensitive, no extra spaces) |
| Summary row count mismatch | Filtering logic too aggressive/lenient | Verify `Total Errors > 0` filter is applied after aggregation |
| Error Summary shows `NaN` in pandas readback | Pandas type inference artifact | Verify with `openpyxl` directly; actual cell value is correct if it shows `"None"` |
| Disposition Mismatch count too high | Alias map missing entries or case mismatch | Ensure alias map covers all variants; use `.lower()` for lookup |
| Missing Final Event count wrong | Event status filter too strict/lenient | Check exact status string comparison (strip whitespace, uppercase) |

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

## Script Usage
Execute `scripts/generate_returns_audit.py` when the task matches the multi-file join audit pattern. Adapt column indices, grouping keys, and qualifying event status to match specific task requirements.

## Related Skills
- `excel-audit-reporting`: For single-file multi-sheet audit patterns (receipts, SLA, timesheets). Shares output format conventions and verification steps.
