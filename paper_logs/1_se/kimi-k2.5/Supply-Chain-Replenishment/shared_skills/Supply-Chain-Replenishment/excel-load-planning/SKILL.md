---
name: excel-load-planning
description: Create supply chain load planning workbooks from Excel source data. Use when task involves reading multi-sheet .xlsx files with stock snapshots, scheduled inbounds/transfers, and config data; calculating days-on-hand, out-of-stock dates, and pallet requirements; and generating Load_Detail and Load_Action_Summary outputs. Handles standard supplier inbound, lane-based structures, and branch/transfer variants. Trigger phrases: 'load plan', 'days on hand', 'DOH', 'OOS date', 'pallet calculation', 'inventory planning', 'pallet gap', 'midmonth analysis', 'rack coverage', 'booking feed', 'commit gap', 'lane coverage', 'restock actions', 'produce planning', 'branch transfer', 'clinic inventory', 'transfer schedule', 'inter-branch transfer', 'incoming shipments', 'shipment needs', 'additional shipments', 'pallet requirement'.
---

# Excel Load Planning

Create load planning workbooks from source Excel data with stock positions, inbound shipments or transfers, and planning parameters.

## Workflow

1. **Discover source structure with Python**
   - Use `openpyxl` - direct Read tool fails on binary .xlsx
   - List all sheet names: `wb.sheetnames`
   - Identify sheets by content pattern matching, not hardcoded names:
     - Stock/Inventory: Look for columns like SKU, Item, On Hand, Units, Daily Rate, Sales, Branch
     - Inbounds/Arrivals/Bookings/Transfers/Shipments: Look for Arrival Date, Delivery Date, Transfer Date, Expected Date, Cases, Units, Status, Booking State
     - Config/Pallet Guide/Ratio: Look for Cases Per Pallet, Pallet Size, Cases-Pallet ratio
   - **Check for hierarchical structures**: Look for 'Lane:', 'Section:', 'Zone:' prefixes indicating grouped data
   - **Check for branch-level structures**: Look for 'Branch' column or 'Branch: XXX' headers
   - Inspect first 10 rows of each sheet to locate headers and metadata dates

2. **Extract planning parameters**
   - AsOfDate and HorizonEnd: Check cells B1, D1, A2, or scan for date patterns
   - Cases_Per_Pallet: Usually in Config/Pallet Guide/Ratio sheet, cell A2 or B2, or as Cases/Pallet columns
   - Header rows: Often row 3 or 4 (not row 1)
   - PlanningDays = (HorizonEnd - AsOfDate).days

3. **Determine variant type**
   - **Standard**: Match on SKU only
   - **Lane/Zone**: Match on (Lane, SKU) composite key
   - **Branch/Transfer**: Match on (Branch, SKU) composite key; source is transfers not supplier inbound

4. **Handle hierarchical stock data (Lane/Zone variants)**
   - Detect 'Lane: XXXX' or similar headers in column 1
   - Track current lane context until next lane header encountered
   - Build composite key: (Lane, SKU) not just SKU
   - Lane headers often have empty cells in other columns

5. **Handle branch-level stock data (Branch/Transfer variants)**
   - Identify Branch column in stock sheet (often column 0 or named 'Branch', 'Location', 'Site')
   - Build composite key: (Branch, SKU) for matching to transfers
   - Branch may be separate column or embedded in item identifier

6. **Filter inbound/transfers by status (if status column exists)**
   - **Critical**: Check for 'Status', 'Dock Status', 'Booking State', 'Load Status' or similar columns
   - **If no status column present**: Skip status filtering, include all rows (validate by inspecting headers)
   - **Only include**: 'Committed', 'Arranged', 'Confirmed', 'Approved', 'Firm', 'Locked', 'Ready', 'Docked'
   - **Exclude**: 'Tentative', 'Pending', 'Draft', 'Proposed', 'Cancelled', 'Hold'
   - Also filter by Arrival_Date <= HorizonEnd
   - For Lane variants: filter by Lane in addition to SKU
   - See `references/variant_patterns.md` for status terminology by industry variant

7. **Handle transfer deduplication (Branch/Transfer variants)**
   - Transfers often have duplicate Transfer IDs with different dates/status
   - **Deduplication rule**: Keep the row with latest Transfer_Date per Transfer_ID
   - Apply deduplication BEFORE status filtering
   - See `references/variant_patterns.md` for deduplication patterns

8. **Handle data quality issues (critical for reliable results)**
   - **Null/empty SKU rows**: Skip rows where SKU is None or empty string
   - **Null/empty Lane rows** (Lane variants): Skip where Lane is None but data present
   - **Null/empty Branch rows** (Branch variants): Skip where Branch is None
   - **Invalid dates**: Skip rows where date parses as string, is None, or raises exception
   - **Missing SKUs with valid data**: Log warning but exclude from calculations (cannot attribute to stock)
   - **Malformed rows**: Skip rows with Comment like 'planner note row' or entirely None values
   - **Date after horizon**: Exclude bookings with Arrival_Date > HorizonEnd
   - **Zero or negative cases**: Treat as 0 for that row

9. **Calculate per-item metrics**
   - Current_Days_On_Hand = On_Floor / Daily_Sales (handle zero sales: use 1 or skip)
   - Projected_OOS_Date = AsOfDate + Current_Days_On_Hand days
   - Inbound_Units_By_Horizon = sum(Units where Status in ALLOWED and Arrival_Date <= HorizonEnd)
   - For Lane variants: match on (Lane, SKU) composite key
   - For Branch variants: match on (Branch, SKU) composite key
   - Delivered_Days_On_Hand = (On_Floor + Inbound_Units) / Daily_Sales
   - Remaining_Demand = Daily_Sales * PlanningDays
   - Additional_Units_Needed = max(0, Remaining_Demand - On_Floor - Inbound_Units_By_Horizon)
   - Pallets_Required = ceil(Additional_Units_Needed / Cases_Per_Pallet)
   - Earlier_Delivery_Required = TRUE if no ALLOWED inbound arrives before Projected_OOS_Date

10. **Build output sheets**
    - **SKU_Coverage/Load_Detail/Rack_Coverage/Lane_Coverage/Branch_Item_Coverage**: All items with full calculated fields
    - **Pallet_Gap_List/Load_Action_Summary/Commit_Gap_Actions/Restock_Actions/Transfer_Gap_List**: Filter to Pallets_Required > 0
    - Include metadata header with Field/Value pairs for AsOfDate, PlanningHorizonEnd, PlanningDays

11. **Verify calculations**
    - Check OOS dates are within or immediately after horizon
    - Confirm Earlier_Delivery_Required correctly identifies gaps without pre-OOS committed inventory
    - Validate pallet counts use ceiling division
    - Spot-check: Items with zero inbound or all pending status should show Earlier_Delivery_Required=TRUE
    - Verify data quality exclusions didn't drop valid rows (check row counts)
    - For transfers: verify deduplication didn't lose intended data

## Common Variant Patterns

| Pattern | Typical Location | Notes |
|---------|-----------------|---------|
| Stock data | 'Current Stock', 'Stock Snapshot', 'Rack Snapshot', 'Current Inventory' | Metadata dates in row 1, headers row 3-4 |
| Inbound data | 'Expected Arrivals', 'Scheduled Inbounds', 'Booking Feed', 'Incoming Shipments' | Status/Booking State column critical for filtering (if present) |
| Transfer data | 'Planned Transfers', 'Transfer Schedule', 'Inter-Branch' | Has Transfer_ID, requires deduplication |
| Config | 'Pallet Guide', 'Load Config', 'Pallet Defaults', 'Ratio' | Cases_Per_Pallet often cell A2 or Cases/Pallet columns |
| Units vs Cases | Header names | Treat synonymously; check which term source uses |
| **Lane variant** | 'Lane Snapshot', 'Lane: XXX' headers | Hierarchical: lane → SKU groups; composite (Lane,SKU) key |
| **Branch variant** | 'Branch Stock', 'Site Inventory' | Composite (Branch,SKU) key; transfer-based inbound |

## Data Quality Patterns

| Issue | Detection | Handling |
|-------|-----------|----------|
| Null SKU | `row[0] is None or row[0] == ''` | Skip row, log if debug mode |
| Null Lane (Lane variants) | `row[lane_col] is None` | Skip row (unattributable) |
| Null Branch (Branch variants) | `row[branch_col] is None` | Skip row (unattributable) |
| Invalid date | `isinstance(date_val, str)` or parse exception | Skip row |
| Missing SKU with data | SKU column None but cases/status present | Skip (unattributable) |
| Planner notes | 'Comment' column contains 'planner note' | Skip row |
| Status after horizon | `arrival_date > horizon_end` | Exclude from sum |
| Duplicate Transfer_ID | Same ID, different dates | Keep latest date per ID |

## Output Column Patterns

Common boolean/flag columns to include:
- **Rounding_Applied**: True when Pallets_Required required ceiling rounding
- **Earlier_Delivery_Required**: True when no qualifying inbound arrives before OOS date

## Anti-patterns
- **Do not** assume sheet names - discover and match by content
- **Do not** ignore status columns on inbound/transfer data - this causes false negatives; but also **do not** fail if status column absent
- **Do not** use direct file Read on .xlsx - always use Python libraries
- **Do not** hardcode date ranges - extract from source metadata
- **Do not** use floor division for pallets - always round up partial pallets
- **Do not** assume all rows are valid - data quality issues are common in booking feeds
- **Do not** miss hierarchical structures - 'Lane:' headers change parsing logic
- **Do not** skip data quality validation - silent errors propagate to wrong pallet calculations
- **Do not** forget transfer deduplication - duplicate Transfer IDs are common

## Troubleshooting
- **Dates not found**: Scan row 1-3 for datetime objects; may be labeled 'AsOfDate', 'Snapshot Date', 'Planning Start', 'Today's Date'
- **All items showing Earlier_Delivery_Required=FALSE**: Check status filtering - may be including tentative arrivals, or status column may not exist
- **Zero pallets calculated for obvious gaps**: Verify status filter is excluding Pending/Tentative; check if status column absent
- **Dates parse as datetime**: Convert with `.date()` before string formatting or calculations
- **Item code mismatches**: Verify exact string matching (case-sensitive) between stock and inbound sheets
- **Missing expected gaps in output**: Check if data quality filters are too aggressive; verify null SKU handling
- **Wrong pallet counts**: Ensure `math.ceil()` not `int()` or `round()` for pallet calculation
- **Lane data not matching**: Ensure composite (Lane, SKU) key used, not SKU alone
- **Branch data not matching**: Ensure composite (Branch, SKU) key used; verify deduplication applied
- **Module not found errors**: Use `--break-system-packages` if pip install fails due to externally-managed-environment

## Scripts
- `scripts/generate_load_plan.py` - Reusable generator; pass `--sheet-hints` for variant structures
- See `references/variant_patterns.md` for tested configurations, status terminology by variant, hierarchical data handling, and transfer deduplication
- See `references/formulas.md` for calculation reference

## Fallback Strategy
If calculations don't match expected results:
1. **Check data quality first** - most common source of errors
   - Verify null SKU rows aren't being counted
   - For Lane variants: verify null Lane rows excluded
   - For Branch variants: verify deduplication and null Branch handling
   - Confirm invalid date rows are excluded
   - Check for hidden rows with planner notes
2. Re-examine inbound/transfer status column - may use 'Booking State', 'Load Status' not 'Status'; may be **absent entirely**
3. Verify header row location (common: row 3 or 4, not 1)
4. Check if Cases_Per_Pallet uses different cell in this file variant, or is in 'Ratio' sheet
5. **For Lane variants**: Confirm composite key matching (Lane, SKU) vs SKU-only
6. **For Branch variants**: Confirm deduplication logic and composite (Branch, SKU) matching
7. Ensure datetime vs date handling is consistent
