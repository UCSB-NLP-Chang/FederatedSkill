---
name: excel-route-dispatch-tracking
description: Processes route dispatch tracking workbooks from template files, grouped stock snapshots, and dispatch queues. Use when tasked with generating route/SKU coverage detail and dispatch plans while preserving template structure, resolving route aliases, deduplicating dispatches by revision, filtering by queue state, and computing per-route/SKU load requirements. Handles grouped stock layouts, alias map resolution, mixed row-type feeds, and metadata header rows in output sheets.
---

# Excel Route Dispatch Tracking & Coverage

## Overview
Transforms a template workbook, grouped stock snapshot, and dispatch queue into a populated route coverage tracker. Preserves unmodified template sheets, resolves route aliases, deduplicates dispatches by keeping the highest revision per Queue ID, filters by valid queue states, computes per-route/SKU coverage metrics, and writes SKU-specific load requirements.

## Workflow
1. **Preserve Template Structure**: Load the template workbook first. Record sheet names and order. Identify metadata/instruction sheets (e.g., `Overview`, `Pack Matrix`, `Route Alias Map`) vs calculation sheets (`Coverage_Detail`, `Dispatch_Plan`). Copy unmodified sheets exactly as-is to the output workbook.
2. **Parse Grouped Stock Snapshot**: Stock sheets often use section headers (e.g., `Route R-100`, `Zone: B`) in the first column to group items. Detect these headers, extract the canonical route/zone name, and assign it to subsequent data rows until the next header appears. Skip header rows during data extraction.
3. **Resolve Route Aliases**: If the dispatch queue uses shorthand aliases instead of canonical routes:
   - Locate the `Route Alias Map` or `Alias Key` sheet.
   - Build a lookup dict: `{alias: canonical_route}`.
   - Apply mapping to dispatch rows. Discard rows with unmapped aliases.
4. **Parse & Filter Dispatch Queue**:
   - **Filter Row Types**: Keep only `DISPATCH`, `SHIPMENT`, or `TRANSFER` rows. Ignore `COMMENT`, `NOTE`, `HEADER`, or blank types.
   - **Deduplicate by Revision**: Group by `Queue ID` / `Load ID`. Keep only the row with the **highest Revision number**. Discard lower revisions.
   - **Filter by State**: Valid states: `Released`, `Approved`, `Committed`, `Confirmed`, `Booked`, `Loaded`. Invalid: `Pending`, `Tentative`, `Cancelled`, `Hold`, `Draft`, `Rejected`.
   - **Validate Data**: Skip rows with blank SKUs or unparseable ship dates.
   - **Horizon Filter**: Only count dispatches with `ship_date <= horizon_end`.
5. **Compute Per-Route/SKU Metrics**:
   - `planning_days = (horizon_end - asof_date).days`
   - `days_oh = on_hand / daily_demand` (handle `daily_demand == 0` → set to `inf` or horizon+1)
   - `oos_date = asof_date + timedelta(days=days_oh)`
   - `inbound_cases = sum(cases for qualifying dispatches within horizon)`
   - `delivered_doh = (on_hand + inbound_cases) / daily_demand` (if `daily_demand > 0`)
   - `remaining_demand = daily_demand * planning_days`
   - `additional_needed = max(0, remaining_demand - (on_hand + inbound_cases))`
   - `loads_required = ceil(additional_needed / cases_per_load)` (use Route/SKU-specific config from Pack Matrix)
   - `earlier_delivery = True` if `inbound_cases == 0` or earliest qualifying dispatch date > `oos_date`
6. **Write Output Workbook**:
   - Maintain original template sheet order.
   - **Coverage_Detail**: Write metadata header rows first (`AsOfDate`, `HorizonEnd`, `PlanningDays`), then a blank row, then column headers, then data rows.
   - **Dispatch_Plan**: Filter to `loads_required > 0`. Write column headers then data rows.
   - Ensure dates are `YYYY-MM-DD` strings or Excel date objects. Ensure booleans are explicit.

## Anti-Patterns & Pitfalls
- **Overwriting Template Sheets**: Never delete or reorder sheets from the template. Copy them first, then overwrite only calculation sheets.
- **Ignoring Revision Dedup**: Multiple rows with same Queue ID but different revisions represent updates. Always keep highest revision; summing all rows double-counts.
- **Treating State as Status**: Dispatch queues use `Queue State` or `Stage`. Map accordingly and filter out `Draft`/`Pending`/`Tentative`.
- **Route/SKU Pairing**: Load configs and metrics are keyed on `(Route, SKU)`, not SKU alone. Always match on both dimensions.
- **Metadata Header Rows**: Coverage_Detail often has 3-4 metadata rows before the actual table headers. Write these explicitly; do not start data at row 1.
- **Date Arithmetic**: Always use `timedelta(days=int)` when adding to dates. Never add raw integers.
- **String Formatting Errors**: Avoid inline f-string format specifiers with conditional logic (e.g., `f"{val:.2f if val else 'N/A'}"`). Use explicit `if/else` blocks to prevent `ValueError`.

## Helper Script
Use `scripts/calculate_route_tracker.py` for deterministic processing. It handles template preservation, grouped stock parsing, alias resolution, revision dedup, state filtering, and metadata header rows.
Run: `python3 scripts/calculate_route_tracker.py <template.xlsx> <stock.xlsx> <queue.xlsx> <output.xlsx>`
⚠️ If column names deviate, adapt the `map_headers` targets or write inline following the workflow above.