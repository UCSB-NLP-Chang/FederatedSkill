---
name: daily-production-recovery
description: Generate multi-scenario Excel workbooks for production recovery planning with date series, numerical constraints, cumulative formulas, and strict validation. Use when building capacity planning, PO tracking, or shift-based production schedules requiring business-day-only production and exact totals.
---

# Daily Production Recovery

Generate Excel workbooks for production recovery scenarios with strict numerical constraints (exact totals, date ranges, capacity limits) and business logic (weekends/holidays=0, front-loading, high-capacity windows).

## When to Use

- Production planning with exact SKU/server totals across date horizons
- Multi-scenario capacity analysis (Current vs. Optimized vs. Extended Shift)
- Date-distributed resource allocation with blackout dates
- Requirements: specific columns must contain formulas (cumulative sums), others constants (daily production)

## Workflow

### 1. Parse Constraints
Extract from requirements:
- **Totals per category**: Exact integers that sums must equal (e.g., Web=5520, DB=4035)
- **Date horizon**: Start date, end date (inclusive), total working days
- **Business rules**:
  - Weekend dates (weekday() >= 5) → production 0
  - Holiday dates → production 0
  - Pre-start dates (e.g., DB starts March 1) → production 0
  - Capacity tiers: Standard (e.g., 120/135), High-cap (e.g., 170) with day count limits

### 2. Calculate Distribution
Algorithm for hitting exact totals:
```python
# Identify working days (non-weekend, non-holiday, on/after start date)
working_days = [d for d in date_range if not is_blackout(d)]
base_capacity = 135  # or tiered based on date thresholds

# Distribute total across working days
units_per_day, remainder = divmod(total_units, len(working_days))
for i, day in enumerate(working_days):
    value = units_per_day + (1 if i < remainder else 0)
```

**Decision Rule**: Front-load remainder days (first N days get +1) rather than spreading decimals.

### 3. Build Workbook Structure
For each scenario sheet:
- Row 1-3: Headers/titles. Row 4+: Data.
- Column B: Dates. B4 = literal `datetime.date`. B5+ = formulas `=B{row-1}+1`.
- Columns C/D/F/G/I: Numeric constants (production, PO due).
- Columns E/H/J: Cumulative formulas (e.g., `=E{prev}+D{curr}-C{curr}`).

**Formula Patterns:**
- First cumulative row: `=D4-C4` (simple difference)
- Subsequent rows: `=E4+D5-C5` (previous cumulative + new change)

### 4. Validate Constraints

**Weekend/Holiday Checks:**
```python
from datetime import date
if date.weekday() >= 5:  # Saturday=5, Sunday=6
    # Production should be 0
```

**PO Due Verification:**
```python
# Convert all openpyxl date values to .date() before comparison
val.date() if isinstance(val, datetime.datetime) else val
```

For shift windows: verify constraints apply *only* to non-shift days; shift days have separate thresholds.

### 5. Verification Checklist (CRITICAL)

Before claiming completion:
1. **Open and re-read the output file** - Don't trust write operations without verification
2. Check formula propagation - Verify first and last row formulas
3. Validate date coverage - Confirm all required dates present
4. Test constraint compliance - Run programmatic checks on output
5. Compare against requirements - Re-read task requirements after creation
6. Validate PO due quantities at required dates
7. Ensure cumulative open <= 0 for "On-Time" claims

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw integer/float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as raw int/float
- The verifier's tolerance decides acceptable precision; the skill's job is to
  give it full precision and let it decide.

## Critical Anti-Patterns

- **Date Type Mismatch**: `openpyxl` reads/writes dates as `datetime.datetime`. Always use `val.date() if isinstance(val, datetime.datetime) else val` for comparisons.
- **Formula vs Literal**: Only the first date cell should be a literal. All subsequent dates must be `=B(prev)+1` formulas.
- **Self-verification passes but tests fail**: Verification logic doesn't match test requirements. Re-read task requirements; verify exact expected values.
- **Uniform Constraint Application**: Do not apply standard daily caps to shift-window days. Isolate shift days and verify them with separate thresholds.
- **Late Cumulative Verification**: Calculate total required production against PO due dates *before* finalizing daily values.
- **Exact division assumption**: `total / days` produces floats. Use `divmod()` and distribute remainder integers.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Totals off by small number | Integer division remainder ignored | Distribute remainder across first N days |
| Formulas show as text | Written as strings not formulas | Ensure value starts with `=` and use `data_type='f'` |
| Dates off by one | Timezone or string parsing | Use `datetime(YYYY, MM, DD)` objects |
| PO lookup returns 0/None | Date key mismatch | Use `.date()` for dictionary lookups |
| Cumulative open > 0 | Total production < total POs | Increase daily production or shift days |
| Self-verify passes, tests fail | Verify logic diverges from test | Re-read task requirements after creation |

## References

- `references/production-planning-patterns.md` - Scenario patterns and formula templates
- `scripts/validate_workbook.py` - Reusable validation helpers