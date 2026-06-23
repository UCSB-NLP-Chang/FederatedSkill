---
name: excel-inventory-coverage
description: Analyze Excel inventory workbooks (single or multiple files) to compute coverage, filter valid inbound shipments, and generate commit gap reports. Use when tasks involve calculating days-on-hand, projecting out-of-stock dates, and identifying delivery requirements from snapshot and arrival/booking feeds.
---

# Excel Inventory Coverage & Gap Analysis

## When to Use
- Input is one or more `.xlsx` files containing inventory snapshots and inbound arrival/booking/transfer feeds.
- Task requires calculating coverage gaps, filtering non-firm shipments, and outputting a structured gap report.
- **Do not** use generic text/`Read` tools on `.xlsx` files; they will fail. Use `openpyxl` via Python.

## Schema Adaptation
Sheet names, column headers, and file structures vary across tasks. Inputs may be a single multi-sheet workbook or split across multiple files.
1. **Inspect first**: Run a quick Python snippet to list sheet names and print row 1 headers for each file.
2. **Map dynamically**: Do not hardcode sheet names or column indices in reusable scripts unless the schema is guaranteed. Use header matching or explicit mapping per task.
3. **Multi-file handling**: If data is split across files, load each independently and merge logically by key (e.g., SKU, Branch+Item) before calculation.

## Core Workflow
1. **Load Workbook(s)**: Use `openpyxl.load_workbook()` in Python. Open in read-only mode to prevent source modification.
2. **Normalize Dates**: Immediately convert all date/datetime values to `datetime.date` before any comparisons or arithmetic. Mixing `datetime` and `date` types causes `TypeError`.
3. **Deduplicate Inbound/Transfers**: If the feed contains duplicate IDs or overlapping rows, keep the row with the latest date or most firm status before aggregation.
4. **Filter Inbound/Bookings**: Exclude rows with:
   - Blank SKU/Lane/Branch references
   - Non-firm states (`Draft`, `Tentative`, `Hold`, `Cancelled`, `Pending`)
   - Invalid or non-parseable ETA/Transfer dates
   - Dates strictly after `HorizonEnd`
5. **Calculate Coverage**:
   - `Days_On_Hand = Cases_On_Hand / Avg_Daily_Pull`
   - `Projected_OOS = AsOfDate + timedelta(days=Days_On_Hand)` (use `floor(Days_On_Hand)` for lane-snapshot variants)
   - `Remaining_Demand = Avg_Daily_Pull * PlanningDays`
   - `Additional_Needed = max(0, Remaining_Demand - (Cases_On_Hand + Valid_Inbound_Cases))`
   - `Pallets_Required = ceil(Additional_Needed / Cases_Per_Pallet)`
6. **Determine Delivery Urgency**: Compare `Required_Delivery_Date` (usually OOS date) against existing valid inbound ETAs. Set `Earlier_Delivery_Required = True` if no valid inbound exists or if the earliest valid ETA > Required Delivery Date.
7. **Generate Output**: Create a new `.xlsx` with a coverage sheet (metadata + key rows) and an actions/gap sheet (only rows with `Additional_Needed > 0`).

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs. Pass raw float values directly. The verifier's tolerance decides acceptable precision.

## Anti-Patterns & Troubleshooting
- **TypeError on date comparison**: `datetime.date` vs `datetime.datetime` raises `TypeError`. Always normalize to `.date()` immediately upon reading.
- **TypeError on date arithmetic**: `date + float` raises `TypeError`. Always wrap DOH in `timedelta(days=...)` before adding to a date.
- **Non-firm shipments**: Never count `Draft`, `Tentative`, `Hold`, or `Cancelled` toward firm coverage.
- **Blank/Invalid rows**: Skip rows where key identifiers are `None` or dates fail parsing.
- **Source modification**: Always open source workbooks in read-only mode or verify checksums post-run.

## Known Invariants (by Variant)

### rack-snapshot-booking-feed
- Input: Single workbook
- Sheet names: `Rack Snapshot`, `Booking Feed`, `Pallet Defaults`
- Key: `SKU_Ref` (single column)
- State column: `Booking State` (`Firm`/`Locked`/`Tentative`/`Hold`)
- Qualifying states: `Firm`, `Locked`
- Output sheets: `Rack_Coverage`, `Commit_Gap_Actions`
- AsOfDate in B1, HorizonEnd in D1

### lane-snapshot-arrival-board
- Input: Single workbook
- Sheet names: `Lane Snapshot`, `Arrival Board`
- Key: `(Lane, SKU)` composite
- State column: `Load Status` (`Ready`/`Docked`/`Draft`/`Cancelled`)
- Qualifying states: `Ready`, `Docked`
- Snapshot format: Grouped by lane with "Lane: XXXX" section headers
- Output sheets: `Lane_Coverage`, `Restock_Actions`
- Pallet size: fixed 54 cases
- `Projected_OOS_Date` MUST use `floor(Days_On_Hand)`

### branch-inventory-transfer-schedule
- Input: Two separate workbooks (Inventory/Stock, Transfer/Arrival Schedule)
- Key: `(Branch, Item)` composite
- State column: `Status` (`Confirmed`/`Tentative`/`Cancelled`)
- Qualifying states: `Confirmed`
- Deduplication: If duplicate Transfer IDs exist, keep the row with the latest date or confirmed status.
- Output sheets: `Branch_Item_Coverage`, `Transfer_Gap_List`
- Metadata: `AsOfDate` and `HorizonEnd` typically in row 1 of the inventory sheet.

## Execution
Run `scripts/calculate_coverage.py <input.xlsx> <output.xlsx>` for a deterministic baseline. Adjust column indices, sheet names, and file loading logic if the source schema varies or uses multiple files. Ensure `openpyxl` is installed (`pip install openpyxl`).