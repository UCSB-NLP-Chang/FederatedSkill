---
name: excel-inventory-planning
description: Reads Excel workbooks for resource coverage planning (inventory, staffing, shifts), calculates coverage days, shortage dates, incoming resources, and additional units needed. Generates formatted output workbooks. Use for supply chain inventory analysis, hospital staffing resilience, or any Excel-based capacity/shortage calculation tasks.
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
5. **Date Normalization**: Excel cells may contain `datetime.datetime`, `datetime.date`, or strings (`'2025-07-04'`). Normalize all dates to `datetime.date` before arithmetic or comparison.
6. **Zero-Division Guard**: If `Daily_Rate` or `Daily_Required` is 0, coverage days and shortage dates are `None`. Handle gracefully to avoid `ZeroDivisionError`.

## Calculation Workflow
For each entity (SKU, Unit, etc.), compute sequentially:
1. `Current_Coverage = Current_Stock / Daily_Rate` (handle 0 rate)
2. `Shortage_Date = AsOfDate + timedelta(days=math.floor(Current_Coverage))`
3. `Incoming_Total = Sum(incoming_units)` for deliveries within planning horizon.
4. `Delivered_Coverage = (Current_Stock + Incoming_Total) / Daily_Rate`
5. `Remaining_Demand = Daily_Rate * Remaining_Days_In_Horizon`
6. `Additional_Needed = Remaining_Demand - (Current_Stock + Incoming_Total)`
7. `Units_Required = math.ceil(Additional_Needed / Unit_Size)` (e.g., pallets, shift blocks)
8. `Earliest_Inbound_Date = Min(delivery dates for this entity)`
9. `Earlier_Arrival_Required = True` if `Earliest_Inbound_Date > Shortage_Date`, else `False`
10. `Required_Start_Date = Shortage_Date` if earlier arrival required, else `AsOfDate + timedelta(days=math.floor(Delivered_Coverage))`

### Domain Mapping
- **Inventory**: `Current_Stock`=In_Stock_Cases, `Daily_Rate`=Daily_Rate, `Unit_Size`=Cases_Per_Pallet
- **Staffing**: `Current_Stock`=Current_Staff_Hours, `Daily_Rate`=Daily_Required_Hours, `Unit_Size`=Hours_Per_Shift_Block

## Output Generation
- Create new workbook with specified sheet names (e.g., `Unit_Results`, `Additional_Shipments_Needed`).
- Write metadata in top rows, headers at specified row index.
- Populate data rows. Ensure booleans are Python `True`/`False` (openpyxl serializes to Excel `TRUE`/`FALSE`).
- Format dates as `YYYY-MM-DD` strings or `datetime.date` objects consistently.
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
  - Do not assume all dates are `datetime` objects; handle string fallbacks.
  - Avoid hardcoding row indices; locate headers dynamically when possible, but respect fixed-layout requirements if specified.
  - Run a lightweight structure validation script immediately after generation, before assuming correctness.
  - Always track `Rounding_Applied` boolean if `math.ceil` changes the value, as verifiers often check this explicitly.