---
name: inventory-load-planning
description: Calculate inventory load plans from stock snapshots and scheduled inbounds. Use when tasks involve days on hand, out-of-stock projections, pallet requirements, or determining if earlier deliveries are needed. Trigger phrases: "load plan", "stock balancing", "inventory planning", "days on hand", "OOS date", "pallets required", "pallet gap", "commit gap", "booking feed", "coverage analysis", "lane restock", "produce inventory", "location-based inventory", "branch transfer", "transfer gap", "clinic inventory", "warehouse replenishment", "recovery log", "revision deduplication", "template workbook", "alias key", "zone alias", "reference mapping", "route tracker", "dispatch plan", "dispatch queue", "route coverage", "loads required".
---

# Inventory Load Planning

Compute inventory metrics from stock data and scheduled inbounds, outputting a load plan with action items.

## When to Use

- Tasks requiring days on hand calculations
- Out-of-stock (OOS) date projections
- Determining additional cases or pallets/loads needed
- Identifying items requiring earlier delivery
- Creating load action summaries from stock snapshots
- Processing booking/commit/dispatch feeds with status filtering
- Multi-location inventory (lanes, zones, warehouses, branches, clinics, routes) where same SKU exists in multiple places
- Branch-to-branch transfer gap analysis
- Clinic or retail location replenishment planning
- Recovery logs or booking feeds with multiple revisions per load
- Template workbooks requiring selective sheet updates
- Feeds using aliases or alternate codes requiring lookup mapping

## Environment Setup

Before processing Excel files with Python:

1. **Install openpyxl** - Required for Excel I/O:
   ```bash
   pip install openpyxl --break-system-packages -q 2>/dev/null
   ```
   The `--break-system-packages` flag is needed in externally-managed Python environments (PEP 668, common in Debian/Ubuntu-based systems). If this fails, try `pip3 install openpyxl --user -q`.

2. **Verify installation** before proceeding with data processing.

## Input Data Structure

Expects source data with:
- **Stock Snapshot**: Item codes, current quantities, daily sales/consumption rates
- **Scheduled Inbounds/Booking Feed/Dispatch Queue/Transfers**: Item codes, arrival dates, quantities expected, status/state field
- **Load Config**: Cases per pallet (or cases per load for route-based planning)
- **Planning Horizon**: As-of date and horizon end date (often in header/metadata rows)
- **Alias Key (optional)**: Lookup table mapping aliases to canonical location/SKU names

### Column Name Variations
Source files may use different column naming conventions. Map as needed:
- Item identifier: `Item_Code`, `SKU_Ref`, `SKU`, `SKU Code`, `Item`
- Location identifier: `Lane`, `Zone`, `Location`, `Warehouse`, `Site`, `Branch`, `Clinic`, `Store`, `Route`
- Quantity on hand: `On_Floor_Cases`, `Units_On_Hand`, `On Hand`, `Stock_Level`, `Cases-on-Rack`, `Cases_On_Rack`, `Cases`, `Units`
- Consumption rate: `Daily_Sales`, `Daily_Rate`, `Daily_Usage`, `Daily_Demand`, `Avg_Daily_Pull`, `Avg_Daily_Pull_Cases`, `Daily_Pull`, `Daily Use`, `Daily_Use`, `Daily Demand`
- Inbound quantity: `Cases_Due`, `Cases_Expected`, `Units_Expected`, `Booked_Cases`, `Units`, `Units Planned`, `Transfer_Units`, `Cases`
- Status field: `Status`, `Booking_State`, `Booking State`, `State`, `Load Status`, `Stage`, `Release State`, `Queue State`
- Arrival date: `ETA`, `Arrival_Date`, `Expected_Date`, `Transfer Date`, `Transfer_Date`, `Load Date`, `Ship Date`
- Reference ID: `Transfer ID`, `Booking_ID`, `Load_ID`, `Shipment_ID`, `Dispatch Ref`, `Queue ID`
- Revision number: `Revision`, `Rev`, `Version`, `Revision No`
- Record type: `Record Type`, `Type`, `Record_Type`, `Row Type`

### Composite Keys and Multi-Location Inventory

When inventory is organized by location (lanes, zones, warehouses, branches, clinics, routes):
- **Composite key**: Use `Location + SKU` as the unique identifier, not SKU alone
- **Same SKU, multiple locations**: Treat each location-SKU pair as a separate item for planning
- **Inbound matching**: Match arrivals to inventory using both location and SKU fields
- **Output structure**: Include both Location and SKU columns in output sheets

Example: PRD-APPLE exists in both COOLER-A and COOLER-C with different stock levels and arrivals—calculate coverage separately for each lane-SKU pair.

## Core Calculations

1. **Current Days on Hand** = On_Floor_Cases / Daily_Sales
2. **Projected OOS Date** = AsOfDate + floor(Days_On_Hand)
3. **Inbound Cases By Horizon** = Sum of qualifying cases arriving on or before HorizonEnd for each item
4. **Delivered Days on Hand** = (On_Floor + Inbound_Cases) / Daily_Sales
5. **Remaining Demand Cases** = Daily_Sales × Planning_Days − On_Floor − Inbound_Cases
6. **Additional Cases Needed** = max(0, Remaining_Demand_Cases)
7. **Pallets Required** = ceil(Additional_Cases_Needed / Cases_Per_Pallet)
8. **Required Delivery Date** = Projected OOS Date (when stock runs out)
9. **Earlier Delivery Required** = Required_Delivery_Date < earliest_qualifying_inbound_date

### Cases Per Pallet / Cases Per Load / Units Per Pallet
- Common defaults: 40 cases/pallet (produce), 48-60 (general warehouse)
- **Per-SKU values**: Some workbooks provide a separate config sheet (e.g., "Pack Matrix") with cases-per-pallet or cases-per-load by location-SKU pair—use these values when available
- For route-based dispatch planning, use cases-per-load from a Pack Matrix or similar config
- For unit-based inventory (clinics, retail), may need to use units-per-pallet or units-per-box
- Always document the assumption in output metadata

## Status Filtering for Inbounds/Transfers/Dispatches

If inbound/booking/transfer/dispatch records include a status or state field, filter to include only qualifying statuses:

### Include (count toward inventory)
- Committed, Arranged, Confirmed, Tentative, Scheduled
- **Firm**, **Locked**
- **Ready**, **Docked** (arrivals in progress, confirmed at dock)
- **Booked**, **Loaded** (confirmed bookings and in-transit loads)
- **Released**, **Staged** (approved for delivery, staged at origin)
- **Approved** (dispatch approved, confirmed for shipment)

### Exclude (do not count)
- Pending, Cancelled, Draft, Hold
- **Draft** (unconfirmed, not yet scheduled)
- **Tentative** (when explicitly marked as unconfirmed/ignore in context)

**Note**: "Tentative" appears in both lists. Context matters—if a booking is explicitly marked to ignore (e.g., comment says "ignore"), exclude it. Otherwise, tentative bookings may be counted as soft commitments.

## Data Quality Handling

### Record Type Filtering

When feeds contain a Record Type or Row Type column (e.g., `DELIVERY`, `DISPATCH`, `MESSAGE`, `NOTE`, `COMMENT`):
- **Process only relevant types**: Typically `DELIVERY`, `DISPATCH`, or equivalent inbound/transfer types
- **Exclude non-data types**: `NOTE`, `MESSAGE`, `HEADER`, `COMMENT`, or similar annotation rows
- **Apply before other filtering**: Filter by record type first, then apply status, date, and SKU validation

### Alias Key / Reference Table Handling

When inbound feeds use aliases or alternate codes for locations/SKUs:
- **Load alias key first**: Read the alias mapping table before processing inbounds
- **Map before aggregation**: Translate aliases to canonical names before matching to inventory or aggregating
- **Unknown aliases**: Exclude records where the alias doesn't exist in the key table—do not create phantom locations
- **Multiple aliases per canonical**: One canonical zone may have multiple aliases (e.g., FRONT-A and ALPHA-1 both map to Z-01)
- **Example workflow**:
  1. Load alias key: `{FRONT-A: Z-01, ALPHA-1: Z-01, FRONT-B: Z-02}`
  2. For each inbound record, look up `Zone Alias` in key to get canonical zone
  3. If alias not found, exclude the record
  4. Use canonical zone for all subsequent calculations

### Revision-Based Deduplication

When booking feeds, dispatch queues, or recovery logs contain multiple revisions for the same load:
- **Identify duplicates**: Group by Load ID, Queue ID, or equivalent reference field
- **Keep highest revision**: For each ID, retain only the row with the highest Revision/Version number
- **Apply before status filtering**: Deduplicate first, then filter by status
- Example: Load L-9001 has revision 80 (Booked) and revision 90 (Loaded)—keep only revision 90

### Excel Formula Handling

When reading Excel files with openpyxl:
- **Formulas return strings**: Cells with formulas (e.g., `'=80*C2'`) return the formula string, not the calculated value
- **Calculate manually**: If a column contains formulas, derive the value from source columns instead (e.g., cases = pallets × cases_per_pallet)
- **Use data_only mode cautiously**: `openpyxl.load_workbook(filename, data_only=True)` returns cached values, but these may be stale or missing if the file wasn't saved by Excel with calculated values
- **Preferred approach**: Read the source values (pallets, cases_per_pallet from config) and calculate directly

### Date Parsing

Source files may contain mixed date formats:
- **datetime objects**: Excel serial dates converted by openpyxl to Python datetime
- **ISO strings**: 'YYYY-MM-DD' format strings
- **Handle both**: Check type and parse accordingly:
  ```python
  if isinstance(cell_value, datetime):
      date_val = cell_value.date()
  elif isinstance(cell_value, str):
      date_val = datetime.strptime(cell_value, '%Y-%m-%d').date()
  ```
- **Invalid dates**: Skip rows with unparseable dates (e.g., "bad-date", "TBD", empty strings)

### Invalid Dates
- Skip rows with unparseable dates (e.g., "bad-date", "TBD", empty strings)
- Log or note skipped rows for transparency

### Missing SKU or Location References
- Skip rows where the SKU/item reference is null, empty, or missing
- Skip rows where location field is required but null/empty (for multi-location inventory)
- Do not create placeholder items for orphaned bookings

### Mixed Data/Note Rows
- Some feeds contain planner notes or empty rows interspersed with data
- Filter to rows where all required fields (SKU, ETA/Ship Date, quantity, and Location if applicable) are present and valid
- Use Record Type/Row Type column if available to distinguish data rows from annotations

### Horizon Boundary
- Only count bookings/dispatches with ETA/Ship Date **on or before** HorizonEnd
- Bookings arriving after HorizonEnd should be excluded from Inbound_Cases_By_Horizon but noted if relevant for future planning

## Output Structure

### Load_Detail / Lane_Coverage / Branch_Coverage / Zone_Coverage / Route_Coverage / Coverage_Detail Sheet
- Metadata rows: AsOfDate, HorizonEnd, PlanningDays
- Per-item columns: Location/Route (if applicable), Item_Code/SKU, On_Floor_Cases/Units_On_Hand, Daily_Sales/Daily_Demand, Current_Days_On_Hand, Projected_OOS_Date, Inbound_Cases/Units_By_Horizon, Delivered_Days_On_Hand, Remaining_Demand_Cases/Units, Additional_Cases/Units_Needed, Pallets_Required/Loads_Required, Required_Delivery_Date, Earlier_Delivery_Required
- Optional useful columns: Rounding_Applied (TRUE if ceil() was used), Earliest_Scheduled_Inbound_Date (for Earlier_Delivery_Required context)

### Load_Action_Summary / Restock_Actions / Transfer_Gap_List / Dispatch_Gap_List / Dispatch_Plan Sheet
- Filter items where Pallets_Required/Loads_Required > 0
- Columns: Location/Route (if applicable), Item_Code/SKU, Required_Delivery_Date, Pallets_Required/Loads_Required, Additional_Cases/Units_Needed, Earlier_Delivery_Required

### Template Workbook Preservation

When updating a template workbook:
- **Preserve unchanged sheets**: Instructions, Overview, config sheets (e.g., Pallet Guide, Pack Matrix, Route Alias Map), and reference sheets should remain intact
- **Clear and repopulate calculation sheets**: Remove old data from coverage/action sheets before writing new results
- **Maintain sheet order**: Preserve original sheet order after updates
- **Read config from template**: Extract cases-per-pallet/load and other settings from template config sheets rather than hardcoding

## Implementation Notes

- Use `openpyxl` for Excel I/O
- Handle items with zero on-floor inventory (OOS date = AsOfDate)
- Handle items with no scheduled inbounds (inbound = 0)
- Handle items with only non-qualifying inbound statuses (inbound = 0 for calculation)
- Round days on hand to reasonable precision; use floor for OOS date calculation
- Compare required delivery date against earliest qualifying inbound date per item for earlier delivery flag
- Earlier_Delivery_Required should be False when no additional cases are needed (Pallets_Required = 0)
- For multi-location inventory, group output by location for readability
- Apply record type filtering first, then alias mapping, then revision deduplication, then status filtering

## Verification

After creating output:
1. Confirm both sheets exist with correct names
2. Verify all items from stock snapshot appear in Load_Detail/Lane_Coverage/Zone_Coverage/Coverage_Detail
3. Check Load_Action_Summary/Restock_Actions/Dispatch_Gap_List/Dispatch_Plan only contains items needing action (Pallets_Required/Loads_Required > 0)
4. Validate Earlier_Delivery_Required logic against scheduled inbound dates
5. Spot-check items with non-qualifying inbound statuses to ensure they show 0 inbound cases
6. Verify bookings with invalid dates or missing SKUs/locations were excluded (not counted)
7. Verify bookings after HorizonEnd were excluded from inbound totals
8. For multi-location: verify each location-SKU pair has its own row with correct totals
9. For template workbooks: verify preserved sheets (Overview, Instructions, config) remain unchanged
10. For revision-based feeds: verify only highest revision per Load/Queue ID was retained
11. For alias-based feeds: verify unknown aliases were excluded and canonical names used in output

## Common Pitfalls

- **Counting pending/hold/draft/cancelled bookings**: Verify status filtering logic excludes unconfirmed arrivals
- **Missing revision deduplication**: When Load/Queue IDs have multiple revisions, failing to deduplicate will double-count inventory
- **Skipping alias mapping**: When feeds use aliases, failing to map to canonical names will create phantom locations or fail to match inventory
- **Unknown alias handling**: Records with unrecognized aliases should be excluded, not crash the calculation
- **Invalid date handling**: Ensure date parsing catches edge cases; don't let bad dates crash the calculation
- **Column name mismatches**: Inspect source file structure before assuming column names
- **Date format handling**: Ensure dates are parsed correctly from Excel (may be datetime objects or strings)
- **Horizon boundary errors**: Double-check that bookings after HorizonEnd are excluded, not just after AsOfDate
- **Orphaned bookings**: Don't let bookings without valid SKUs or locations create phantom inventory items
- **Ignoring location in multi-location inventory**: When same SKU exists in multiple locations, treat each location-SKU as separate item; don't aggregate across locations unless explicitly required
- **Missing cases-per-pallet/load**: If not in source data, use reasonable default (40 for produce) and document assumption; prefer reading from Pack Matrix or config sheet when available
- **Binary Excel files**: The Read tool cannot read .xlsx files directly; use Python with openpyxl to inspect and process Excel files
- **Overwriting template sheets**: When updating template workbooks, explicitly preserve non-calculation sheets rather than replacing entire workbook
- **Processing non-delivery record types**: Filter by Record Type/Row Type before processing; MESSAGE/NOTE/COMMENT rows are not inbounds
- **Excel formula values**: When cells contain formulas like `=80*C2`, openpyxl returns the formula string, not the calculated value. Calculate manually from source columns or use data_only mode with caution.
- **Python package installation**: In externally-managed environments (PEP 668), use `--break-system-packages` flag or `--user` flag to install packages.