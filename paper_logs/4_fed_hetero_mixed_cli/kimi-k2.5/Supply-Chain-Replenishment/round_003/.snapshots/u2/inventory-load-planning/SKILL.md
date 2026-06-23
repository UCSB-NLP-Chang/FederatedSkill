---
name: inventory-load-planning
description: Generate inventory load plans and replenishment schedules from Excel source data. Use for tasks involving days-on-hand calculations, projected stock-out dates, pallet requirements, or expedited delivery determination based on current inventory, sales velocity, and scheduled inbounds. Critical trigger when source files contain Dock_Status, Booking_State, or Status columns, or when output requires Delivered Days On Hand calculations. Applies to both warehouse floor inventory and rack-based storage scenarios.
---

# Inventory Load Planning

## Workflow

1. **Prepare Environment**
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install pandas openpyxl
   ```

2. **Inspect Source Structure**
   - Source files often have metadata rows before headers (AsOfDate, HorizonEnd)
   - If `pd.read_excel()` returns wrong columns, use `header=None` and inspect raw rows
   - Data typically starts 2-3 rows down with actual headers in row 2
   - Check for `Dock_Status`, `Booking_State`, or `Status` columns in inbound/arrivals sheets

3. **Parse with Robust Pattern**
   - See `references/formulas.md` for calculation specifications
   - Use `scripts/load_calculator.py` as a starting template, adapting column names
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
| Stock Snapshot | Rack Snapshot, Inventory Snapshot, Current Stock |
| Scheduled Inbounds | Booking Feed, Expected Arrivals, Inbound Shipments, Arrivals |
| Load Config | Pallet Defaults, Config, Parameters |

## Column Name Variations

Source files use varying terminology. Map these common synonyms:

| Concept | Common Column Names |
|---------|---------------------|
| Item Code | SKU, Item_Code, Product_ID, Material, SKU Ref |
| On Hand | On_Floor_Cases, Units_On_Hand, Cases_On_Hand, Current_Stock, Cases on Rack |
| Daily Rate | Daily_Sales, Daily_Rate, Sales_Velocity, Daily_Usage, Avg Daily Pull |
| Arrivals | Scheduled_Inbounds, Expected_Arrivals, Inbound_Shipments, Booking Feed |
| Arrival Date | Arrival_Date, Expected_Date, Dock_Date, ETA |
| Status | Dock_Status, Status, Shipment_Status, Confirm_Status, Booking_State |

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

```python
# Filter to reliable statuses before summing
if 'Dock_Status' in inbounds.columns:
    reliable = ['Committed', 'Arranged', 'Confirmed']
    inbounds = inbounds[inbounds['Dock_Status'].isin(reliable)]
elif 'Booking_State' in inbounds.columns:
    reliable = ['Firm', 'Locked']
    inbounds = inbounds[inbounds['Booking_State'].isin(reliable)]

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

- **Load_Detail / Rack_Coverage**: All items with full calculation trace
- **Load_Action_Summary / Commit_Gap_Actions**: Filtered view (typically where Additional_Needed > 0 or Pallets_Required > 0)

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

## Anti-Patterns

- **Don't assume headers are in row 0**: The trace showed headers at index 2 with metadata above
- **Don't include header strings in calculations**: Filter out rows containing "On Floor" or "Item Code" before math operations
- **Don't allow negative Additional Needed**: Always apply `max(0, ...)`
- **Don't compare string dates**: Convert to datetime first
- **Don't use `date.timedelta`**: Import as `from datetime import timedelta`, not `date.timedelta`
- **Don't assume column names match exactly**: Always inspect source files and map to semantic concepts (SKU vs Item_Code, etc.)
- **Don't sum all inbound rows without checking status**: Exclude tentative/pending shipments if status column exists
- **Don't forget data cleaning**: Null SKUs and invalid dates in source files will cause calculation errors
- **Don't use line continuation in shell -c**: Use heredoc (<< 'EOF') for multi-line Python commands

## Validation Steps

- Verify Additional Cases Needed never negative
- Confirm pallet calculations use `math.ceil()`, not `round()`
- Check Earlier Delivery Required compares datetime objects
- Validate items with sufficient inbound coverage show Earlier Delivery Required = False
- Verify status filtering applied if column present in source
- Confirm Delivered_Days_On_Hand calculation if required by output specification
- Check that null/None rows were filtered from inbound data before summing

## References

- `references/formulas.md` - Complete formula specification with examples
- `scripts/load_calculator.py` - Reusable implementation template (adapt column names)
