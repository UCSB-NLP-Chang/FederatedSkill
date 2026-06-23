---
name: excel-inventory-planning
description: Reads inventory and shipment Excel workbooks, calculates DOH, OOS dates, pallet requirements, and generates formatted output workbooks. Use for supply chain inventory analysis, shipment scheduling, or Excel-based logistics calculation tasks.
---

# Excel Inventory Planning & Shipment Calculation

## Environment Setup
- Modern Debian/Ubuntu environments enforce PEP 668. Install dependencies with:
  `pip install openpyxl --break-system-packages -q`
  Or use a virtual environment: `python3 -m venv .venv && source .venv/bin/activate && pip install openpyxl`

## Data Extraction Pattern
1. Load workbook: `wb = openpyxl.load_workbook(path, data_only=False)`
2. Inspect sheets: `wb.sheetnames`
3. Read headers and data carefully. Use `ws.max_column` (not `max_col`).
4. **Formula Handling**: `openpyxl` reads formulas as strings (e.g., `'=80*C2'`). Compute values manually in Python. Do not assume `data_only=True` will resolve formulas unless the file was previously saved with calculated values.
5. **Date Normalization**: Excel cells may contain `datetime.datetime`, `datetime.date`, or strings (`'2025-07-04'`). Normalize all dates to `datetime.date` before arithmetic or comparison.

## Calculation Workflow
For each SKU, compute sequentially:
1. `Current_DOH = In_Stock_Cases / Daily_Rate`
2. `OOS_Date = AsOfDate + timedelta(days=math.floor(Current_DOH))`
3. `Inbound_Cases = Sum(pallets * cases_per_pallet)` for deliveries within planning horizon.
4. `Delivered_DOH = (In_Stock_Cases + Inbound_Cases) / Daily_Rate`
5. `Remaining_Demand = Daily_Rate * Remaining_Days_In_Horizon`
6. `Additional_Cases_Needed = Remaining_Demand - (In_Stock_Cases + Inbound_Cases)`
7. `Pallets_Required = math.ceil(Additional_Cases_Needed / Cases_Per_Pallet)`
8. `Earliest_Inbound_Date = Min(delivery dates for this SKU)`
9. `Earlier_Delivery_Required = True` if `Earliest_Inbound_Date > OOS_Date`, else `False`
10. `Required_Delivery_Date = OOS_Date` if earlier delivery required, else `AsOfDate + timedelta(days=math.floor(Delivered_DOH))`

## Output Generation
- Create new workbook with specified sheet names (e.g., `SKU_Results`, `Additional_Shipments_Needed`).
- Write metadata in top rows, headers at specified row index.
- Populate data rows. Ensure booleans are Python `True`/`False` (openpyxl serializes to Excel `TRUE`/`FALSE`).
- Format dates as `YYYY-MM-DD` strings or `datetime.date` objects consistently.
- Save: `wb.save(output_path)`

## Verification & Troubleshooting
- **Structure Check**: Verify sheet names, header row index, column count, and data row count match requirements exactly.
- **Legacy Node Checks Failure**: If `test_legacy_node_checks` or similar verifiers fail, verify:
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
