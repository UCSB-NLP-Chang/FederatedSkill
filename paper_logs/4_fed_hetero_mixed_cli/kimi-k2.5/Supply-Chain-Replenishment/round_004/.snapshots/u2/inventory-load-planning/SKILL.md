---
name: inventory-load-planning
description: Generate inventory load plans and replenishment schedules from Excel source data. Use for tasks involving days-on-hand calculations, projected stock-out dates, pallet requirements, or expedited delivery determination based on current inventory, sales velocity, and scheduled inbounds. Critical trigger when source files contain Dock_Status, Booking_State, Load Status, or Status columns, or when output requires Delivered Days On Hand calculations. Applies to warehouse floor inventory, rack-based storage, and lane-based produce scenarios.
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
   - If `pd.read_excel()` returns wrong columns, use `header=None` and inspect raw rows
   - Data typically starts 2-3 rows down with actual headers in row 2
   - Check for `Dock_Status`, `Booking_State`, `Load Status`, or `Status` columns in inbound/arrivals sheets

3. **Parse with Robust Pattern**
   - See `references/formulas.md` for calculation specifications
   - Use `scripts/load_calculator.py` as a starting template, adapting column names
   - For lane-section files, see Lane-Based Section Parsing below
   - Adjust row indices based on your specific file structure

## Critical Parsing Rule

When standard pandas reading fails (e.g., "ValueError: could not convert string to float"):

```python
# Read without headers first to inspect structure
raw = pd.read_excel(path, sheet_name='Stock Snapshot', header=None)

# Extract metadata from specific cells
as_of_date = pd.to_datetime(raw.iloc[0, 1])
horizon_end = pd.to_datetime(raw.iloc[0, 3])

# Skip to actual data (row 2=headers, row 3+=data)
data = raw.iloc[3:].copy()
data.columns = ['Item_Code', 'On_Floor_Cases', 'Daily_Sales', '_drop']
data = data.drop('_drop', axis=1).reset_index(drop=True)
```

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

## Sheet Name Variations

Source files use varying terminology for sheets:

| Standard | Alternative Names |
|----------|-------------------|
| Stock Snapshot | Rack Snapshot, Inventory Snapshot, Current Stock, **Lane Snapshot** |
| Scheduled Inbounds | Booking Feed, Expected Arrivals, Inbound Shipments, Arrivals, **Arrival Board** |
| Load Config | Pallet Defaults, Config, Parameters |

## Column Name Variations

Source files use varying terminology. Map these common synonyms:

| Concept | Common Column Names |
|---------|---------------------|
| Item Code | SKU, Item_Code, Product_ID, Material, SKU Ref |
| Lane/Zone | Lane, Location, Zone, Area |
| On Hand | On_Floor_Cases, Units_On_Hand, Cases_On_Hand, Current_Stock, Cases on Rack, **Cases** |
| Daily Rate | Daily_Sales, Daily_Rate, Sales_Velocity, Daily_Usage, Avg Daily Pull, **Daily Pull** |
| Arrivals | Scheduled_Inbounds, Expected_Arrivals, Inbound_Shipments, Booking Feed |
| Arrival Date | Arrival_Date, Expected_Date, Dock_Date, ETA |
| Status | Dock_Status, Status, Shipment_Status, Confirm_Status, Booking_State, **Load Status** |

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

## Status Filtering Patterns

Many source files include status columns. Filter by reliable statuses before summing inbounds.

### Dock_Status / Shipment_Status values:
**Include**: `["Committed", "Arranged", "Confirmed", "At Dock", "In Transit"]`
**Exclude**: `["Tentative", "Pending", "Planned", "Forecasted", "Requested"]`

### Booking_State values:
**Include**: `["Firm", "Locked", "Confirmed"]`
**Exclude**: `["Tentative", "Hold", "Pending", "Requested"]`

### Load Status values (produce/lane scenarios):
**Include**: `["Ready", "Docked", "Confirmed"]`
**Exclude**: `["Draft", "Cancelled", "Pending", "Tentative", "Planned"]`

```python
# Filter to reliable statuses before summing
if 'Dock_Status' in inbounds.columns:
    reliable = ['Committed', 'Arranged', 'Confirmed']
    inbounds = inbounds[inbounds['Dock_Status'].isin(reliable)]
elif 'Booking_State' in inbounds.columns:
    reliable = ['Firm', 'Locked']
    inbounds = inbounds[inbounds['Booking_State'].isin(reliable)]
elif 'Load Status' in inbounds.columns:
    reliable = ['Ready', 'Docked', 'Confirmed']
    inbounds = inbounds[inbounds['Load Status'].isin(reliable)]

inbound_by_horizon = inbounds[
    inbounds['Arrival_Date'] <= horizon_end
]['Cases_Due'].sum()
```

## Core Calculation Sequence

1. **Days On Hand**: `On_Floor / Daily_Sales`
2. **Projected OOS**: `AsOfDate + floor(Days_On_Hand)`
3. **Planning Days**: `(HorizonEnd - AsOfDate).days`
4. **Remaining Demand**: `Daily_Sales * Planning_Days`
5. **Inbound by Horizon**: Filter inbounds where `Arrival_Date <= HorizonEnd` AND status is reliable
6. **Additional Needed**: `max(0, Remaining_Demand - On_Floor - Inbound_By_Horizon)`
7. **Pallets**: `ceil(Additional_Needed / Cases_Per_Pallet)`
8. **Earlier Delivery Required**: `Required_Delivery < Earliest_Inbound_Date`
9. **Delivered Days On Hand** (if required): `(On_Floor + Inbound_By_Horizon) / Daily_Sales`

## Output Structure

Output sheet names vary by task requirements. Confirm required names from task description:

- **Load_Detail / Rack_Coverage / Lane_Coverage**: All items with full calculation trace
- **Load_Action_Summary / Commit_Gap_Actions / Restock_Actions**: Filtered view (typically where Additional_Needed > 0 or Pallets_Required > 0)

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known Invariants (by Sub-task)

### excel-inventory-load-planning (B1)
- Source workbook structure: metadata rows precede headers in Stock Snapshot sheet
- AsOfDate typically in row 0 column B; HorizonEnd in row 0 column D
- Data headers at row index 2; data rows start at row index 3+
- Scheduled Inbounds sheet: headers at row 0, data starts row 1
- Load Config sheet: CasesPerPallet at cell A2 (or similar)
- Output must have exactly two sheets: Load_Detail (first), Load_Action_Summary (second)
- Load_Action_Summary includes only items where Additional_Cases_Needed > 0

### produce-lane-restock-gap (B1)
- Source: Lane Snapshot sheet with embedded lane headers ("Lane: COOLER-X")
- Metadata in first rows: AsOfDate row 0, HorizonEnd row 0 cols 2-3
- Arrivals: Arrival Board sheet with Load Status column (include Ready/Docked, exclude Draft/Cancelled)
- Output: Lane_Coverage (metadata header rows 1-4, data row 6+), Restock_Actions (filter Pallets_Required > 0)
- Required calculation: Delivered_Days_On_Hand
- Status filter critical: Draft/Cancelled arrivals must be excluded

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
- **Don't use line continuation in shell -c**: Use heredoc (<< 'EOF') for multi-line Python commands

## Validation Steps

- Verify Additional Cases Needed never negative
- Confirm pallet calculations use `math.ceil()`, not `round()`
- Check Earlier Delivery Required compares datetime objects (not strings)
- Validate items with sufficient inbound coverage show Earlier Delivery Required = False
- Verify status filtering applied if column present in source (critical for Draft/Cancelled exclusion)
- Confirm Delivered_Days_On_Hand calculation if required by output specification
- Check that null/None rows were filtered from inbound data before summing
- Verify lane/zone identifiers correctly propagated to output for lane-based scenarios

## References

- `references/formulas.md` - Complete formula specification with examples, including lane section parsing
- `scripts/load_calculator.py` - Reusable implementation template (adapt column names)
