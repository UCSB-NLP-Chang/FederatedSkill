---
name: supply-demand-gap-analysis
description: Analyze supply/demand gaps from inventory snapshots and booking feeds. Use for planning tasks requiring Days On Hand calculations, horizon-based booking aggregation, pallet sizing, and procurement action lists. Trigger when you see Rack Snapshot + Booking Feed data structures, or when asked to calculate coverage gaps and required delivery dates.
---

# Supply/Demand Gap Analysis

Calculate inventory coverage gaps from rack snapshots and booking feeds to generate procurement action lists.

## Core Workflow

1. **Extract Metadata**
   - Read AsOfDate and HorizonEnd from the Rack Snapshot (typically row 1)
   - Calculate PlanningDays = (HorizonEnd - AsOfDate).days + 1
   - Get CasesPerPallet from Pallet Defaults sheet

2. **Filter Booking Feed** (critical for correctness)
   - Include only bookings where:
     - SKU Ref is not None/blank
     - ETA is a valid datetime (not string 'bad-date', not None)
     - Booking State is 'Firm' or 'Locked' (exclude 'Tentative', 'Hold')
     - ETA <= HorizonEnd (within planning window)
   - Sum BookedCases by SKU for qualifying rows

3. **Calculate Coverage per SKU**
   - CurrentDaysOnHand = CasesOnRack / AvgDailyPull (skip if daily pull is 0 or None)
   - ProjectedOOSDate = AsOfDate + timedelta(days=floor(CurrentDaysOnHand))
   - BookedCasesByHorizon = sum from filtered bookings
   - DeliveredDaysOnHand = (CasesOnRack + BookedCasesByHorizon) / AvgDailyPull
   - RemainingDemandCases = AvgDailyPull * PlanningDays
   - AdditionalCasesNeeded = max(0, RemainingDemandCases - CasesOnRack - BookedCasesByHorizon)
   - PalletsRequired = ceil(AdditionalCasesNeeded / CasesPerPallet) if AdditionalCasesNeeded > 0 else 0

4. **Determine Delivery Requirements**
   - RequiredDeliveryDate = ProjectedOOSDate if AdditionalCasesNeeded > 0 else None
   - EarlierDeliveryRequired = (RequiredDeliveryDate is not None) and (RequiredDeliveryDate <= AsOfDate)

5. **Generate Action List**
   - Filter to SKUs where PalletsRequired > 0
   - Output: SKU_Ref, RequiredDeliveryDate, PalletsRequired, AdditionalCasesNeeded, EarlierDeliveryRequired

## Validation Checklist

- [ ] AsOfDate and HorizonEnd parsed as datetime objects
- [ ] PlanningDays includes both endpoints (difference + 1)
- [ ] Booking filter excludes: null SKUs, non-datetime ETAs, Tentative/Hold states, dates beyond horizon
- [ ] Division by zero guarded when AvgDailyPull is 0 or None
- [ ] PalletsRequired uses ceiling, rounds up for any remainder
- [ ] EarlierDeliveryRequired correctly identifies same-day or past requirements

## Common Data Quality Issues

| Issue | Pattern | Fix |
|-------|---------|-----|
| Missing SKU | `None` in SKU Ref column | Skip row |
| Invalid date | String 'bad-date' or non-datetime | Check isinstance before comparison |
| Tentative booking | State == 'Tentative' | Exclude from sum |
| Hold state | State == 'Hold' | Exclude from sum |
| Planner notes | Rows with all None values | Skip rows where SKU is None |
| Zero inventory | CasesOnRack == 0 | Still calculate; CurrentDaysOnHand = 0 |

## Anti-Patterns

- **Do not** include Tentative bookings in coverage calculations (overstates supply)
- **Do not** treat Hold state as firm supply
- **Do not** use string comparison for dates; parse to datetime first
- **Do not** floor pallet calculation; always round up partial pallets
- **Do not** assume AvgDailyPull > 0; guard division

## Helper Resources

- **scripts/calculate_coverage.py**: Deterministic baseline calculator for R2 schema variant. Run with `python3 scripts/calculate_coverage.py <input.xlsx> <output.xlsx>`. Adjust column indices if schema varies.
- **references/calculation-formulas.md**: Detailed formulas for each calculation step.
- **references/excel-datetime-handling.md**: Patterns for handling datetime.datetime vs datetime.date type issues with openpyxl.

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Known Invariants (by sub-task)

### R2 variant (Rack Snapshot + Booking Feed)
- Sheet names: `Rack Snapshot`, `Booking Feed`, `Pallet Defaults`
- State column: `Booking State` with values `Firm`/`Locked`/`Tentative`/`Hold`
- Output sheets: `Rack_Coverage`, `Commit_Gap_Actions`
- AsOfDate in Rack Snapshot cell B1, HorizonEnd in D1
- SKU data starts at row 4 (metadata rows above)

### General invariants
- Booking filter MUST exclude: null SKUs, non-datetime ETAs, Tentative/Hold states, ETAs > HorizonEnd
- PalletsRequired MUST use ceiling (never floor or round)
- EarlierDeliveryRequired MUST be True when RequiredDeliveryDate <= AsOfDate

## When Output Format Matters

Create two sheets:
1. **Rack_Coverage**: All SKUs with full calculation columns
2. **Commit_Gap_Actions**: Subset where PalletsRequired > 0, sorted by RequiredDeliveryDate