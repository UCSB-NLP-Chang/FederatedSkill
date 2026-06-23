---
name: excel-inventory-analysis
description: Analyze inventory and shipment data from Excel workbooks, calculate supply gaps, and generate updated shipment plans. Use when tasks involve reading multi-sheet Excel files with inventory, shipment schedules, and ratios, then computing days-on-hand, out-of-stock dates, and additional pallet requirements.
---

# Excel Inventory & Shipment Analysis

## Environment Setup
- `openpyxl` is frequently missing in base environments. Install immediately using:
  ```bash
  pip install openpyxl -q --break-system-packages
  ```
  (Use a venv if policy requires it, but `--break-system-packages` is reliable for isolated agent runs.)
- Prefer `openpyxl` over `pandas` for this domain. It preserves cell types, formulas, and allows precise row/column placement required by verifiers.

## Data Extraction Workflow
1. **Load Workbook**: `wb = openpyxl.load_workbook(path, data_only=False)`
2. **Identify Sheets**: Inspect `wb.sheetnames`. Typical layout: `Current Inventory`, `Incoming Shipments`, `Ratio`.
3. **Normalize Dates**: Excel cells mix `datetime` objects and ISO strings (`YYYY-MM-DD`). Use `scripts/setup_and_load.py` or inline parsing to convert all to `date` objects before arithmetic.
4. **Handle Formulas**: Cells like `=80*C2` are read as strings. Extract multipliers programmatically. Do not assume `data_only=True` will return evaluated numbers unless the source file was saved post-calculation.

## Calculation Logic
- **Days on Hand (DOH)**: `Current_Cases / Daily_Rate`
- **Projected OOS Date**: `AsOfDate + timedelta(days=DOH)`
- **Inbound Cases**: Sum `Pallets * Cases_Per_Pallet` for deliveries `<= PlanningHorizonEnd`.
- **Remaining Demand**: `Daily_Rate * Remaining_Days_In_Horizon`
- **Additional Cases Needed**: `max(0, Remaining_Demand - (Current_Cases + Inbound_Cases))`
- **Pallets Required**: `math.ceil(Additional_Cases / Cases_Per_Pallet)`
- **Required Delivery Date**: `AsOfDate + timedelta(days=Additional_Cases / Daily_Rate)`
- **Earlier Delivery Required**: `True` if `Required_Delivery_Date < Earliest_Scheduled_Inbound_Date`

## Output Generation
- Create a new workbook with `SKU_Results` (metadata + detailed rows) and `Additional_Shipments_Needed` (summary).
- Write metadata in `A1:B4` (AsOfDate, PlanningHorizonEnd, RemainingDays).
- Place headers at row 6 for `SKU_Results`, row 1 for `Additional_Shipments_Needed`.
- Format all dates as `YYYY-MM-DD` strings to avoid Excel serialization quirks.
- **Verification Step**: Immediately reload the saved workbook. Print sheet names, headers, and row counts. Assert expected structure before finishing.

## Anti-Patterns & Troubleshooting
- **Import Error**: `from datetime import datetime, date` followed by `date.timedelta` causes `AttributeError`. Always use `datetime.timedelta` or import `timedelta` directly.
- **Date Parsing**: Never assume uniform formats. Check `isinstance(val, datetime)` first.
- **Formula Evaluation**: `openpyxl` does not evaluate formulas. Parse them manually or compute values in Python before writing.
- **Silent Failures**: Always verify output by reading it back. Mismatched types (e.g., writing `datetime` instead of string) often break downstream verifiers.

## Helper Script
- Import or run `scripts/setup_and_load.py` to safely install `openpyxl`, normalize mixed dates, and extract formula multipliers without boilerplate.