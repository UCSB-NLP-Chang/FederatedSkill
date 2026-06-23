---
name: production-capacity-planning
description: Generate Excel workbooks for capacity planning, production recovery, and queue catch-up scenarios. Handles multi-sheet workbooks with date series, cumulative formulas, constraint validation, and verification. Covers weekly queue recovery (step-down policy) and daily production recovery (multi-scenario).
---

# Production Capacity Planning

## When to Use
- Weekly queue recovery simulation with step-down policy (B1)
- Daily multi-scenario production recovery with PO deadlines (B2)
- Excel workbooks requiring cumulative formulas and date constraints
- Capacity planning across multiple scenarios/sheets

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
   - Run `scripts/verify_outputs.py` against generated files.

---

### Part B: Daily Multi-Scenario Recovery (B2)

**D1. Pre-Validate Demand**
   - Sum all PO due quantities BEFORE simulation.
   - Verify total demand is achievable within date horizon and capacity constraints.

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

**D4. Build Workbook**
   - Use `openpyxl`. One sheet per scenario.
   - Row 1-3: Headers/titles. Row 4+: Data.
   - Column B: Dates. First cell = literal `datetime.date`. Subsequent = formula `=B(prev)+1`.
   - Constants: Columns C, D, F, G, I (production, PO due).
   - Formulas: Columns E, H, J (cumulative: `=E(prev)+D(curr)-C(curr)`).

**D5. Verify Constraints**
   - Convert all openpyxl dates to `.date()` before comparison.
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

### B2: Daily Production (Harbor DC)
- Holidays: Feb 19 (Louis Riel Day), Mar 30 (Good Friday).
- Capacity: 120 → 135 after Feb 5. High-cap days: up to 170, max 22-24 days.
- openpyxl stores dates as `datetime.datetime`, not `datetime.date`. Use `.date()` conversion.
- Formula columns (E, H, J): must contain formulas, not constants.
- B4: literal `datetime.date`; B5+: formula `=B4+1`, `=B5+1`, etc.

---

## Critical Anti-Patterns

- **Date Type Mismatch**: openpyxl reads/writes dates as `datetime.datetime`. Always use `val.date() if isinstance(val, datetime.datetime) else val` for comparisons and lookups.
- **Column-to-Week Assumption**: Do NOT assume column positions. Verify header row first.
- **Row Index Assumption**: Locate rows by label, not by hardcoded index (key failure mode).
- **Iterative Parameter Tweaking**: Do NOT iterate parameters blindly. Calculate required capacity analytically.
- **Self-Verification Mismatch**: Verification code that validates its own output may diverge from test expectations. Read actual output file and compare cell-by-cell.
- **Uniform Constraint Application**: Shift-window days bypass standard caps. Isolate shift days with separate thresholds.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| KeyError on row access | Row-index assumption | Locate by label, not position |
| None rows in output | Loop overran valid range | Check loop bounds; filter None |
| Cumulative open > 0 | Total production < POs | Recalculate daily output analytically |
| Date mismatch in lookup | datetime.datetime vs datetime.date | Convert via `.date()` |
| Self-verify passes, tests fail | Verification logic mismatch | Read actual file; compare with expected |
| High-cap day count wrong | Counting before start date | Filter with `date >= threshold` |