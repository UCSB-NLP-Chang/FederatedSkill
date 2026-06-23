---
name: inventory-load-planning
description: Calculate inventory load plans from stock snapshots and scheduled inbounds/bookings. Use when building OOS projections, pallet/load requirements, delivery schedules, or replenishment action summaries from Excel inventory data. Trigger on tasks involving stock snapshots, booking/recovery/transfer feeds, rack coverage, commit-gap analysis, inbound planning workbooks, branch transfer gap analysis, or template-based tracker refreshes.
---

# Inventory Load Planning

## Workflow

1. **Prepare Environment**
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install pandas openpyxl
   ```
   *Fallback*: If venv unavailable, use `pip install pandas openpyxl --break-system-packages`

2. **Inspect Source Structure**
   - Source files often have metadata rows before headers (AsOfDate, HorizonEnd)
   - Lane-based files have section headers like "Lane: COOLER-A" with embedded tables
   - Branch transfer files may have duplicate transfer IDs with different dates/statuses
   - Template workbooks have pre-populated sheets (Instructions, Pallet Guide) to preserve
   - If `pd.read_excel()` returns wrong columns, use `header=None` and inspect raw rows
   - Data typically starts 2-3 rows down with actual headers in row 2 or 3
   - Check for `Dock_Status`, `Booking_State`, `Load Status`, `Status`, or `Stage` columns in inbound/arrivals sheets

3. **Parse with Robust Pattern**
   - See `references/formulas.md` for calculation specifications
   - Use `scripts/load_calculator.py` as a starting template, adapting column names
   - For lane-section files, see Lane-Based Section Parsing below
   - For branch transfers with duplicate IDs, see Deduplication Rule below
   - For template workbooks, see Template Workbook Handling below
   - Adjust row indices based on your specific file structure

4. **Extract Parameters**: Read `AsOfDate`, `HorizonEnd`, compute `PlanningDays = (HorizonEnd - AsOfDate).days`. Extract `CasesPerPallet` (or `UnitsPerPallet`, `CasesPerLoad`) from config/pallet guide sheet.

5. **Deduplicate Transfer/Booking/Load IDs** (critical — do this FIRST before status filtering):

   **Date-based deduplication** (keep row with latest date):
   ```python
   transfers = transfers.sort_values(['Transfer_ID', 'Transfer_Date'], ascending=[True, False])
   transfers = transfers.drop_duplicates(subset=['Transfer_ID'], keep='first')
   ```

   **Revision-based deduplication** (if numeric Revision/Version column exists, keep highest revision):
   ```python
   transfers['Revision'] = pd.to_numeric(transfers['Revision'], errors='coerce')
   transfers = transfers.sort_values('Revision', ascending=False)
   transfers = transfers.drop_duplicates(subset=['Transfer_ID'], keep='first')
   ```

6. **Filter Inbounds/Bookings by Status** (critical step after dedup):
   - Check for status column: 'Dock Status', 'Booking State', 'Status', 'Load Status', 'Transfer Status', 'Stage'
   - Include confirmed statuses: `Committed`, `Arranged`, `Confirmed`, `Firm`, `Locked`, `Approved`, `Ready`, `Docked`, `In Transit`, `Booked`, `Loaded`
   - Exclude uncertain statuses: `Pending`, `Tentative`, `Planned`, `Proposed`, `Hold`, `Unconfirmed`, `Draft`, `Cancelled`
   - If no status column exists, include all inbounds
   - Exclude rows with missing grouping keys (blank Lane/Zone/SKU/Branch+Item)

7. **Clean Booking/Inbound Data**:
   - Skip rows with invalid/unparseable dates (text in date columns)
   - Skip rows with missing item references (blank SKU/Item_Code/Branch cells)
   - Skip metadata/note rows (planner notes, comment-only rows)

8. **Calculate per-item metrics** (preserve source order):
   - `cur_doh = on_floor / daily_sales`
   - `oos_date = as_of_date + timedelta(days=floor(cur_doh))`
   - `inbound_cases = sum(cases for qualifying inbounds where arrival_date <= horizon_end)`
   - `delivered_doh = (on_floor + inbound_cases) / daily_sales`
   - `remaining_demand = daily_sales * planning_days`
   - `additional = max(0, remaining_demand - on_floor - inbound_cases)`
   - `pallets = ceil(additional / cases_per_pallet)` if `additional > 0` else `0`
   - `req_date = oos_date` if `pallets > 0` else `None`
   - `earlier = True` if `pallets > 0` AND (`no qualifying inbounds exist` OR `earliest_qualifying_inbound > req_date`) else `False`

9. **Write Output**: Create output sheets matching template structure. If working from a template workbook, copy pre-populated sheets (Instructions, Pallet Guide) and fill computed sheets (Coverage, Actions).

10. **Verify**: Read back output. Spot-check 2-3 items manually. Ensure sheet order and item order match requirements.

## Deduplication Rule

When transfer/inbound data contains duplicate IDs (same Transfer_ID appearing multiple times):

```python
# DATE-BASED: Sort by Transfer_ID and Transfer_Date (latest first)
transfers = transfers.sort_values(['Transfer_ID', 'Transfer_Date'], ascending=[True, False])
transfers = transfers.drop_duplicates(subset=['Transfer_ID'], keep='first')
```

```python
# REVISION-BASED: If numeric Revision/Version column exists, keep highest revision
transfers['Revision'] = pd.to_numeric(transfers['Revision'], errors='coerce')
transfers = transfers.sort_values('Revision', ascending=False)
transfers = transfers.drop_duplicates(subset=['Transfer_ID'], keep='first')
```

**Order**: Deduplicate FIRST, then apply status filtering. Filtering first may discard the correct row.

## Template Workbook Handling

When the task provides a template workbook with pre-existing sheets to preserve:

```bash
python3 << 'EOF'
import openpyxl

# Load template
template = openpyxl.load_workbook('/path/to/template.xlsx')

# Create output workbook
wb = openpyxl.Workbook()

# CRITICAL: Remove openpyxl's default "Sheet"
wb.remove(wb.active)

# Copy static sheets from template (row-by-row cell copy)
for sheet_name in ['Instructions', 'Pallet Guide']:
    src_sheet = template[sheet_name]
    dst_sheet = wb.create_sheet(sheet_name)
    for row in src_sheet.iter_rows():
        for cell in row:
            dst_sheet.cell(row=cell.row, column=cell.column, value=cell.value)

# Create and populate computed sheets
coverage_sheet = wb.create_sheet('Coverage_Detail')
actions_sheet = wb.create_sheet('Recovery_Loads')
# ... populate with calculations ...

wb.save('/path/to/output.xlsx')
EOF
```

**Key invariant**: `openpyxl.Workbook()` always creates a default "Sheet". Remove it with `wb.remove(wb.active)` before saving.

## Earlier Delivery Logic — Out-of-Horizon Loads

**Critical distinction**: "Qualifying loads" for the `Earlier_Delivery_Required` check includes ALL reliable loads (Booked/Loaded/Confirmed) regardless of whether their arrival date falls within the planning horizon.

- `Inbound_By_Horizon` only counts loads with `arrival_date <= horizon_end`
- `Earlier_Delivery_Required` compares `Required_Delivery_Date` against the earliest arrival date among **ALL** qualifying loads (even those after horizon)

Example: A load arriving 2025-11-22 is excluded from inbound count when horizon ends 2025-11-20, but if it's the only qualifying load for a SKU, `Earlier_Delivery_Required` = TRUE when OOS date (e.g., 2025-11-14) is before 2025-11-22.

## Lane-Based Section Parsing

When source data is organized by lane/zone sections with embedded headers (common in produce lane scenarios):

```
Lane: COOLER-A
SKU               Cases    Daily Pull
PRD-APPLE         100      12
PRD-BANANA        40       8

Lane: COOLER-B
...
```

Parse by iterating rows and tracking current lane:

```python
lane_data = []
current_lane = None

for _, row in df.iterrows():
    val = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ''
    if val.startswith('Lane:'):
        current_lane = val.split(':', 1)[1].strip()
    elif val in ['SKU', 'nan', 'NaN'] or pd.isna(row.iloc[0]):
        continue  # Skip header rows and empty rows
    elif current_lane and pd.notna(row.iloc[0]):
        lane_data.append({
            'Lane': current_lane,
            'SKU': row.iloc[0],
            'Cases_On_Hand': pd.to_numeric(row.iloc[1], errors='coerce'),
            'Daily_Pull': pd.to_numeric(row.iloc[2], errors='coerce')
        })

stock_data = pd.DataFrame(lane_data)
stock_data = stock_data.dropna(subset=['SKU', 'Cases_On_Hand'])
```

## Shell Command Pattern

When running multi-line Python in shell, use heredoc to avoid escape character issues:

```bash
# CORRECT: Use heredoc for multi-line Python
python3 << 'EOF'
import openpyxl
wb = openpyxl.load_workbook('/path/to/file.xlsx')
print(wb.sheetnames)
EOF

# WRONG: Line continuation characters cause syntax errors
python3 -c "import openpyxl; wb = openpyxl.load_workbook('/path/file.xlsx'); \nfor sheet in wb.sheetnames:..."
```

## Composite Grouping Keys

When inventory data is keyed by multiple dimensions (e.g., Branch+Item, Zone+SKU, Aisle+Product), treat the **full composite key** as the grouping identifier for inbound aggregation. Do not aggregate by Item alone if the same Item appears in multiple Branches/Zones.

```python
# Group by composite key for inbound matching
transfers['group_key'] = transfers['Branch'].astype(str) + '|' + transfers['Item'].astype(str)
# Match stock rows using the same composite key
```

## Sheet Name Variations

Source files use varying terminology for sheets:

| Standard | Alternative Names |
|----------|-------------------|
| Stock Snapshot | Rack Snapshot, Inventory Snapshot, Current Stock, Lane Snapshot, Branch Stock |
| Scheduled Inbounds | Booking Feed, Expected Arrivals, Inbound Shipments, Arrivals, Arrival Board, Planned Transfers, Recovery Log |
| Load Config | Pallet Defaults, Config, Parameters, Pallet Guide |

## Column Name Variations

Source files use varying terminology. Map these common synonyms:

| Concept | Common Column Names |
|---------|---------------------|
| Item Code | SKU, Item_Code, Product_ID, Material, SKU Ref, Item |
| Lane/Zone | Lane, Location, Zone, Area, Branch |
| On Hand | On_Floor_Cases, Units_On_Hand, Cases_On_Hand, Current_Stock, Cases on Rack, Cases, Units, Stock_Units |
| Daily Rate | Daily_Sales, Daily_Rate, Sales_Velocity, Daily_Usage, Avg Daily Pull, Daily Pull, Daily Use, Daily_Use_Units_Per_Day |
| Arrivals | Scheduled_Inbounds, Expected_Arrivals, Inbound_Shipments, Booking Feed, Planned Transfers |
| Arrival Date | Arrival_Date, Expected_Date, Dock_Date, ETA, Transfer_Date, Load_Date |
| Quantity | Cases_Due, Units_Due, Expected_Quantity, Units_Planned, Transfer_Units, Units |
| Status | Dock_Status, Status, Shipment_Status, Confirm_Status, Booking_State, Load Status, Transfer Status, Stage |
| Transfer ID | Transfer_ID, Shipment_ID, Booking_ID, Load_ID |
| Revision | Revision, Version, Rev |

## Status Filtering Patterns

Many source files include status columns. Filter by reliable statuses before summing inbounds.

### Include statuses (reliable):
`Committed`, `Arranged`, `Confirmed`, `Firm`, `Locked`, `Approved`, `Ready`, `Docked`, `In Transit`, `Booked`, `Loaded`

### Exclude statuses (uncertain):
`Pending`, `Tentative`, `Planned`, `Proposed`, `Hold`, `Unconfirmed`, `Draft`, `Cancelled`

```python
CONFIRMED_STATUSES = {'Committed', 'Arranged', 'Confirmed', 'Approved', 'Firm', 'Locked', 'Ready', 'Docked', 'In Transit', 'Booked', 'Loaded'}
UNCERTAIN_STATUSES = {'Pending', 'Tentative', 'Planned', 'Proposed', 'Unconfirmed', 'Hold', 'Draft', 'Cancelled'}

# Filter to only confirmed inbounds
qualifying = inbounds[inbounds['Status'].isin(CONFIRMED_STATUSES)]
```

**Inference Rule**: If unfamiliar statuses appear, infer reliability from context. Words implying physical presence or finalization (`Ready`, `Docked`, `At Dock`, `In Transit`, `Confirmed`, `Booked`, `Loaded`) are safe to include. Words implying planning or uncertainty (`Draft`, `Planned`, `Tentative`, `Forecasted`, `Cancelled`) must be excluded.

## Data Quality Checks

Before calculations, clean the data to avoid errors:

```python
# Filter out rows with null/None SKU
inbounds = inbounds[inbounds['Item_Code'].notna()]

# Filter out rows with invalid dates
inbounds['Arrival_Date'] = pd.to_datetime(inbounds['Arrival_Date'], errors='coerce')
inbounds = inbounds[inbounds['Arrival_Date'].notna()]

# Ensure numeric columns are actually numeric
stock_data['On_Floor_Cases'] = pd.to_numeric(stock_data['On_Floor_Cases'], errors='coerce')
stock_data = stock_data[stock_data['On_Floor_Cases'].notna()]
```

## Core Calculation Sequence

1. **Days On Hand**: `On_Floor / Daily_Sales`
2. **Projected OOS**: `AsOfDate + floor(Days_On_Hand)`
3. **Planning Days**: `(HorizonEnd - AsOfDate).days`
4. **Remaining Demand**: `Daily_Sales * Planning_Days`
5. **Inbound by Horizon**: Filter inbounds where `Arrival_Date <= HorizonEnd` AND status is reliable
6. **Additional Needed**: `max(0, Remaining_Demand - On_Floor - Inbound_By_Horizon)`
7. **Pallets**: `ceil(Additional_Needed / Cases_Per_Pallet)` if `Additional_Needed > 0` else `0`
8. **Earlier Delivery Required**: `True` if `Pallets > 0` AND (`no qualifying inbounds exist` OR `earliest_all_qualifying_inbound > Required_Delivery_Date`) else `False`
9. **Delivered Days On Hand** (if required): `(On_Floor + Inbound_By_Horizon) / Daily_Sales`

## Output Structure

Output sheet names vary by task requirements. Confirm required names from task description:

- **Load_Detail / Rack_Coverage / Lane_Coverage / Branch_Item_Coverage / Coverage_Detail**: All items with full calculation trace
- **Load_Action_Summary / Commit_Gap_Actions / Restock_Actions / Transfer_Gap_List / Recovery_Loads**: Filtered view (typically where Additional_Needed > 0 or Pallets_Required > 0)

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### excel-inventory-load-planning (B1)
- Source workbook structure: metadata rows precede headers in Stock Snapshot sheet
- AsOfDate typically in row 0 column B; HorizonEnd in row 0 column D
- Data headers at row index 2; data rows start at row index 3+
- Scheduled Inbounds sheet: headers at row 0, data starts row 1
- Load Config sheet: CasesPerPallet at cell A2 (or similar)
- Output must have exactly two sheets: coverage sheet (first), action summary (second)
- Action summary includes only items where Additional_Cases_Needed > 0

### produce-lane-restock-gap (B1)
- Source: Lane Snapshot sheet with embedded lane headers ("Lane: COOLER-X")
- Metadata in first rows: AsOfDate row 0, HorizonEnd row 0 cols 2-3
- Arrivals: Arrival Board sheet with Load Status column (include Ready/Docked, exclude Draft/Cancelled)
- Output: Lane_Coverage (metadata header rows 1-4, data row 6+), Restock_Actions (filter Pallets_Required > 0)
- Required calculation: Delivered_Days_On_Hand
- Status filter critical: Draft/Cancelled arrivals must be excluded

### clinic-branch-transfer-gap (B1)
- Source: Branch Stock sheet (metadata row 0, headers row 2, data row 3+)
- Transfers: Planned Transfers sheet with potential duplicate Transfer_IDs
- Critical: Deduplicate transfers by keeping latest Transfer_Date per Transfer_ID before filtering
- Status column: Include "Confirmed", exclude "Tentative" and "Cancelled"
- Output: Branch_Item_Coverage (all branch-item combinations), Transfer_Gap_List (Pallets_Required > 0)
- Required calculation: Delivered_Days_On_Hand
- Planning unit: Units (not Cases)
- Composite key: Branch + Item

### frozen-meal-tracker (B1)
- Template workbook with pre-populated sheets (Instructions, Pallet Guide) to preserve
- Booking feed may have Revision column — deduplicate by highest revision before status filter
- Out-of-horizon loads still count for Earlier_Delivery_Required check
- Output: Instructions + Pallet Guide (copied) + Coverage_Detail + Recovery_Loads (computed)
- Remove openpyxl default "Sheet" before saving

## Anti-Patterns

- **Don't assume headers are in row 0**: The trace showed headers at index 2 with metadata above, or lane sections with embedded headers
- **Don't include header strings in calculations**: Filter out rows containing "On Floor" or "Item Code" before math operations
- **Don't allow negative Additional Needed**: Always apply `max(0, ...)`
- **Don't compare string dates**: Convert to datetime first
- **Don't mix date and datetime types**: Convert all dates to `datetime.date` or `pd.Timestamp` before arithmetic operations to avoid TypeError
- **Don't use `date.timedelta`**: Import as `from datetime import timedelta`, not `date.timedelta`
- **Don't assume column names match exactly**: Always inspect source files and map to semantic concepts (SKU vs Item_Code, etc.)
- **Don't sum all inbound rows without checking status**: Exclude tentative/pending/draft/cancelled shipments if status column exists
- **Don't forget data cleaning**: Null SKUs and invalid dates in source files will cause calculation errors
- **Don't ignore duplicate IDs**: When Transfer_ID appears multiple times, deduplicate to avoid double-counting
- **Don't use line continuation in shell -c**: Use heredoc (`<< 'EOF'`) for multi-line Python commands
- **Don't filter status before deduplication**: Deduplicate by latest date or highest revision FIRST, then filter by status. Filtering first may discard the correct row.
- **Don't aggregate by single key when composite is needed**: If data is keyed by Branch+Item or Zone+SKU, use the full composite key for inbound matching.
- **Don't forget to remove openpyxl default sheet**: `openpyxl.Workbook()` always creates a default "Sheet". Remove it before saving: `wb.remove(wb.active)` if `wb.active.title == "Sheet"`.
- **Don't confuse horizon-filtered inbound with all qualifying loads**: Inbound count only includes loads within horizon; earlier delivery check considers ALL qualifying loads regardless of date.

## Validation Steps

- Verify Additional Cases Needed never negative
- Confirm pallet calculations use `math.ceil()`, not `round()`
- Check Earlier Delivery Required compares datetime objects (not strings)
- Validate items with sufficient inbound coverage show Earlier Delivery Required = False
- Verify status filtering applied if column present in source (critical for Draft/Cancelled/Excluded exclusion)
- Confirm Delivered_Days_On_Hand calculation if required by output specification
- Check that null/None rows were filtered from inbound data before summing
- Verify lane/zone/branch identifiers correctly propagated to output
- Verify deduplication applied if duplicate IDs detected in source
- Confirm template workbook sheets preserved and default "Sheet" removed

## References

- `references/formulas.md` - Complete formula specification with examples, including lane section parsing and deduplication patterns
- `scripts/load_calculator.py` - Reusable implementation template (adapt column names)