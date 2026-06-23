---
name: excel-load-planning
description: Generates inventory load plans, commit gap analyses, and rack/lane coverage reports from source Excel workbooks containing stock snapshots, booking feeds, and pallet configs. Use when tasked with calculating days on hand, out-of-stock dates, pallet requirements, delivery urgency flags, or filtering inbound/booking/transfer statuses. Handles dynamic sheet layouts, grouped/hierarchical data, status filtering, type-safe parsing, column synonym mapping, zone/location alias resolution, mixed-record-type feeds, formula-based case calculations, and ratio sheet lookups.
---

# Excel Load Planning & Inventory Balancing

## Overview
Transforms raw DC/branch inventory or booking/transfer data into a structured load plan or gap analysis workbook. Reads stock levels, inbound/booking/transfer schedules, and pallet configs, then computes projected stockouts, additional case needs, pallet counts, and delivery urgency flags.

## Workflow
1. **Inspect & Map Sheets Dynamically**: Do not hardcode sheet names or cell addresses. Scan workbook for sheets containing keywords (`Stock`, `Snapshot`, `Current`, `Rack`, `Lane`, `Inventory`), (`Inbound`, `Arrival`, `Schedule`, `Booking`, `Feed`, `Transfer`), (`Config`, `Guide`, `Pallet`, `Defaults`, `Ratio`). Read headers dynamically to map columns.
2. **Map Column Synonyms**: Source workbooks vary widely. Map headers to logical fields using synonyms:
   - `SKU` ↔ `Item`, `Product`, `Code`, `Part`, `SKU Code`, `Product SKU`
   - `OnFloor` ↔ `Units`, `Stock`, `Qty`, `OnHand`, `On Hand`, `In Stock (cases)`, `Current_Cases`
   - `Daily` ↔ `DailyUse`, `Rate`, `Consumption`, `AvgDaily`, `Daily Demand`, `Rate of Sale (cases/day)`
   - `Lane` ↔ `Branch`, `Location`, `Zone`, `Aisle`, `Zone Alias`
   - `Inbound` ↔ `Transfer`, `Booking`, `Shipment`, `Expected`
   - `Status` ↔ `Stage`, `Release State`, `Dock Status`, `Load Status`, `Booking State`
   - `Pallets` ↔ `Number of Pallets`, `Pallet_Count`, `Loads`
   - `Cases` ↔ `Number of Cases`, `Cases_Left`, `Units`
3. **Handle Formula Cells in Inbound Sheets**: Inbound sheets often contain formulas (e.g., `=80*C2`) instead of pre-calculated values. When `data_only=True` returns `None` for the cases column:
   - Check if a `Pallets` column exists and contains numeric values.
   - Look for a `Ratio`, `Conversion`, or `Config` sheet defining `cases_per_pallet`.
   - Compute `cases = pallets * cases_per_pallet`.
   - ⚠️ Never rely on `data_only=True` alone for formula cells; always validate and compute fallback.
4. **Read Ratio/Conversion Sheets**: If cases are not directly provided:
   - Scan for sheets named `Ratio`, `Conversion`, `Config`, `Pallet Guide`.
   - Look for key-value pairs like `Cases: 80, Pallet: 1` or headers `Cases | Pallet` with values `80 | 1`.
   - Default to 40 if no ratio found and cases column is missing.
5. **Handle Alias Key Workbooks**: If the feed uses aliases (e.g., `FRONT-A`, `ALPHA-1`) instead of canonical zones/locations:
   - Look for a separate workbook or sheet named `Alias Map`, `Alias Key`, `Zone Mapping`, `Location Map`.
   - Build a lookup dict: `{alias: canonical_zone}`.
   - Apply mapping after reading feed rows. Discard rows with aliases not in the map.
6. **Handle Mixed-Record-Type Feeds**: If the feed has a `Record Type` or `Type` column:
   - Filter to only `DELIVERY`, `SHIPMENT`, `TRANSFER`, or `INBOUND` records.
   - Ignore `NOTE`, `MESSAGE`, `HEADER`, `COMMENT`, or blank record types.
7. **Handle Grouped/Hierarchical Layouts**: If the inventory sheet uses section headers (e.g., `Lane: COOLER-A`, `Zone: B`) in the first column to group items, parse these headers to assign a `Lane`/`Zone` key to subsequent rows until the next header appears. Skip the header rows during data extraction.
8. **Extract Parameters**:
   - Locate `today_date` (AsOfDate) and `horizon_end` by scanning config/snapshot sheets for labels like `Today's Date`, `Month End`, `AsOfDate`, `HorizonEnd`.
   - `planning_days = (horizon_end - today_date).days`
   - Find `cases_per_pallet` in config/guide/ratio sheet (default to 40 if missing).
9. **Parse Stock & Inbounds Safely**:
   - Skip header/section rows by validating data types (e.g., SKU column should be string, quantity columns numeric).
   - **Deduplicate Conflicting Records**: If the same transfer/booking ID appears multiple times with different statuses or dates, prioritize the highest-confidence status (`Confirmed`/`Committed` > `Tentative`/`Pending`) or the latest valid date. Sum only qualifying records.
   - For inbounds/bookings/transfers, check for a `Status`, `Dock Status`, `Load Status`, `Booking State`, or `Release State` column.
   - **Valid Statuses**: `Committed`, `Arranged`, `Confirmed`, `Firm`, `Locked`, `Ready`, `Docked`, `Released`, `Staged`.
   - **Invalid Statuses**: `Pending`, `Tentative`, `Cancelled`, `Hold`, `Draft`, `Rejected`.
   - Filter inbounds to `arrival_date <= horizon_end`.
   - Match inbounds to stock using `(Lane/Branch, SKU/Item)` if a location column exists, otherwise match on `SKU` alone.
10. **Compute Per-Item Metrics**:
    - `days_oh = on_floor / daily_sales` (guard against `daily_sales == 0` → set to `inf` or horizon+1)
    - `oos_date = today_date + timedelta(days=days_oh)` (⚠️ Use `timedelta`, never add raw integers to dates)
    - `inbound_cases = sum(cases for qualifying inbounds)`
    - `total_demand = daily_sales * planning_days`
    - `additional_needed = max(0, total_demand - (on_floor + inbound_cases))`
    - `pallets = ceil(additional_needed / cases_per_pallet)`
    - `rounding_applied = (additional_needed / cases_per_pallet) != pallets` (True if fractional pallets required)
    - `earlier_delivery = True` if `inbound_cases == 0` or earliest qualifying inbound arrives after `oos_date`
11. **Generate Output Workbook**: Create two sheets:
    - `SKU_Results` (or `Lane_Coverage`, `Branch_Item_Coverage`, `Rack_Coverage`, `Zone_Coverage`): Write metadata header rows first (`AsOfDate`, `PlanningHorizonEnd`/`HorizonEnd`, `RemainingDaysInJuly`/`PlanningDays`), then a blank row, then column headers, then data rows. Standard columns: `Product_SKU`, `Current_Cases`, `Daily_Rate_Cases_Per_Day`, `Current_DOH`, `Projected_OOS_Date`, `Inbound_Cases_By_Horizon`, `Delivered_DOH_To_Horizon`, `Remaining_Demand_Cases`, `Additional_Cases_Needed`, `Pallets_Required_Rounded_Up`, `Required_Delivery_Date`, `Rounding_Applied`, `Earlier_Delivery_Required`, `Earliest_Scheduled_Inbound_Date`.
    - `Additional_Shipments_Needed` (or `Restock_Actions`, `Transfer_Gap_List`, `Pallet_Gap_List`, `Dispatch_Gap_List`): Filtered to `pallets > 0`. Columns: `Product_SKU`, `Required_Delivery_Date`, `Pallets_Required_Rounded_Up`, `Additional_Cases_Needed`, `Rounding_Applied`, `Earlier_Delivery_Required`.
12. **Verify**: Cross-check a sample item. Ensure dates are `YYYY-MM-DD` ISO strings, booleans are native `True`/`False`, numerics are `int`/`float`, and no type errors during arithmetic.

## Anti-Patterns & Pitfalls
- **Hardcoded Layouts**: Source workbooks vary widely. Always map headers to indices dynamically. Scan for labels instead of assuming `A2`, `B1`, etc.
- **Formula Cells Returning None**: When using `data_only=True`, openpyxl returns `None` for uncalculated formulas. Always validate cases columns and compute from pallets * ratio if None.
- **Grouped Layouts as Flat Tables**: Failing to detect section headers causes `TypeError` or misaligned data. Check if the first column contains repeating category labels before parsing.
- **Ignoring Inbound/Booking Status**: Not all scheduled inbounds are reliable. Filter out `Pending`/`Tentative`/`Hold`/`Draft`/`Cancelled` unless explicitly instructed otherwise.
- **Division by Zero**: Handle `daily_sales == 0` gracefully. Set `days_oh` to a large number or horizon limit, and flag for review.
- **Date Arithmetic Errors**: `datetime.date + int` raises `TypeError`. Always use `datetime.timedelta(days=int)` when adding days to a date object.
- **Single-Key Matching**: When lanes/branches/zones are present, matching inbounds on `SKU` alone causes cross-contamination. Always match on `(Location, SKU)` if the location dimension exists.
- **Ignoring Alias Resolution**: Feeds often use shorthand aliases. Always check for a separate alias key workbook or sheet. Discard rows with unmapped aliases.
- **Processing Non-Delivery Records**: Mixed feeds contain notes, messages, or headers. Filter by `Record Type` before processing.
- **Invalid Dates in Feeds**: Feeds may contain malformed dates (`bad-date`, blank, text). Parse dates safely and skip rows with unparseable ETAs.
- **Blank SKUs**: Skip feed rows where SKU is `None`, blank, or non-string.
- **Rounding_Applied Always True**: Only set `Rounding_Applied = True` when `additional_needed / cases_per_pallet` has a fractional part. Do not hardcode to True.

## Helper Script
Use `scripts/calculate_load_plan.py` for deterministic, reusable calculation logic. It dynamically detects sheets, handles grouped/hierarchical layouts, filters inbounds by status, handles formula-based case calculations, reads ratio sheets, and writes the formatted workbook.
Run: `python3 scripts/calculate_load_plan.py <source.xlsx> <output.xlsx>`
⚠️ If the task involves **alias key resolution** or **mixed-record-type feeds**, the base script may need adaptation. Either:
1. Pre-process the feed to resolve aliases and filter record types before passing to the script, or
2. Extend the script's `map_headers` and inbound parsing logic to handle `Record Type` filtering and alias lookup.
⚠️ If column names deviate significantly from standard inventory terms, adapt the `map_headers` targets or write a custom inline script following the workflow above.