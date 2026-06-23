---
name: excel-inventory-coverage
description: Analyze multi-sheet Excel inventory workbooks to compute rack/lane coverage, filter valid inbound shipments, and generate commit gap reports. Use when tasks involve calculating days-on-hand, projecting out-of-stock dates, and identifying pallet delivery requirements from snapshot and arrival/booking feeds.
---

# Excel Inventory Coverage & Gap Analysis

## When to Use
- Input is a multi-sheet `.xlsx` file containing inventory snapshots and inbound arrival/booking feeds.
- Task requires calculating coverage gaps, filtering non-firm shipments, and outputting a structured gap report.
- **Do not** use generic text/`Read` tools on `.xlsx` files; they will fail. Use `openpyxl` via Python.

## Schema Adaptation
Sheet names and column headers vary across tasks (e.g., `Rack Snapshot` vs `Lane Snapshot`, `Booking Feed` vs `Arrival Board`, `booking_state` vs `Load Status`).
1. **Inspect first**: Run a quick Python snippet to list sheet names and print row 1 headers.
2. **Map dynamically**: Do not hardcode sheet names or column indices in reusable scripts unless the schema is guaranteed. Use header matching or explicit mapping per task.

## Core Workflow
1. **Load Workbook**: Use `openpyxl.load_workbook()` in Python.
2. **Normalize Dates**: Immediately convert all date/datetime values to `datetime.date` before any comparisons.
3. **Filter Inbound/Bookings**: Exclude rows with:
   - Blank SKU/Lane references
   - Non-firm states (`Draft`, `Tentative`, `Hold`, `Cancelled`, `Pending`)
   - Invalid or non-parseable ETA dates
   - ETAs strictly after `HorizonEnd`
4. **Calculate Coverage**:
   - `Days_On_Hand = Cases_On_Hand / Avg_Daily_Pull`
   - `Projected_OOS = AsOfDate + timedelta(days=Days_On_Hand)`
   - `Remaining_Demand = Avg_Daily_Pull * PlanningDays`
   - `Additional_Needed = max(0, Remaining_Demand - (Cases_On_Hand + Valid_Inbound_Cases))`
   - `Pallets_Required = ceil(Additional_Needed / Cases_Per_Pallet)`
5. **Determine Delivery Urgency**: Compare `Required_Delivery_Date` (usually OOS date) against existing valid inbound ETAs. Set `Earlier_Delivery_Required = True` if no valid inbound exists or if the earliest valid ETA > Required Delivery Date.
6. **Generate Output**: Create a new `.xlsx` with a coverage sheet (metadata + SKU/Lane rows) and an actions/gap sheet (only rows with `Additional_Needed > 0`).

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Anti-Patterns & Troubleshooting
- **TypeError on date arithmetic**: `datetime.date + float` or `date + date` raises `TypeError`. Always wrap DOH in `timedelta(days=...)` before adding to a date.
- **Non-firm shipments**: Never count `Draft`, `Tentative`, `Hold`, or `Cancelled` toward firm coverage.
- **Blank/Invalid rows**: Skip rows where SKU/Lane is `None` or ETA fails parsing.
- **Source modification**: Always open source workbooks in read-only mode or verify checksums post-run to ensure no accidental writes.

## Known Invariants (by Variant)

### rack-snapshot-booking-feed
- Sheet names: `Rack Snapshot`, `Booking Feed`, `Pallet Defaults`
- Key: SKU_Ref (single column)
- State column: `Booking State` with values `Firm`/`Locked`/`Tentative`/`Hold`
- Qualifying states: Firm, Locked
- Output sheets: `Rack_Coverage`, `Commit_Gap_Actions`
- AsOfDate in Rack Snapshot B1, HorizonEnd in D1

### lane-snapshot-arrival-board
- Sheet names: `Lane Snapshot`, `Arrival Board`
- Key: (Lane, SKU) composite — Lane from section header, SKU from data row
- State column: `Load Status` with values `Ready`/`Docked`/`Draft`/`Cancelled`
- Qualifying states: Ready, Docked
- Snapshot format: Grouped by lane with "Lane: XXXX" section headers
- Output sheets: `Lane_Coverage`, `Restock_Actions`
- Pallet size: fixed 54 cases (no Pallet Defaults sheet)
- Projected_OOS_Date MUST use `floor(Days_On_Hand)` for this variant

## Execution
Run `scripts/calculate_coverage.py <input.xlsx> <output.xlsx>` for a deterministic baseline. Adjust column indices and sheet names in the script if the source schema varies. Ensure `openpyxl` is installed (`pip install openpyxl`).
