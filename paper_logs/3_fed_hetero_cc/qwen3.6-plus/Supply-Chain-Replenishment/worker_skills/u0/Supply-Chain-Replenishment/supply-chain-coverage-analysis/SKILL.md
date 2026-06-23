---
name: supply-chain-coverage-analysis
description: Build inventory coverage and gap analysis workbooks from multiple Excel sources. Use when tasks require calculating days-on-hand, out-of-stock projections, inbound reconciliation, and dispatch gap lists. Covers rack-snapshot + booking-feed, lane-snapshot + arrival-board, branch-stock + planned-transfers, zone-snapshot + feed + alias-map, route-snapshot + queue-export + template variants, and legacy ratio-based inventory + shipments + ratio-sheet format.
---

# Supply Chain Coverage Analysis

## When to Use
- Multi-sheet or multi-file Excel tasks that calculate inventory coverage and gap/replenishment reports
- Input: one or more workbooks with stock/snapshot data + inbound/booking/feed data (and optional alias map, template, or ratio sheet)
- Output: Excel with coverage sheet + gap/action list sheet

## Anti-Pattern: Read Tool on Binary Excel
The Read tool cannot read binary .xlsx files. **Always use Python with openpyxl.**

## Anti-Pattern: pip install without --break-system-packages
Modern Python environments (PEP 668) block system-wide pip installs. Use `pip install openpyxl --break-system-packages` if openpyxl is missing.

## Workflow
1. **Load Sources**: Read all input workbooks with `openpyxl.load_workbook(path, data_only=True)`.
2. **Parse Metadata**: Extract planning dates (AsOfDate, HorizonEnd) from designated cells. Compute `PlanningDays = (HorizonEnd - AsOfDate).days`.
3. **Build Alias Map** (if applicable): Map zone/branch/route aliases to canonical names. Skip unknowns — do not hard-fail.
4. **Process Inbound/Feed**:
   - Filter to valid record types only (e.g., `Record Type == 'DELIVERY'`, or `Row Type == 'DISPATCH'` for route variants).
   - Skip rows with blank SKU or invalid ETA/Ship Date.
   - Validate dates: handle `datetime`, `date`, or parse `%Y-%m-%d` strings. Skip invalid.
   - Deduplicate by dispatch/transfer/queue reference, keeping the highest revision/version.
   - Filter status/release state to only firm/confirmed values (variant-specific; see Known Invariants).
   - Resolve aliases via alias map. Skip unmapped.
   - Drop inbound where ETA/Ship Date > HorizonEnd.
5. **Calculate Coverage** (per Zone/SKU or Branch/Item or Lane/SKU or Route/SKU or SKU):
   - `Current_Days_On_Hand = On_Hand / Daily_Demand`
   - `Projected_OOS_Date = AsOfDate + timedelta(days=Current_Days_On_Hand)`
   - `Inbound_Units_By_Horizon = sum(Units for qualifying deliveries)`
   - `Delivered_Days_On_Hand = Inbound_Units / Daily_Demand`
   - `Remaining_Demand_Units = Daily_Demand * PlanningDays`
   - `Additional_Units_Needed = max(0, Remaining_Demand - On_Hand - Inbound_Units)`
   - `Pallets_Required = ceil(Additional_Units_Needed / LOAD_SIZE)` (variant-specific size; see Known Invariants)
   - `Required_Delivery_Date = Projected_OOS_Date` (cap at HorizonEnd if OOS exceeds it)
   - `Earlier_Delivery_Required = True` if `Pallets_Required > 0` and (`Inbound_Units == 0` or earliest inbound ETA > `Required_Delivery_Date`)
6. **Generate Output**: Create workbook with coverage sheet (metadata + all rows) and gap list sheet (rows where `Additional_Units_Needed > 0` or `Pallets_Required > 0`). For template-based variants, refresh existing sheets and preserve unchanged sheets.
7. **Verify**: Ensure source files are unmodified. Read back output to validate.

## Anti-Patterns & Validation
- **Do not** process non-delivery/non-dispatch record types (MESSAGE, NOTE, COMMENT, etc.).
- **Do not** include non-firm release states (Pending, Hold, Draft, Cancelled, ignore) in coverage.
- **Always** deduplicate by dispatch/transfer reference BEFORE filtering by release state or horizon.
- **Validate dates rigorously**: Excel may return strings like `"bad-date"`. Catch parse errors and skip.
- **Check alias mapping**: Unmapped aliases must be excluded, not hard-failed.
- **Preserve source files**: Read-only access for inputs.
- **Do not** use pandas — rely on openpyxl exclusively.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Script Usage
- **Zone variant (B4)**: Run `python3 scripts/build_replenishment.py <stock.xlsx> <feed.xlsx> <alias.xlsx> <output.xlsx>` — implements filtering, dedup, alias resolution, and coverage math with fixed 36/pallet.
- **Route variant (B5)**: Run `python3 scripts/refresh_route_tracker.py <route_snapshot.xlsx> <queue_export.xlsx> <template.xlsx> <output.xlsx>` — implements section-based route parsing, Pack Matrix lookup for variable load sizes, queue dedup, and template-preserving output.
- **Legacy/Ratio variant (B6)**: Run `python3 scripts/build_legacy_coverage.py <inventory.xlsx> <output.xlsx>` — implements ratio-sheet load size lookup, formula-cell handling via data_only=True, and output with Rounding_Applied + Earliest_Scheduled_Inbound_Date columns.

## Known invariants (by sub-task)

### B1: rack-snapshot + booking-feed
- Output sheets: Rack_Coverage + Restock_Actions
- Dedup key: Booking reference
- Valid booking states: Confirmed only (exclude Tentative, Hold)
- Data rows start at row 4+ (metadata in rows 1-3)
- Load size: 36 units/pallet
- Common failure: counting Tentative/Hold as firm; datetime.datetime vs datetime.date TypeError

### B2: lane-snapshot + arrival-board
- Output sheets: Lane_Coverage + Restock_Actions
- Parse section-based lane snapshot (Lane headers + SKU/Cases/DailyPull rows)
- Aggregate by (Lane, SKU) composite key — NOT by SKU alone
- Valid arrival states: exclude Draft, Cancelled
- Load size: 36 units/pallet
- Common failure: aggregating by SKU alone; missing section-header parsing

### B3: branch-stock + planned-transfers
- Output sheets: Branch_Item_Coverage + Transfer_Gap_List
- Deduplicate by Transfer ID (keep max date) BEFORE filtering status
- Filter Status=Confirmed only (exclude Tentative)
- Aggregate by (Branch, Item) composite key — NOT by Item alone
- Load size: 36 units/pallet
- Common failure: filtering before dedup; including Tentative; aggregating by Item alone

### B4: zone-snapshot + feed + alias-map
- Output sheets: Zone_Coverage + Dispatch_Gap_List
- Three input workbooks (stock, feed, alias map)
- Filter Record Type == 'DELIVERY' only (exclude MESSAGE, NOTE)
- Dedup by Dispatch_Ref keeping highest Revision
- Valid release states: 'Released', 'Staged' only (exclude Pending, Hold, ignore)
- Resolve Zone Alias via alias map; skip unmapped zones
- ETA <= HorizonEnd required
- Load size: 36 units/pallet
- Common failure: including MESSAGE/NOTE record types; missing Revision dedup; including Pending release state; unmapped alias hard-fail instead of skip

### B5: route-snapshot + queue-export + template
- **Input**: Three workbooks: Route Snapshot (section-based), Queue Export, Template (with Pack Matrix + Route Alias Map)
- **Output sheets**: Coverage_Detail + Dispatch_Plan (refresh within template)
- **Preserve unchanged**: Overview, Pack Matrix, Route Alias Map sheets
- **Route Snapshot parsing**: Section headers like "Route R-100" in column A; track current_route state
- **Queue Export columns**: Row Type, Dispatch Ref, Revision No, Route Alias, SKU Code, Ship Date, ETA Cases, Queue State
- **Row Type filter**: `Row Type == 'DISPATCH'` only — exclude COMMENT and all other types
- **Dedup**: By Dispatch Ref (Queue ID) keeping highest Revision No
- **Queue State filter**: Only 'Released' or 'Approved' — exclude Pending, Draft, ignore
- **Alias resolution**: Route Alias Map in template; skip unmapped routes
- **Ship Date validation**: Must be valid date <= HorizonEnd
- **Variable load size**: Lookup Cases_Per_Load from Pack Matrix by (Route, SKU) key — NOT fixed pallet size
- **Coverage calculation**: Uses Cases_Per_Load from Pack Matrix for `Loads_Required = ceil(Additional_Needed / Cases_Per_Load)`
- Common failure: hard-coding cases-per-load instead of Pack Matrix lookup; wrong Row Type filter (DISPATCH vs all); wrong state filter (Released/Approved vs Released/Staged); creating new workbook instead of refreshing template

### B6: legacy inventory + shipments + ratio sheet
- **Trigger**: Input workbook has sheets named 'Current Inventory', 'Incoming Shipments', and 'Ratio' (or similar legacy naming)
- **Input**: Single workbook with three sheets:
  - 'Current Inventory': Metadata in row 1 ("Today's Date" at B1, "Month End" at D1), headers at row 3 (Product SKU, In Stock (cases), Rate of Sale (cases/day)), data from row 4
  - 'Incoming Shipments': Headers at row 1 (Product SKU, Delivery Date, Number of Pallets, Number of Cases Left), data from row 2. Cases column contains formulas like `=80*C2` — **must use data_only=True**
  - 'Ratio': Cases-per-pallet at A2 (e.g., 80)
- **Output sheets**: SKU_Results + Additional_Shipments_Needed
- **Metadata labels**: AsOfDate, PlanningHorizonEnd, RemainingDaysInJuly (or variant month name)
- **Column names**: Product_SKU, Current_Cases, Daily_Rate_Cases_Per_Day, Current_DOH, Projected_OOS_Date, Inbound_Cases_By_Horizon, Delivered_DOH_To_Horizon, Remaining_Demand_Cases, Additional_Cases_Needed, Pallets_Required_Rounded_Up, Required_Delivery_Date, Rounding_Applied, Earlier_Delivery_Required, Earliest_Scheduled_Inbound_Date
- **Load size**: Read from Ratio sheet A2 (NOT hardcoded)
- **Rounding_Applied**: `True` if `Additional_Cases_Needed % LOAD_SIZE != 0`, else `False`
- **Earliest_Scheduled_Inbound_Date**: Earliest delivery date for that SKU (even if before AsOfDate); include in both output sheets
- **Gap list filter**: All rows where `Pallets_Required_Rounded_Up > 0`
- **Common failure**: Hard-coding 36 instead of reading Ratio sheet; not using data_only=True (getting formula strings instead of computed cases); missing Rounding_Applied or Earliest_Scheduled_Inbound_Date columns; wrong metadata labels
