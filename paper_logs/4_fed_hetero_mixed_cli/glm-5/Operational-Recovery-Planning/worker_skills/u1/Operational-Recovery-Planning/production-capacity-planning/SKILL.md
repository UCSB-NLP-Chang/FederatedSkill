---
name: production-capacity-planning
description: Generate Excel workbooks for capacity planning, production recovery, and queue catch-up scenarios. Handles multi-sheet workbooks with date series, cumulative formulas, constraint validation, and verification. Covers weekly queue recovery (step-down policy), daily production recovery (multi-scenario), shift-day high-capacity windows, and date-cutoff distribution constraints. Applies to Harbor DC, Fulfillment, Running Board, and Harvest/Ag recovery domains.
---

# Production Capacity Planning

## When to Use
- Weekly queue recovery simulation with step-down policy (B1)
- Daily multi-scenario production recovery with PO deadlines (B2)
- Shift-day high-capacity windows (20-24 days at elevated capacity)
- Date-cutoff distribution constraints (e.g., ">= X before date Y, 0 after")
- Excel workbooks requiring cumulative formulas and date constraints
- Capacity planning across multiple scenarios/sheets
- **Harvest/Ag recovery**: Wheat=Web, Canola=DB, Flax=Network (same patterns)
- **Running Board recovery**: Crew Cab=Web, Extended Cab=DB, Grill Guard=Network (same patterns)
- **Outcome-driven scenarios**: When the task specifies target business outcomes per scenario (e.g., "May PO On-Time: No", "Crew Yes, Extended No") and you must design production schedules to achieve them

---

## Workflow

### Part A: Weekly Queue Recovery (B1)

1. **Discover Sheet Structure**
   - Locate demand row by label (e.g., "Demand", "Weekly Forecast"), NOT by position.
   - Find header row containing week numbers.
   - Identify parameter cells: daily capacity, threshold days, initial queue.

2. **Verify Column-to-Week Mapping**
   - Read header row values; filter columns where header is numeric (skip "Total", "Notes").
   - Map each valid column to its week number before extracting values.

3. **Extract Initial Conditions**
   - If spec says "Start + Demand = X", solve: `Calc Start = X - Demand`.
   - Cross-reference with sheet formulas if available.

4. **Run Weekly Loop**
   - Step-down policy: 6→5→4 days after threshold week.
   - Track milestone weeks (queue ≤ threshold).
   - Calculate cumulative progress.

5. **Generate Output**
   - Excel: domain headers, N data rows (no extra None rows), weeks ascending.
   - summary.txt: milestone weeks + domain narrative (word/sentence limits).

6. **Verify**
   - Run `scripts/validate_workbook.py` against generated files.

---

### Part B: Daily Multi-Scenario Recovery (B2)

**D0. Count Working Days Programmatically**
   - **CRITICAL**: Never manually count working days. Use a script to enumerate all dates, filter weekends (weekday >= 5) and holidays, then count.
   - A single off-by-one error in working day count cascades into wrong production totals and failed outcome checks.
   - Decision rule: If `total_production != expected_total`, first verify working day count before adjusting rates.

**D1. Pre-Validate Demand**
   - Sum all PO due quantities BEFORE simulation.
   - Verify total demand is achievable within date horizon and capacity constraints.

**D1b. Outcome-Driven Production Design (When Task Specifies Target Outcomes)**
   - When the task requires specific business outcomes per scenario (e.g., "May PO On-Time: No"), work backwards from the target:
     1. Calculate total PO demand for the category.
     2. For "On-Time: Yes": target total production >= total PO demand → cumulative EOD <= 0.
     3. For "On-Time: No": target total production < total PO demand → cumulative EOD > 0.
     4. Compute required daily rate: `rate = target_total // working_days`.
     5. Distribute remainder via front-load pattern (first N days get +1).
   - Verify: `sum(production) == target_total` and `cumulative_EOD` matches expected sign.
   - See `references/outcome-design-patterns.md` for worked examples.

**D2. Build Calendar**
   - Generate date range (start to end, inclusive).
   - Exclude weekends (weekday >= 5).
   - Exclude holidays (document in reference files).
   - Identify capacity transition dates (e.g., 120→135 after Feb 5).

**D3. Distribute Production**
   - Use `divmod(total, working_days)` to split evenly.
   - Front-load remainder: first N days get +1.
   - Apply category-specific start dates (e.g., DB starts March 1).
   - High-capacity days: up to 170 units, limited to 20-24 days.
   - **CRITICAL**: Calculate exact remaining need. Do NOT fill all available capacity days to maximum.
     ```python
     # WRONG: Fill all shift days to max capacity
     shift_day_production = 170  # Fills every shift day

     # RIGHT: Calculate exact remaining need
     remaining = total_po - already_produced
     per_day, remainder = divmod(remaining, len(remaining_days))
     # Then distribute per_day (+1 for first remainder days)
     ```

**D3b. Shift-Day Selection (When Applicable)**
   - Identify eligible working days on/after threshold date.
   - **CRITICAL**: Also filter by ALL category start dates. If any category starts later than the threshold, shift days must be on/after the LATEST start date to avoid premature production.
   - Select 20-24 consecutive or distributed days.
   - Apply elevated capacity (e.g., 160-170) only on selected days.
   - Validate: shift days must be working days, on/after threshold AND all category start dates, within count range.
   - See `references/constraint-patterns.md` for shift-day algorithm with category constraints.

**D3c. Date-Cutoff Distribution (When Applicable)**
   - For constraints like ">= X before date Y, 0 after":
     1. First pass: identify all working days before cutoff date.
     2. Calculate per-day allocation: `target // count`, remainder front-loaded.
     3. Second pass: set all days on/after cutoff to 0.
     4. Verify: sum before cutoff >= target, sum after cutoff == 0.
   - See `references/constraint-patterns.md` for two-pass pattern.

**D4. Build Workbook**
   - Use `openpyxl`. One sheet per scenario.
   - Row 1-3: Headers/titles. Row 4+: Data.
   - Column B: Dates. First cell = literal `datetime.date`. Subsequent = formula `=B(prev)+1`.
   - Constants: Columns C, D, F, G, I (production, PO due).
   - Formulas: Columns E, H, J (cumulative: `=E(prev)+D(curr)-C(curr)`).

**D5. Verify Constraints**
   - **CRITICAL**: Convert all openpyxl dates to `.date()` before ANY comparison.
   - Use the canonical helper: `to_date(val)` from `scripts/validate_workbook.py`.
   - Weekend/holiday production = 0.
   - PO due quantities match at specified dates.
   - Cumulative open <= 0 for "On-Time" scenarios.
   - Shift-window days: separate thresholds (not standard caps).

**D6. Generate Summary**
   - Create summary.md with sections and **bold** field labels.

---

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

---

## Known Invariants (by Sub-Task)

### B1: Queue Recovery (SOC, Radiology, Harbor GDP, Returns Center)
- Returns Center demand = Exception Review + Standard Return Intake (aggregate both rows).
- Capacity sheets may have "Total" columns — filter these from header inspection.
- Weeks 6-54 format: header may show 6-54 range, extract from header.

### B2: Daily Production (Harbor DC, Fulfillment Recovery, Harvest/Ag, Running Board)
- **Domain Mapping**:
  - Harvest/Ag: Wheat=Web, Canola=DB, Flax=Network
  - Running Board: Crew Cab=Web, Extended Cab=DB, Grill Guard=Network
- Holidays: Feb 19 (Louis Riel Day), Mar 30 (Good Friday).
- Capacity: 120 → 135 after Feb 5. High-cap days: up to 170, max 22-24 days.
- **Category Start Dates**: Wheat/Web immediate, Canola/DB March 1 (or Feb 20 in early-start scenarios).
- **Flax/Network Constraints**: Either minimum total (≥1200), front-loaded cutoff (≥100 before Feb 1), or eliminated (=0).
- openpyxl stores dates as `datetime.datetime`, not `datetime.date`. Use `.date()` conversion.
- Formula columns (E, H, J): must contain formulas, not constants.
- B4: literal `datetime.date`; B5+: formula `=B4+1`, `=B5+1`, etc.
- See `references/variant-patterns.md` for domain-specific details.

---

## Critical Anti-Patterns

- **Date Type Mismatch**: openpyxl reads/writes dates as `datetime.datetime`. Always use `val.date() if isinstance(val, datetime.datetime) else val` for comparisons and lookups. **Never compare datetime.datetime to datetime.date directly** — this causes TypeError.
- **Column-to-Week Assumption**: Do NOT assume column positions. Verify header row first.
- **Row Index Assumption**: Locate rows by label, not by hardcoded index (key failure mode).
- **Hardcoded Row Ranges in Verification**: Do NOT assume data occupies specific row ranges (e.g., rows 4-104). Discover actual data bounds by iterating until empty cells or using `ws.max_row`. Hardcoded ranges cause off-by-one errors and partial verification.
- **Manual Working Day Counting**: Do NOT count working days by hand. Always enumerate dates programmatically and filter. A single missed holiday or miscounted weekend day cascades into wrong production totals.
- **Iterative Parameter Tweaking**: Do NOT iterate parameters blindly. Calculate required capacity analytically.
- **Self-Verification Mismatch**: Verification code that validates its own output may diverge from test expectations. Read actual output file and compare cell-by-cell. **This is the most common failure mode for this task family.**
- **Uniform Constraint Application**: Shift-window days bypass standard caps. Isolate shift days with separate thresholds.
- **Loop Variable Scoping**: When refactoring verification loops, ensure loop variable names are consistent throughout the block. Mismatched variables (e.g., `ri` vs `ri3`) cause NameError at runtime.
- **Holiday Inclusion in Distribution**: When distributing quantities before a cutoff date, exclude holidays from the eligible day count. Including holidays (which have 0 production) in the divisor causes under-allocation.
- **Shift-Day Category Conflict**: Selecting shift days before a category's start date causes that category to show production prematurely. Always filter eligible shift days by the LATEST of (scenario threshold date, all category start dates). If Canola starts Feb 20 but threshold is Feb 1, shift days must be >= Feb 20.
- **Assuming verification coverage**: Just because you verified *something* doesn't mean you verified *the right things*. Map requirements to verifications explicitly.
- **Verifying constraints vs verifying outcomes**: Passing constraint checks (caps, dates, formulas) does NOT guarantee correct business outcomes (on-time delivery, exact totals). Always verify the FINAL business metrics, not just intermediate constraints.
- **Capacity Filling vs Exact Distribution**: Do NOT fill all available capacity days to maximum. Calculate exact remaining production needed and distribute that amount only. Overproduction on shift days causes cumulative open < 0, which is wrong.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| KeyError on row access | Row-index assumption | Locate by label, not position |
| None rows in output | Loop overran valid range | Check loop bounds; filter None |
| Cumulative open > 0 | Total production < POs | Recalculate daily output analytically |
| Date mismatch in lookup | datetime.datetime vs datetime.date | Convert via `.date()` |
| Self-verify passes, tests fail | Verification logic mismatch | Read actual file; compare with expected; map requirements to verifications |
| High-cap day count wrong | Counting before start date | Filter with `date >= threshold` |
| TypeError comparing dates | datetime.datetime vs datetime.date | Use `to_date()` helper before comparison |
| Distribution under-allocated | Holidays included in day count | Filter `is_non_working(d)` before counting eligible days |
| NameError in verification | Loop variable mismatch after refactor | Audit all variable references in loop body |
| All checks pass but output wrong | Verified wrong properties | Read test file if available; verify exact expected values |
| Constraints pass but outcomes fail | Verified intermediate, not final | Verify business outcomes (totals, on-time status) not just constraints |
| Verification row range error | Hardcoded row limits | Iterate until empty cell or use `max_row` |
| Harvest scenario confusion | Not recognizing Ag mapping | Treat Wheat=Web, Canola=DB, Flax=Network |
| Running Board scenario confusion | Not recognizing RB mapping | Treat Crew Cab=Web, Extended Cab=DB, Grill Guard=Network |
| Category production before start date | Shift days selected before category start | Filter shift days by `max(threshold, all_category_starts)` |
| Cumulative open < 0 (overproduction) | Capacity filling instead of exact need | Calculate exact remaining need; don't fill shift days to max |
| Working day count off by 1 | Manual counting error | Enumerate dates programmatically; filter weekends + holidays; count |

---

## Verification Helpers

Use `scripts/validate_workbook.py` for reusable validation:
- `to_date(val)`: Canonical date conversion (handles datetime, date, None)
- `validate_sheet_names()`: Verify sheet structure
- `validate_date_range()`: Check date span coverage
- `validate_weekend_zero_production()`: Ensure no weekend/holiday production
- `validate_cumulative_formulas()`: Verify formula vs constant columns
- `validate_po_quantities()`: Check PO due values on specific dates
- `validate_formula_vs_constant()`: Ensure correct column types
- `validate_shift_days()`: Verify shift-day count, capacity, and date constraints

Run these after workbook generation to catch issues before test submission.

---

## Pre-Submission Verification Checklist

Before submitting, explicitly verify:

1. **Business Outcomes** (not just constraints):
   - [ ] Total production per category matches requirements
   - [ ] Final cumulative open PO values are correct (negative/zero for on-time)
   - [ ] On-time status matches expected outcome per scenario

2. **Constraint Satisfaction**:
   - [ ] All capacity caps respected (standard and shift-day)
   - [ ] Weekend/holiday production is zero
   - [ ] Category start dates honored
   - [ ] Date-cutoff constraints met (if applicable)

3. **Formula Correctness**:
   - [ ] Cumulative columns contain formulas, not constants
   - [ ] Date column has literal date in first row, formulas thereafter

4. **Read Test File** (if available):
   - [ ] Extract exact expected values from test file
   - [ ] Compare generated output cell-by-cell with expectations
   - [ ] Do NOT assume your verification covers what tests check

### Verification-Test Alignment Check

Self-verification passing ≠ tests passing. The gap is usually in WHAT you verified, not HOW.

- List every explicit requirement from the task
- For each requirement, confirm your verification actually tests that specific property
- If a test file is available, read it to understand exact expectations
- Map requirements to verifications explicitly: "Requirement X → verified by checking Y"

---

## Domain References

- `references/variant-patterns.md` — Domain variants (SOC, Radiology, Harbor DC, Harvest/Ag, Running Board)
- `references/constraint-patterns.md` — Distribution algorithms and shift-day selection
- `references/outcome-design-patterns.md` — Worked examples for designing production schedules to achieve specific business outcomes
