---
name: inventory-metrics-calculation
description: Read multi-sheet Excel workbooks containing entity, incoming, and ratio data; perform capacity/coverage calculations (DOH/coverage days, shortage dates, inbound aggregation, delivered coverage, demand forecasting, block/pallet/crate rounding, scheduling); and generate verified output workbooks. Use when tasks involve parsing .xlsx files with mixed date formats, computing inventory, staffing, maintenance resupply, or freshness/expiration metrics, and writing structured results back to Excel.
---

# Inventory & Capacity Metrics Calculation

## Environment Setup
- `openpyxl` is often missing in containerized environments.
- If `pip install openpyxl` fails with `externally-managed-environment`, use:
  ```bash
  pip install openpyxl --break-system-packages -q
  ```
- Always verify installation before running calculation scripts.

## Reading Source Workbooks
- Source workbooks typically contain three sheets: `Current [Entity]`, `Incoming [Entity]`, `Ratio` (or domain-specific equivalents like `Shelf_Life`).
- **Date parsing**: Dates may appear as `datetime` objects or ISO strings (`YYYY-MM-DD`). Normalize all dates to `datetime.date` before arithmetic. Use a robust helper:
  ```python
  def to_date(val):
      if isinstance(val, date): return val
      if isinstance(val, str): return datetime.strptime(val, "%Y-%m-%d").date()
      return val
  ```
- Use `data_only=True` when loading if formulas exist, but for raw data extraction, default loading is fine.
- Extract metadata from header rows or specific cells (e.g., `B1` for `AsOfDate`, `D1` for `PlanningHorizonEnd`).

## Core Calculation Workflow
1. **Coverage Days / DOH**: `current_amount / daily_rate`
2. **Projected Shortage Date**: `as_of_date + timedelta(days=floor(Coverage_Days))`
3. **Inbound Amount**: Sum amounts from incoming records where `date <= PlanningHorizonEnd`.
4. **Delivered Coverage**: `(current_amount + inbound_amount) / daily_rate`
5. **Remaining Demand**: `daily_rate * remaining_days_in_horizon`
6. **Additional Amount Needed**: `max(0, remaining_demand - current_amount - inbound_amount)`
7. **Blocks/Pallets/Crates Required**: `math.ceil(additional_amount / units_per_block)`
8. **Required Start/Delivery Date**:
   - If `blocks == 0`: `None`/blank
   - Else if `earliest_inbound_date` exists and `earliest_inbound_date <= projected_shortage_date`: `as_of_date + floor(delivered_coverage)`
   - Else: `projected_shortage_date`
9. **Rounding Applied**: `TRUE` if `additional_amount > 0` and `(additional_amount % units_per_block) != 0`. Else `FALSE`.
10. **Earlier Delivery/Shift Required**: `TRUE` if `blocks > 0` AND (`earliest_inbound_date` is missing/blank OR `required_date < earliest_inbound_date`). Else `FALSE`.

## Staffing & Shift Scheduling Variant
When the domain is hospital staffing or shift scheduling, map columns as follows:
- `Current_Staff_Hours` → `current_amount`
- `Daily_Required_Hours` → `daily_rate`
- `Current_Coverage_Days` → `Coverage Days`
- `Projected_Understaff_Date` → `Projected Shortage Date`
- `Incoming_Hours_By_Horizon` → `Inbound Amount`
- `Delivered_Coverage_To_Horizon` → `Delivered Coverage`
- `Remaining_Demand_Hours` → `Remaining Demand`
- `Additional_Hours_Needed` → `Additional Amount Needed`
- `Shift_Blocks_Required_Rounded_Up` → `Blocks Required`
- `Hours_Per_Shift_Block` → `units_per_block`
- **Zero-rate handling**: If `daily_rate == 0`, output blanks for coverage days, shortage date, and delivered coverage. Set remaining demand and additional hours to `0`.

## Freshness/Expiration Variant
When the domain involves perishable goods (meal kits, food inventory, shelf-life tracking), apply these adaptations:

### Sheet Mapping
- `Current Inventory` → contains `Current_Boxes`, `Daily_Order_Rate_Boxes`, and **`Boxes_Expiring_By_Horizon`**
- `Incoming Deliveries` → contains `Delivery Date`, `Pallets`, `Boxes`
- `Shelf_Life` (replaces `Ratio`) → contains `Boxes_Per_Pallet` and optionally `Minimum_RSL_Days`

### Expiration Adjustment (CRITICAL)
- **Usable Inventory** = `Current_Boxes - Boxes_Expiring_By_Horizon`
- Use `Usable_Inventory` as `current_amount` in all downstream calculations (DOH, shortage date, delivered coverage, additional needed)
- Do NOT use raw `Current_Boxes` for calculations—expiration reduces available stock

### Column Mapping
- `Current_Boxes` → raw inventory (do not use directly)
- `Boxes_Expiring_By_Horizon` → subtract from current to get usable
- `Usable_Current_Boxes` → `current_amount` for DOH/coverage math
- `Daily_Order_Rate_Boxes` → `daily_rate`
- `Boxes_Per_Pallet` (from Shelf_Life sheet) → `units_per_block`
- `Pallets_Required_Rounded_Up` → `Blocks Required`

### Inbound Filtering
- Only count deliveries where `Delivery Date <= PlanningHorizonEnd`
- Deliveries after the horizon do NOT contribute to inbound amount
- Find `earliest_inbound_date` across ALL deliveries for the entity (not just those within horizon) for the Earlier_Delivery_Required logic

### Output Structure
- Sheet 1: `Freshness_Results` (or similar) with metadata rows (AsOfDate, PlanningHorizonEnd, RemainingDays) followed by entity data rows
- Sheet 2: `Additional_Freshness_Needed` (or similar) filtered to entities where `Pallets_Required > 0`
- Boolean flags: `Rounding_Applied`, `Earlier_Delivery_Required` must be Python `True`/`False`

## Writing Output Workbooks
- **Standard Layout**: Two sheets.
  1. `Part_Results` (or domain-specific name): Rows 1-3 for metadata (`AsOfDate`, `PlanningHorizonEnd`, `RemainingDays`), Row 4 blank, Row 5 headers, Row 6+ data.
  2. `Additional_[Action]_Needed`: Filtered to only entities where `Blocks/Crates_Required > 0`.
- **Critical `openpyxl` API rule**: Always use `value=` keyword argument in `ws.cell()`. Never mix positional and keyword arguments.
  ```python
  # CORRECT
  ws.cell(row=r, column=c, value=some_value)
  # WRONG (SyntaxError)
  ws.cell(row=r, column=c, some_value)
  ```
- **Boolean values**: Must be Python `bool` type (`True`/`False`), not integers (`1`/`0`). Integers appear as numbers in Excel, not TRUE/FALSE.
  ```python
  # CORRECT - displays as TRUE/FALSE in Excel
  ws.cell(row=r, column=c, value=bool(rounding_applied))
  # WRONG - displays as 1 or 0 in Excel
  ws.cell(row=r, column=c, value=1 if condition else 0)
  ```
- Format dates as ISO strings (`.isoformat()`) or keep as `datetime` objects consistently.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Verification Steps
1. Reload the generated workbook with `openpyxl.load_workbook()`.
2. Verify sheet names, row counts, and column headers match requirements.
3. Spot-check edge cases:
   - Entities where `earliest_inbound_date < as_of_date`
   - Entities where `earliest_inbound_date > shortage_date` (triggers `Earlier_Required`)
   - Entities with no inbound deliveries (`earliest_inbound_date` is blank)
   - Division-by-zero or zero-rate scenarios (must output blanks/zeros, not crash)
   - **Freshness variant**: Verify usable = current - expiring before DOH calculation
4. Confirm boolean flags and rounding logic match expected outputs.
5. Verify filtered sheet only contains rows where `Blocks/Crates > 0`.

## Anti-Patterns to Avoid
- **Do not** use f-strings with inline conditionals for formatting: `f"{val:.4f if val else 'N/A'}"` → SyntaxError. Pre-compute the formatted string.
- **Do not** assume all dates in Excel are `datetime` objects. Check `isinstance(val, str)` and parse with `datetime.fromisoformat()` or `datetime.strptime()`.
- **Do not** skip `--break-system-packages` in root containers if `pip` fails; it's safe in ephemeral environments.
- **Do not** write calculation scripts inline in the shell. Use `write_file` to create a `.py` script, then execute it. This avoids escaping issues and enables debugging.
- **Do not** filter incoming records by horizon when finding `earliest_inbound_date`. The earliest date should consider *all* inbound records for the entity, not just those within the planning horizon.
- **Do not** use integer `1`/`0` for boolean Excel flags. Always use Python `True`/`False`.
- **Do not** use raw `Current_Boxes` for DOH calculations in freshness tasks—always subtract expiring boxes first.
- **Do not** assume the third sheet is always named `Ratio`—it may be `Shelf_Life`, `Constants`, or similar.

## Known invariants (by sub-task)

### multi-sheet-inventory-workbook
- Input sheets: `Current Inventory`, `Incoming Shipments`, `Ratio`
- Header rows may be offset from row 1 (check rows 1-3 for metadata like `Today's Date`, `Month End`)
- Formula cells (e.g., `=80*C2` for cases) return `None` when read; calculate manually using constants from Ratio sheet
- Cases per pallet: 80 (standard ratio, verify in workbook)

### multi-sheet-staffing-workbook
- Input sheets: `Current Staffing`, `Incoming Shifts`, `Ratio`
- Metadata typically in `B1` (AsOfDate) and `D1` (PlanningHorizonEnd)
- `Hours_Per_Shift_Block` is in `Ratio` sheet (e.g., 24)
- Preserve source entity order in output.
- Filter `Additional_Shifts_Needed` sheet to only entities where `Blocks_Required > 0`.

### maintenance-resupply-workbook
- Input sheets: `Current Parts`, `Scheduled Deliveries`, `Ratio`
- Metadata in `B1` (AsOfDate) and `D1` (PlanningHorizonEnd) of first sheet.
- Scheduled Deliveries has both `Crates` and `Units` columns; use `Units` for calculations, `Crates` for reference.
- `Units_Per_Crate` is a global value in `Ratio` sheet.
- **Remaining days calculation**: Use `(horizon_end - as_of_date).days + 1` for inclusive counting.
- **Earliest scheduled delivery**: Find minimum delivery date per part; set to `None` if no deliveries scheduled.
- Preserve source entity order in output.
- Filter `Additional_Resupply_Needed` sheet to only entities where `Crates_Required > 0`.

### freshness-replenishment-workbook
- Input sheets: `Current Inventory`, `Incoming Deliveries`, `Shelf_Life`
- Metadata in `B1` (AsOfDate) and `D1` (PlanningHorizonEnd) of Current Inventory sheet.
- `Current Inventory` contains `Boxes_Expiring_By_Horizon` column—subtract from `Current_Boxes` to get usable inventory.
- `Shelf_Life` sheet contains `Boxes_Per_Pallet` (units_per_block) and optionally `Minimum_RSL_Days`.
- **Usable inventory** = `Current_Boxes - Boxes_Expiring_By_Horizon` (use this for all DOH/coverage math).
- Inbound filtering: only count deliveries where `Delivery Date <= PlanningHorizonEnd`.
- Preserve source entity order in output.
- Filter `Additional_Freshness_Needed` sheet to only entities where `Pallets_Required > 0`.
- Boolean flags: `Rounding_Applied`, `Earlier_Delivery_Required` must be Python `True`/`False`.

## Troubleshooting
- `ModuleNotFoundError: No module named 'openpyxl'` → Install with `--break-system-packages`.
- `SyntaxError: positional argument follows keyword argument` → Add `value=` to all `ws.cell()` calls.
- `TypeError: unsupported operand type(s) for -: 'str' and 'str'` → Normalize date/numeric types before arithmetic using a `to_date()` helper.
- Incorrect delivery/shift dates → Verify the `earliest_inbound_date <= shortage_date` branching logic and ensure `floor()`/`ceil()` are applied correctly.
- Zero-rate crashes → Guard division with `if rate == 0: coverage = None` before computing dates.
- Boolean flags show as 1/0 in Excel → Ensure you pass Python `bool` (`True`/`False`) to `ws.cell(value=...)`.
- DOH calculations wrong in freshness tasks → Verify you're using `Usable_Inventory` (current - expiring), not raw `Current_Boxes`.
- Inbound amount too high → Check that deliveries after `PlanningHorizonEnd` are excluded from the sum.