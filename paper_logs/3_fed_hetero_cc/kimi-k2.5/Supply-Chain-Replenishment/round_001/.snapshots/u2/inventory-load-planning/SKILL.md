---
name: inventory-load-planning
description: Generates inventory load plans from multi-sheet Excel workbooks containing stock snapshots, scheduled inbounds, and configuration. Use when tasked with calculating days on hand, out-of-stock dates, additional cases needed, pallet requirements, and delivery timing from supply chain spreadsheets.
---

# Inventory Load Planning Workflow

## Overview
Transform source inventory/inbound Excel workbooks into a structured load plan workbook using `openpyxl`. The process involves extracting configuration and inventory data, performing supply chain calculations, and writing results to `Load_Detail` and `Load_Action_Summary` sheets.

## When to Use
- Multi-sheet Excel inputs with stock snapshots, scheduled inbounds, and configuration
- Calculating days on hand, out-of-stock projections, pallet requirements
- Supply chain replenishment planning with horizon-based demand matching

## Step-by-Step Workflow
1. **Inspect Source Structure**: Read all sheet names. Identify sheets for configuration (e.g., `Load Config`), stock levels (e.g., `Stock Snapshot`), and inbound schedules (e.g., `Scheduled Inbounds`). Use `header=None` to inspect raw layout first.
2. **Extract Configuration & Dates**:
   - Locate `AsOfDate`, `HorizonEnd`, and `CasesPerPallet`.
   - **Critical**: Dates are often in row 1 or 2. Always validate cell values are not `None` before performing date arithmetic. If a cell is `None`, check adjacent rows or parse string formats.
   - Calculate `PlanningDays = (HorizonEnd - AsOfDate).days`.
3. **Parse Inventory & Inbounds**:
   - Map item codes to `OnFloor` cases and `DailySales`. Use explicit `skiprows` based on inspection.
   - Map item codes to inbound arrivals (`ArrivalDate`, `CasesDue`). Filter inbounds to only those `<= HorizonEnd`.
4. **Calculate Metrics** (per item):
   - `DaysOnHand = OnFloor / DailySales` (guard against `DailySales == 0`).
   - `ProjectedOOSDate = AsOfDate + timedelta(days=DaysOnHand)`.
   - `InboundByHorizon = sum(CasesDue for arrivals <= HorizonEnd)`.
   - `DeliveredDOH = (OnFloor + InboundByHorizon) / DailySales`.
   - `RemainingDemand = DailySales * PlanningDays`.
   - `AdditionalCases = max(0, RemainingDemand - OnFloor - InboundByHorizon)`.
   - `PalletsRequired = ceil(AdditionalCases / CasesPerPallet)`.
   - `RequiredDeliveryDate = ProjectedOOSDate`.
   - `EarlierDeliveryRequired = True` if `RequiredDeliveryDate < earliest_inbound_date` or no inbound exists.
5. **Generate Output Workbook**:
   - Create `Load_Detail` sheet with headers and calculated rows.
   - Create `Load_Action_Summary` sheet filtering items where `PalletsRequired > 0`.
   - Save as `.xlsx`.
6. **Verify Output**: Read back the generated workbook. Confirm sheet names, header counts, row counts, and data types (dates as strings/dates, numbers as floats/ints, booleans as bools).

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Anti-Patterns & Troubleshooting
- **`TypeError: unsupported operand type(s) for -: 'NoneType' and 'NoneType'`**: Caused by assuming dates are in a fixed row without checking. Always assert `cell.value is not None` and `isinstance(cell.value, (date, datetime))` before subtraction.
- **Hardcoded Row Indices**: Source layouts vary. Use header matching or explicit value checks rather than assuming `A2` or `B1`.
- **Division by Zero**: Guard against `DailySales == 0` when calculating DOH.
- **Date Formatting**: Excel stores dates as `datetime` objects. Convert to `YYYY-MM-DD` strings for output if required, or keep as native dates for Excel compatibility.
- **Inbound Filtering**: Only count inbounds arriving on or before `HorizonEnd`. Future inbounds outside the planning horizon do not reduce current demand.
- **Header Row Misidentification**: Supply chain exports often have metadata rows before headers. Always inspect raw structure first; don't assume `header=0`.
- **Header Text in Data Rows**: If "On Floor" appears as a value, skiprows was wrong. Use inspection to find correct header row.

See `references/troubleshooting.md` for symptom-to-fix mapping.

## Verification Checklist
- [ ] `AsOfDate` and `HorizonEnd` are valid dates.
- [ ] All item codes from source appear in `Load_Detail`.
- [ ] `PalletsRequired` uses ceiling division.
- [ ] `EarlierDeliveryRequired` correctly compares required date vs earliest inbound.
- [ ] Output file opens without corruption and matches expected schema.

## Known invariants (by sub-task)

### B1: Multi-sheet Excel load plan
- Output workbook must have exactly two sheets: `Load_Detail` and `Load_Action_Summary`
- `Load_Detail` includes metadata header rows before column headers
- Dates in output are ISO strings (`YYYY-MM-DD`), not datetime objects