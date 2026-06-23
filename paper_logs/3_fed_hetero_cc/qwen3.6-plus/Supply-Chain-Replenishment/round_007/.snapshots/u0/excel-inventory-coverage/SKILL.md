---
name: excel-inventory-coverage
description: Build zone-based inventory coverage and gap analysis workbooks from multiple Excel sources. Use when tasks require calculating days-on-hand, out-of-stock projections, inbound reconciliation, and dispatch gap lists with alias resolution. Covers rack-snapshot + booking-feed, lane-snapshot + arrival-board, branch-stock + planned-transfers, and zone-snapshot + feed + alias-map variants.
---

# Excel Inventory Coverage

## When to Use
- Multi-sheet or multi-file Excel tasks that calculate inventory coverage and gap/replenishment reports
- Input: one or more workbooks with stock/snapshot data + inbound/booking/feed data (and optional alias map)
- Output: Excel with coverage sheet + gap/action list sheet

## Anti-Pattern: Read Tool on Binary Excel
The Read tool cannot read binary .xlsx files. **Always use Python with openpyxl.**

## Workflow
1. **Load Sources**: Read all input workbooks with `openpyxl.load_workbook(path, data_only=True)`.
2. **Parse Metadata**: Extract planning dates (AsOfDate, HorizonEnd) from designated cells. Compute `PlanningDays = (HorizonEnd - AsOfDate).days`.
3. **Build Alias Map** (if applicable): Map zone/branch aliases to canonical names. Skip unknowns — do not hard-fail.
4. **Process Inbound/Feed**:
   - Filter to valid record types only (e.g., `Record Type == 'DELIVERY'`).
   - Skip rows with blank SKU or invalid ETA.
   - Validate ETA: handle `datetime`, `date`, or parse `%Y-%m-%d` strings. Skip invalid.
   - Deduplicate by dispatch/transfer reference, keeping the highest revision/version.
   - Filter status/release state to only firm/confirmed values (e.g., `'Released'`, `'Staged'`, `'Confirmed'` — exclude `'Pending'`, `'Hold'`, `'Draft'`, `'Cancelled'`, `'ignore'`).
   - Resolve aliases via alias map. Skip unmapped.
   - Drop inbound where `ETA > HorizonEnd`.
5. **Calculate Coverage** (per Zone/SKU or Branch/Item or Lane/SKU):
   - `Current_Days_On_Hand = On_Hand / Daily_Demand`
   - `Projected_OOS_Date = AsOfDate + timedelta(days=Current_Days_On_Hand)`
   - `Inbound_Units_By_Horizon = sum(Units for qualifying deliveries)`
   - `Delivered_Days_On_Hand = Inbound_Units / Daily_Demand`
   - `Remaining_Demand_Units = Daily_Demand * PlanningDays`
   - `Additional_Units_Needed = max(0, Remaining_Demand - On_Hand - Inbound_Units)`
   - `Pallets_Required = ceil(Additional_Units_Needed / PALLET_SIZE)` (variant-specific size)
   - `Required_Delivery_Date = Projected_OOS_Date` (cap at HorizonEnd if OOS exceeds it)
   - `Earlier_Delivery_Required = True` if `Pallets_Required > 0` and (`Inbound_Units == 0` or earliest inbound ETA > `Required_Delivery_Date`)
6. **Generate Output**: Create workbook with coverage sheet (metadata + all rows) and gap list sheet (rows where `Additional_Units_Needed > 0` or `Pallets_Required > 0`).
7. **Verify**: Ensure source files are unmodified. Read back output to validate.

## Anti-Patterns & Validation
- **Do not** process non-delivery record types (MESSAGE, NOTE, etc.).
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

## Script Usage (zone-snapshot + feed + alias-map variant)
Run `python3 scripts/build_replenishment.py <stock.xlsx> <feed.xlsx> <alias.xlsx> <output.xlsx>` for the 3-workbook zone variant. It implements filtering, dedup, alias resolution, and coverage math. Adjust pallet size constant if task specifies differently.

## Known invariants (by sub-task)

### B1: rack-snapshot + booking-feed
- Output sheets: Rack_Coverage + Restock_Actions
- Dedup key: Booking reference
- Valid booking states: Confirmed only (exclude Tentative, Hold)
- Data rows start at row 4+ (metadata in rows 1-3)
- Common failure: counting Tentative/Hold as firm; datetime.datetime vs datetime.date TypeError

### B2: lane-snapshot + arrival-board
- Output sheets: Lane_Coverage + Restock_Actions
- Parse section-based lane snapshot (Lane headers + SKU/Cases/DailyPull rows)
- Aggregate by (Lane, SKU) composite key — NOT by SKU alone
- Valid arrival states: exclude Draft, Cancelled
- Common failure: aggregating by SKU alone; missing section-header parsing

### B3: branch-stock + planned-transfers
- Output sheets: Branch_Item_Coverage + Transfer_Gap_List
- Deduplicate by Transfer ID (keep max date) BEFORE filtering status
- Filter Status=Confirmed only (exclude Tentative)
- Aggregate by (Branch, Item) composite key — NOT by Item alone
- Common failure: filtering before dedup; including Tentative; aggregating by Item alone

### B4: zone-snapshot + feed + alias-map
- Output sheets: Zone_Coverage + Dispatch_Gap_List
- Three input workbooks (stock, feed, alias map)
- Filter Record Type == 'DELIVERY' only (exclude MESSAGE, NOTE)
- Dedup by Dispatch_Ref keeping highest Revision
- Valid release states: 'Released', 'Staged' only (exclude Pending, Hold, ignore)
- Resolve Zone Alias via alias map; skip unmapped zones
- ETA <= HorizonEnd required
- Pallet size: 36 units/pallet
- Common failure: including MESSAGE/NOTE record types; missing Revision dedup; including Pending release state; unmapped alias hard-fail instead of skip
