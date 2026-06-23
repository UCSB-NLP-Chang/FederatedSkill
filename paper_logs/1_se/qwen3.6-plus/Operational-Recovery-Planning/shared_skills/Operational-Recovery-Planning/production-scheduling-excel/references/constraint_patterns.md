# Constraint Patterns for Production Scheduling

## PO Deadline Tracking
- **Rule**: Cumulative production by a specific date must meet or exceed the PO due quantity.
- **Implementation**: Maintain a running sum. If `cumulative < due_qty` on the deadline date, front-load production or increase daily capacity until the gap closes.
- **Validation**: `assert sum(production[:deadline_idx]) >= due_qty`

## Capacity Ramps & Phase Transitions
- **Rule**: Daily capacity changes on specific dates (e.g., 120/day before Feb 5, 135/day after).
- **Implementation**: Split the workday list into segments based on transition dates. Apply `distribute_demand` per segment, or adjust the `capacity_limit` dynamically during iteration.
- **Validation**: Ensure no day exceeds its phase-specific cap.

## Temporary Capacity Windows & Overrides
- **Rule**: Capacity is temporarily increased/decreased for a specific date range (e.g., 10-hour shifts from Feb 5 to Mar 6, or equipment relocation).
- **Implementation**: Create a `date -> capacity` override map. During daily iteration, check if `current_date` falls within any active window. If so, use the override capacity for that day instead of the base/phase capacity. This handles overlapping or product-specific windows cleanly without rigid calendar segmentation.
- **Validation**: Verify that override days exactly match the specified range and that production on those days does not exceed the temporary cap.

## Multi-Product Independent Capacity Phases
- **Rule**: Different products may have different start dates, capacity ramps, or shift extensions.
- **Implementation**: Maintain a separate capacity lookup or rule set per product. During daily iteration, evaluate `current_date` against each product's phase boundaries and override windows to determine its cap for that row.
- **Validation**: Verify each product's production against its own phase caps independently. Check that shift extensions only apply to eligible products and dates.

## Shared Resources & Competition
- **Rule**: Multiple products share a fixed daily capacity pool.
- **Implementation**: Allocate priority products first. Distribute remaining capacity to secondary products. If total demand > total capacity, scale down proportionally or flag shortfall.
- **Validation**: `sum(product_prods) <= daily_pool_capacity` for every workday.

## PO Due Value Placement
- **Rule**: PO due quantities must appear on specific date rows in the schedule, with `0` on all other rows.
- **Implementation**: Map PO due dates to row indices. Write the due quantity to the corresponding cell. Ensure non-PO rows explicitly contain `0` or remain empty as specified.
- **Validation**: Iterate through all date rows. Assert `cell_value == due_qty` on PO dates and `cell_value == 0` elsewhere.

## Excel Formula Safety
- **Avoid Circular References**: Never define `A = B - C` and `B = A + C` in the same sheet. Use constants for daily production, and formulas only for cumulative/open/remaining columns.
- **Date Handling**: `openpyxl` writes `datetime.datetime` by default. Use `.date()` in Python validation. In Excel, use `=B4+1` for sequential dates to avoid type mismatches.
- **Verification**: Do not rely on `data_only=True` for chained formulas. Validate totals by summing constant columns directly in Python before saving.

## Verifier & Output Matching
- **Exact String Matching**: Verifiers often use strict equality checks for sheet names, headers, and summary text. Copy-paste directly from the prompt. Trim leading/trailing whitespace.
- **Date Type Consistency**: When reading back the workbook for validation, `openpyxl` returns `datetime.datetime` for date cells. Always compare using `.date()`. When writing, pass `datetime.date` objects to avoid `00:00:00` time components that may trigger string mismatch failures.
- **Formula vs Constant Enforcement**: If the prompt specifies "Column X must be a formula", verify by checking `isinstance(cell.value, str) and cell.value.startswith('=')`. If it specifies constants, verify `isinstance(cell.value, (int, float))`.
- **Row/Column Bounds**: Ensure the output covers exactly the date range specified. Do not pad or truncate. Verify row counts match `(end_date - start_date).days + 1`.