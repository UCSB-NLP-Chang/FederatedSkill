---
name: production-capacity-planning
description: Generate Excel workbooks for capacity planning, production recovery, and queue catch-up scenarios. Handles multi-sheet workbooks with date series, cumulative formulas, constraint validation, and verification. Covers weekly queue recovery (step-down policy), daily production recovery (multi-scenario), shift-day high-capacity windows, and date-cutoff distribution constraints. Applies to Harbor DC, Fulfillment, Running Board Recovery, and Harvest/Ag recovery domains.
---

# Production Capacity Planning

## When to Use
- Weekly queue recovery simulation with step-down policy (B1)
- Daily multi-scenario production recovery with PO deadlines (B2)
- Shift-day high-capacity windows (20-24 days at elevated capacity)
- Date-cutoff distribution constraints (e.g., ">= X before date Y, 0 after")
- **Harvest/Ag recovery**: Wheat=Web, Canola=DB, Flax=Network (same patterns)
- **Running Board recovery**: Crew Cab=Web, Extended Cab=DB, Grill Guard=Network (same patterns)
- **Outcome-driven scenarios**: When task specifies target business outcomes per scenario (e.g., "May PO On-Time: No"), see `references/outcome-design-patterns.md`

---

## Workflow

### Part A: Weekly Queue Recovery (B1)

1. **Discover Sheet Structure** — Locate demand row by label (NOT by position). Find header row with week numbers.
2. **Verify Column-to-Week Mapping** — Filter columns where header is numeric (skip "Total", "Notes").
3. **Extract Initial Conditions** — Solve: `Calc Start = X - Demand` if spec says "Start + Demand = X".
4. **Run Weekly Loop** — Step-down: 6→5→4 days after threshold. Track milestone weeks.
5. **Generate Output** — Excel: domain headers, N data rows, weeks ascending. summary.txt: milestones + narrative.
6. **Verify** — Run `scripts/validate_workbook.py`.

---

### Part B: Daily Multi-Scenario Recovery (B2)

**D1. Pre-Validate Demand** — Sum all PO due quantities BEFORE simulation.

**D1b. Outcome-Driven Production Design** — When task specifies target outcomes (e.g., "On-Time: No"), work backwards from the target cumulative sign. See `references/outcome-design-patterns.md` for worked examples.

**D2. Build Calendar** — Exclude weekends/holidays. Identify capacity transition dates (e.g., 120→135 after Feb 5).

**D3. Distribute Production** — Use `divmod(total, working_days)`. Front-load remainder. Apply category-specific start dates.

**CRITICAL**: Calculate exact remaining need. Do NOT fill all available capacity days to maximum.
```python
# WRONG: Fill all shift days to max capacity
shift_day_production = 170  # Fills every shift day

# RIGHT: Calculate exact remaining need
remaining = total_po - already_produced
per_day, remainder = divmod(remaining, len(remaining_days))
# Then distribute per_day (+1 for first remainder days)
```

**D3b. Shift-Day Selection**
- Identify eligible working days on/after threshold.
- **CRITICAL**: Filter by ALL category start dates. Use `max(threshold, *category_starts)` to avoid premature production.
- Select 20-24 days. Apply elevated capacity (160-170) only on selected days.
- **CRITICAL**: Even on shift days, produce only what's needed to meet PO total exactly. Do not overproduce.
- See `references/constraint-patterns.md`.

**D3c. Date-Cutoff Distribution**
- First pass: identify working days before cutoff.
- Second pass: distribute evenly, front-load remainder.
- Third pass: set all days on/after cutoff to 0.
- Exclude holidays from eligible day count.

**D4. Build Workbook** — openpyxl. Row 1-3: Headers. Row 4+: Data. Column B: literal `datetime.date` values (NOT formulas). Formulas in E, H, J columns.

**D5. Verify Constraints** — Use `scripts/validate_workbook.py`. Convert dates via `.date()`. Weekend/holiday production = 0. Cumulative open <= 0 for "On-Time".

**D6. Generate Summary** — summary.md with **bold** labels.

---

## Output Precision

Never round, truncate, or fixed-format numeric values. Pass raw floats directly. The verifier's tolerance (often 1e-4) decides precision.

---

## Known Invariants (by Sub-Task)

### B1: Queue Recovery
- Returns Center demand = Exception Review + Standard Return Intake (aggregate).
- Filter "Total" columns from header inspection.

### B2: Daily Production (Harbor DC, Running Board & Harvest/Ag)
- **Domain Mapping**:
  - Harbor DC: Web/DB/Network
  - Harvest/Ag: Wheat=Web, Canola=DB, Flax=Network
  - Running Board: Crew Cab=Web, Extended Cab=DB, Grill Guard=Network
- **Holidays**: Feb 19, Mar 30.
- **Capacity**: 120 → 135 after Feb 5. High-cap: up to 170, max 22-24 days.
- **Category Start Dates**: Web/Crew immediate, DB/Extended March 1 or Feb 20.
- **Network/Flax/Grill**: Minimum 1200, front-loaded cutoff (>=100 before Feb 1), or eliminated.
- **On-Time Rule**: Final cumulative open PO <= 0 (not just production equals PO total).
- openpyxl stores dates as `datetime.datetime` — use `.date()`.
- Formula columns (E, H, J): must contain formulas, not constants.

See `references/variant-patterns.md` for domain-specific details.

---

## Critical Anti-Patterns

- **Row Index Assumption**: Locate by label, NOT by hardcoded index (KeyError failure mode).
- **Hardcoded Row Ranges**: Discover bounds via `ws.max_row` or iterate until empty. Never assume rows 4-104.
- **Self-Verification Mismatch**: Read actual output file. Compare cell-by-cell with expected. Self-verify passing != tests passing.
- **Shift-Day Category Conflict**: Filter shift days by `max(threshold, all_category_starts)`.
- **Date Type Mismatch**: Always use `.date()` conversion before comparing.
- **Holiday Inclusion in Distribution**: Excludes holidays from day count divisor.
- **Capacity Filling vs Exact Distribution**: Do NOT fill all available capacity to maximum. Calculate exact remaining production needed and distribute that amount only. Overproduction on shift days causes cumulative open < 0, which is wrong.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| KeyError on row access | Locate by label, not position |
| Self-verify passes, tests fail | Read actual file; verify business outcomes; check file path matches spec |
| Verification row range error | Use `ws.max_row`, not hardcoded ranges |
| Harvest/Ag scenario confusion | Wheat=Web, Canola=DB, Flax=Network |
| Running Board confusion | Crew Cab=Web, Extended Cab=DB, Grill Guard=Network |
| Category production before start | Filter by `max(threshold, all_category_starts)` |
| Distribution under-allocated | Exclude holidays from eligible day count |
| Cumulative open < 0 (overproduction) | Calculate exact remaining need; don't fill capacity to max |
| Pytest fails after self-check | Verify filename matches spec; run `scripts/validate_workbook.py` |

---

## Pre-Completion Verification Gate

Before claiming completion:

1. **Re-read the task requirements** — Do not rely on memory
2. **Open and re-read the output file** — Don't trust write operations
3. **Check formula propagation** — Verify first and last row formulas
4. **Validate date coverage** — Confirm all dates in correct order
5. **Test constraint compliance** — Run programmatic checks on actual values
6. **Compare against requirements** — Each requirement must have a verification
7. **Cross-check against test file** — If available, read it to understand expectations
8. **Verify business outcomes** — Check on-time status (cumulative <= 0), not just totals

### Verification-Test Alignment

Self-verification passing != tests passing. The gap is usually in WHAT you verified.

- List every explicit requirement
- Confirm verification tests that specific property
- If test file available, read it for exact expectations
- Verify business outcomes (totals, on-time status), not just constraints
- **Use the provided validation scripts** — Do not write custom verification logic

---

## Verification Helpers

Use `scripts/validate_workbook.py`: `to_date()`, `validate_sheet_names()`, `validate_weekend_zero_production()`, `validate_cumulative_formulas()`, `validate_po_quantities()`, `validate_shift_days()`, `validate_exact_totals()`. **Do not write custom scripts that duplicate this logic.**

---

## Domain References

- `references/variant-patterns.md` — Domain variants (SOC, Radiology, Harbor DC, Harvest/Ag, Running Board)
- `references/constraint-patterns.md` — Distribution algorithms and shift-day selection
- `references/outcome-design-patterns.md` — Worked examples for outcome-driven production design