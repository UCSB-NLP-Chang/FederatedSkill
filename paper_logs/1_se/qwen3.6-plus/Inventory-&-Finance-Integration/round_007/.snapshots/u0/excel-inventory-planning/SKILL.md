---
name: excel-inventory-planning
description: Reads Excel workbooks for resource coverage planning (inventory, staffing, shifts, freshness/replenishment), calculates coverage days, shortage dates, incoming resources, palletization, and additional units needed. Generates formatted output workbooks. Use for supply chain inventory analysis, hospital staffing resilience, perishable goods freshness planning, or any Excel-based capacity/shortage calculation tasks.
---

# Excel Resource Coverage & Shortage Planning

## Environment Setup
- Modern Debian/Ubuntu environments enforce PEP 668. Install dependencies with:
  `pip install openpyxl --break-system-packages -q`
  Or use a virtual environment: `python3 -m venv .venv && source .venv/bin/activate && pip install openpyxl`

## Data Extraction Pattern
1. Load workbook: `wb = openpyxl.load_workbook(path, data_only=False)`
2. Inspect sheets: `wb.sheetnames`
3. Read headers and data carefully. Use `ws.max_column` (not `max_col`).
4. **Formula Handling**: `openpyxl` reads formulas as strings. Compute values manually in Python. Do not assume `data_only=True` will resolve formulas unless the file was previously saved with calculated values.
5. **Date Normalization**: Excel cells may contain `datetime.datetime`, `datetime.date`, or strings (`'2025-07-04'`). Normalize all dates to `datetime.date` before arithmetic or comparison. Use `date.fromisoformat(val)` for strings.
6. **Zero-Division Guard**: If `Daily_Rate` or `Daily_Required` is 0, coverage days and shortage dates are `None`. Handle gracefully to avoid `ZeroDivisionError`.
7. **Lookup Table Verification**: When reading small reference tables (e.g., `Boxes_Per_Pallet`), explicitly verify column indices. Do not assume A1/B1 layout; print headers first to avoid off-by-one column reads.

## Calculation Workflow
For each entity (SKU, Unit, Meal Kit, etc.), compute sequentially:
1. `Usable_Stock = Current_Stock - Expiring_Stock` (if freshness/expiry data exists)
2. `Current_Coverage = Usable_Stock / Daily_Rate` (handle 0 rate)
3. `Shortage_Date = AsOfDate + timedelta(days=math.floor(Current_Coverage))`
4. `Incoming_Total = Sum(incoming_units)` for deliveries where `Delivery_Date <= PlanningHorizonEnd`.
5. `Delivered_Coverage = (Usable_Stock + Incoming_Total) / Daily_Rate`
6. `Remaining_Demand = Daily_Rate * Remaining_Days_In_Horizon`
7. `Additional_Needed = max(0, Remaining_Demand - (Usable_Stock + Incoming_Total))`
8. `Units_Required = math.ceil(Additional_Needed / Unit_Size)` (e.g., pallets, crates, shift blocks)
9. `Earliest_Inbound_Date = Min(delivery dates for this entity within horizon)`
10. `Earlier_Delivery_Required = True` if `Earliest_Inbound_Date > Shortage_Date` or no inbound exists, else `False`
11. `Required_Start_Date = Shortage_Date` if earlier arrival required, else `AsOfDate + timedelta(days=math.floor(Delivered_Coverage))`

### Boolean Flags & Rounding
- `Rounding_Applied`: `True` if `math.ceil(Additional_Needed / Unit_Size) != (Additional_Needed / Unit_Size)`, else `False`. Verifiers often check this explicitly.
- `Earlier_Delivery_Required`: `True` if `Earliest_Inbound_Date` is after `Shortage_Date` or if no inbound exists.
- **Zero/None Handling**: If `Additional_Needed <= 0`, set `Units_Required = 0`, `Required_Start_Date = None`, `Rounding_Applied = False`, `Earlier_Delivery_Required = False`.

### Domain Mapping
- **Inventory**: `Current_Stock`=In_Stock_Cases, `Daily_Rate`=Daily_Rate, `Unit_Size`=Cases_Per_Pallet
- **Freshness/Perishables**: `Expiring_Stock`=Boxes_Expiring_By_Date, `Unit_Size`=Boxes_Per_Pallet
- **Staffing**: `Current_Stock`=Current_Staff_Hours, `Daily_Rate`=Daily_Required_Hours, `Unit_Size`=Hours_Per_Shift_Block
- **Maintenance/Parts**: `Current_Stock`=Current_Units, `Daily_Rate`=Daily_Consumption_Units, `Unit_Size`=Units_Per_Crate

## Output Generation
- Create new workbook with specified sheet names (e.g., `Unit_Results`, `Additional_Shipments_Needed`).
- Write metadata in top rows, headers at specified row index. Leave blank rows if required by layout.
- Populate data rows. Ensure booleans are Python `True`/`False` (openpyxl serializes to Excel `TRUE`/`FALSE`).
- Format dates as `YYYY-MM-DD` strings or `datetime.date` objects consistently.
- **Filtering**: The "Additional Needed" sheet typically excludes entities with `Units_Required == 0`.
- Save: `wb.save(output_path)`

## Verification & Troubleshooting
- **Structure Check**: Verify sheet names, header row index, column count, and data row count match requirements exactly.
- **Legacy Node Checks Failure**: If verifiers fail, verify:
  - Exact header string matches (case-sensitive, no trailing spaces).
  - Date serialization matches expected format (string vs datetime object).
  - Boolean values are not strings (`'TRUE'` vs `True`).
  - Numeric precision: round to 2 decimals if required, or keep full float.
  - Hidden rows/columns or merged cells in source/output.
- **Anti-Patterns**:
  - Do not use `ws.max_col` (use `max_column`).
  - Do not rely on `data_only=True` for formula resolution.
  - Do not assume all dates are `datetime` objects; handle string fallbacks with `date.fromisoformat()`.
  - **Date Arithmetic**: Always use `timedelta(days=N)` when adding/subtracting days from a `date` object. Direct `+ int` raises `TypeError`.
  - Avoid hardcoding row indices; locate headers dynamically when possible, but respect fixed-layout requirements if specified.
  - Run a lightweight structure validation script immediately after generation, before assuming correctness.
  - Always track `Rounding_Applied` boolean if `math.ceil` changes the value, as verifiers often check this explicitly.
  - **Inbound Filtering**: Only sum inbound deliveries that fall *on or before* the planning horizon end date. Deliveries after the horizon do not count toward coverage.
