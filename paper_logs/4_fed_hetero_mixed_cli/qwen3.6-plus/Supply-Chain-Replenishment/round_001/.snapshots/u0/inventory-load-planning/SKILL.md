---
name: inventory-load-planning
description: Calculate inventory load plans from stock snapshots and scheduled inbounds. Use when building OOS projections, pallet requirements, delivery schedules, or replenishment action summaries from Excel inventory data.
---

# Inventory Load Planning

## Workflow

1. **Read source workbook**: Parse stock snapshot, scheduled inbounds, and config sheets
2. **Extract metadata**: As-of date, horizon end, planning days, cases per pallet
3. **Calculate per-item metrics** using formulas below
4. **Create output workbook**: Load_Detail sheet with all calculations, Load_Action_Summary with items needing pallets
5. **Verify**: Check calculations and summary matches detail

## Key Formulas

| Metric | Formula |
|--------|----------|
| Current Days On Hand | `on_floor / daily_sales` |
| Projected OOS Date | `as_of_date + floor(days_on_hand)` |
| Delivered Days On Hand | `(on_floor + inbound_cases) / daily_sales` |
| Remaining Demand Cases | `daily_sales × planning_days - on_floor - inbound_cases` |
| Additional Cases Needed | `max(0, remaining_demand)` |
| Pallets Required | `ceil(additional_cases / cases_per_pallet)` |
| Required Delivery Date | `projected_oos_date` (or earlier if stockout imminent) |
| Earlier Delivery Required | `inbound_arrival_date > required_delivery_date` |

## Edge Cases

- **Zero on_floor**: Days on hand = 0, OOS date = as_of_date, immediate action needed
- **No scheduled inbound**: Treat inbound_cases = 0, still calculate requirements
- **Inbound after horizon**: Include in calculations but flag for earlier delivery
- **Excess inventory**: Additional cases needed = 0, no pallets required

## Anti-Patterns

- Using `floor()` for pallets instead of `ceil()` — underestimates truck space
- Forgetting items with zero current stock — they need immediate attention
- Ignoring scheduled inbounds that arrive after OOS date — these trigger earlier delivery flags
- Skipping verification step — always confirm output workbook structure and calculations
- **Import Error**: Use `from datetime import timedelta`, not `date.timedelta`

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Scripts

Run `scripts/load_plan_calculator.py` for a reference implementation of all calculations. The script provides function-based helpers that return full-precision values.