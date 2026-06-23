---
name: production-capacity-planning
description: Generate Excel workbooks for capacity planning, production recovery, and queue catch-up scenarios. Handles multi-sheet workbooks with date series, cumulative formulas, constraint validation, and verification. Covers weekly queue recovery (step-down policy), daily production recovery (multi-scenario), shift-day high-capacity windows, and date-cutoff distribution constraints. Applies to Harbor DC, Fulfillment, and Harvest/Ag recovery domains.
---

# Production Capacity Planning

## When to Use
- Weekly queue recovery simulation with step-down policy (B1)
- Daily multi-scenario production recovery with PO deadlines (B2)
- Shift-day high-capacity windows (20-24 days at elevated capacity)
- Date-cutoff distribution constraints (e.g., ">= X before date Y, 0 after")
- **Harvest/Ag recovery**: Wheat=Web, Canola=DB, Flax=Network (same patterns)

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

**D2. Build Calendar** — Exclude weekends/holidays. Identify capacity transition dates (e.g., 120→135 after Feb 5).

**D3. Distribute Production** — Use `divmod(total, working_days)`. Front-load remainder. Apply category-specific start dates.

**D3b. Shift-Day Selection**
- Identify eligible working days on/after threshold.
- **CRITICAL**: Filter by ALL category start dates. Use `max(threshold, *category_starts)` to avoid premature production.
- Select 20-24 days. Apply elevated capacity (160-170) only on selected days.
- See `references/constraint-patterns.md`.

**D3c. Date-Cutoff Distribution**
- First pass: identify working days before cutoff.
- Second pass: distribute evenly, front-load remainder.
- Third pass: set all days on/after cutoff to 0.
- Exclude holidays from eligible day count.

**D4. Build Workbook** — openpyxl. Row 1-3: Headers. Row 4+: Data. Column B: literal date + formulas. Formulas in E, H, J columns.

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

### B2: Daily Production (Harbor DC & Harvest/Ag)
- **Domain Mapping**: Wheat=Web, Canola=DB, Flax=Network.
- **Holidays**: Feb 19, Mar 30.
- **Capacity**: 120 → 135 after Feb 5. High-cap: up to 170, max 22-24 days.
- **Category Start Dates**: Wheat immediate, Canola March 1 or Feb 20.
- **Flax/Network**: Minimum 1200, front-loaded cutoff (≥100 before Feb 1), or eliminated.
- openpyxl stores dates as `datetime.datetime` — use `.date()`.
- Formula columns (E, H, J): must contain formulas, not constants.

See `references/variant-patterns.md` for domain-specific details.

---

## Critical Anti-Patterns

- **Row Index Assumption**: Locate by label, NOT by hardcoded index (KeyError failure mode).
- **Hardcoded Row Ranges**: Discover bounds via `ws.max_row` or iterate until empty. Never assume rows 4-104.
- **Self-Verification Mismatch**: Read actual output file. Compare cell-by-cell with expected.
- **Shift-Day Category Conflict**: Filter shift days by `max(threshold, all_category_starts)`.
- **Date Type Mismatch**: Always use `.date()` conversion before comparing.
- **Holiday Inclusion in Distribution**: Excludes holidays from day count divisor.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| KeyError on row access | Locate by label, not position |
| Self-verify passes, tests fail | Read actual file; verify business outcomes |
| Verification row range error | Use `ws.max_row`, not hardcoded ranges |
| Harvest scenario confusion | Wheat=Web, Canola=DB, Flax=Network |
| Category production before start | Filter by `max(threshold, all_category_starts)` |
| Distribution under-allocated | Exclude holidays from eligible day count |

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

### Verification-Test Alignment

Self-verification passing ≠ tests passing. The gap is usually in WHAT you verified.

- List every explicit requirement
- Confirm verification tests that specific property
- If test file available, read it for exact expectations
- Verify business outcomes (totals, on-time status), not just constraints

---

## Verification Helpers

Use `scripts/validate_workbook.py`: `to_date()`, `validate_sheet_names()`, `validate_weekend_zero_production()`, `validate_cumulative_formulas()`, `validate_po_quantities()`, `validate_shift_days()`. **Do not write custom scripts that duplicate this logic.**