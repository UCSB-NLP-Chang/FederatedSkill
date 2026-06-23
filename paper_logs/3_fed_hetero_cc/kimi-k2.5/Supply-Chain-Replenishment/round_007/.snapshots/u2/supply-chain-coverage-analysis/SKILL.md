---
name: supply-chain-coverage-analysis
description: Build zone-based inventory coverage and gap analysis workbooks from multiple Excel sources. Use when tasks require calculating days-on-hand, out-of-stock projections, inbound reconciliation, and dispatch gap lists with alias resolution.
---

# Zone Coverage and Gap Analysis

Build a coverage workbook from three inputs: Zone Snapshot (current stock), Zone Feed (inbound deliveries), and Alias Map (zone name resolution).

## Input Structure

**Zone Snapshot**: Headers in row 1-2 with metadata, data starts row 3+
- AsOfDate, HorizonEnd (datetime values)
- Zone, SKU, On Hand, Daily Demand

**Zone Feed**: Flat delivery records
- Record Type (filter for "DELIVERY"), Dispatch Ref, Revision, Zone Alias, SKU Code, ETA, Units, Release State

**Alias Map**: Two-column lookup
- Alias → Canonical Zone

## Processing Workflow

1. **Load with openpyxl**
   - Use `from openpyxl import load_workbook` (do not rely on pandas)
   - Access cell values via `ws.cell(row, col).value`
   - Excel dates return as datetime objects

2. **Parse Metadata**
   - Extract AsOfDate and HorizonEnd from snapshot headers
   - Calculate PlanningDays = (HorizonEnd - AsOfDate).days

3. **Build Alias Map**
   - Create dict: `alias_map[alias] = canonical_zone`

4. **Process Inbound Feed**
   - Filter: Record Type == "DELIVERY"
   - Deduplicate: Group by (Dispatch Ref), keep max(Revision)
   - Filter Release State: Keep only "Released" or "Staged" (exclude "Pending", "ignore")
   - Resolve Alias: Map Zone Alias → Canonical Zone (skip unknown aliases)
   - Validate: SKU not blank/None, ETA is valid datetime
   - Date Range: Keep only ETA <= HorizonEnd
   - Aggregate: Sum Units by (Zone, SKU, ETA) for coverage calculation

5. **Calculate Coverage**
   For each Zone/SKU:
   - Current_Days_On_Hand = On_Hand / Daily_Demand
   - Projected_OOS_Date = AsOfDate + timedelta(days=Current_Days_On_Hand)
   - Inbound_Units_By_Horizon = sum of valid inbound Units for this Zone/SKU
   - Delivered_Days_On_Hand = (On_Hand + Inbound) / Daily_Demand
   - Remaining_Demand_Units = PlanningDays * Daily_Demand
   - Additional_Units_Needed = max(0, Remaining_Demand - On_Hand - Inbound)
   - Pallets_Required = ceil(Additional_Units_Needed / 50)  # or variant-specific pallet size
   - Required_Delivery_Date = Projected_OOS_Date (if gap exists)
   - Earlier_Delivery_Required = True if (Additional_Units_Needed > 0) or (any inbound ETA > Projected_OOS_Date when gap exists)

6. **Output Workbook**
   Create two sheets:

   **Zone_Coverage**: All Zone/SKU rows with calculated fields
   - Include metadata: AsOfDate, HorizonEnd, PlanningDays

   **Dispatch_Gap_List**: Filtered to rows where Additional_Units_Needed > 0
   - Columns: Zone, SKU, Required_Delivery_Date, Pallets_Required, Additional_Units_Needed, Earlier_Delivery_Required

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Validation Checklist

- [ ] Deduplication kept highest revision per dispatch reference
- [ ] No inbound with ETA > HorizonEnd included in calculations
- [ ] Unknown aliases logged/skipped, not hard-failed
- [ ] Release State strictly filtered (Pending deliveries excluded)
- [ ] Gap list only shows rows with Additional_Units_Needed > 0
- [ ] Dates formatted as YYYY-MM-DD strings in output

## Anti-Patterns

- Do not use pandas (often not available); use openpyxl exclusively
- Do not forget `from openpyxl import load_workbook` (NameError risk)
- Do not include "Pending" or "ignore" release states in inbound calculations
- Do not include deliveries beyond HorizonEnd in "Inbound_Units_By_Horizon"
- Do not calculate pallets as simple division; always ceiling round up

## Troubleshooting

**Empty inbound after filtering**: Check that ETA dates are datetime objects, not strings. Check Release State values match exactly (case-sensitive).

**Alias resolution failures**: Log unknown aliases but continue processing. Common causes: new aliases not yet in map, whitespace in alias strings.

**Date math errors**: Ensure AsOfDate and HorizonEnd are datetime objects, not strings from Excel. Use `.date()` comparison if time components exist.

## Variants

If pallet size differs from 50 units, modify the pallet calculation constant. If release states have different valid values, adjust the filter list in step 4.
