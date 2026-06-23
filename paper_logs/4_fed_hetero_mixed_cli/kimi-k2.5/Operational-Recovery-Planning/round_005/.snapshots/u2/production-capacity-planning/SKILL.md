---
name: production-capacity-planning
description: Generate capacity planning Excel workbooks for queue recovery simulations (weekly step-down) and daily production recovery scenarios. Covers multi-sheet workbooks with date series, production constraints, cumulative formulas, and constraint validation. Use when building production schedules, PO tracking, or operational recovery analysis requiring strict numerical constraints.
---

# Production Capacity Planning

Generate Excel workbooks for operational recovery planning: queue recovery simulations with step-down policies (B1) and daily multi-scenario production recovery (B2).

## When to Use

- **Queue recovery (B1)**: Weekly simulation with step-down policy (6→5→4 days), milestone tracking
- **Daily production recovery (B2)**: Multi-scenario Excel with date series, capacity tiers, PO due tracking
- **Multi-sheet workbooks**: Identical column structure across scenarios
- **Constraint validation**: Exact totals, weekend/holiday=0, cumulative formulas

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

---

## Workflow A: Weekly Queue Recovery Simulation (B1)

### Input Structure
- Excel file with weekly demand/forecast row
- Parameters: daily capacity, 4-day threshold, initial queue, overtime formula
- **Domains**: SOC (40 weeks, 28hr/day), Radiology (49 weeks, 26hr/day), Harbor GDP (36 weeks), Returns Center (weeks 3-45, 32hr/day)
- Capacity sheets may include "Total" summary columns that must be filtered

### Step-by-Step Workflow

#### 1. Discover Sheet Structure
```python
wb = openpyxl.load_workbook(input_file)
sheet = wb.active  # or find correct sheet by name
```

#### 2. Locate Demand Row by Label (CRITICAL: NOT by position)
```python
# DO NOT assume row 5 is the demand row
demand_row = None
for row in range(1, sheet.max_row + 1):
    cell_val = sheet.cell(row=row, column=1).value
    if cell_val and any(label in str(cell_val).lower() for label in ['demand', 'forecast', 'weekly']):
        demand_row = row
        break
assert demand_row is not None, "Demand row not found"
```

#### 3. Verify Column-to-Week Mapping from Header Row (CRITICAL)
```python
# DO NOT assume column B is week 1
# Find header row and verify week labels
header_row = demand_row - 1  # typically above demand row
week_cols = {}
for col in range(2, sheet.max_column + 1):  # skip column A (labels)
    header_val = sheet.cell(row=header_row, column=col).value
    if header_val and isinstance(header_val, (int, float)):
        week_num = int(header_val)
        week_cols[week_num] = col
    # Filter non-numeric "Total" columns
    if header_val and 'total' in str(header_val).lower():
        continue  # skip summary columns

# Verify first week column
assert 1 in week_cols, "Week 1 column not found in header"
```

#### 4. Extract Valid Weeks (Filter Non-Numeric)
```python
valid_weeks = []
for week_num in sorted(week_cols.keys()):
    col = week_cols[week_num]
    val = sheet.cell(row=demand_row, column=col).value
    if isinstance(val, (int, float)) and val > 0:
        valid_weeks.append((week_num, col, val))
```

#### 5. Derive Initial Conditions
- Check for initial queue formula or cross-sheet reference
- Parse overtime formula if present

#### 6. Weekly Simulation Loop with Step-Down
```python
step_down_policy = [6, 5, 4]  # days per week threshold
current_threshold = step_down_policy[0]  # start at 6 days

for week_num, col, demand in valid_weeks:
    # Calculate production
    daily_capacity = params['daily_capacity']
    days_this_week = min(current_threshold, 5)  # cap at 5 workdays
    weekly_production = days_this_week * daily_capacity

    # Update queue
    queue = queue + demand - weekly_production

    # Check step-down trigger (queue < threshold)
    if queue < params['threshold']:
        step_down_index = min(step_down_index + 1, len(step_down_policy) - 1)
        current_threshold = step_down_policy[step_down_index]

    # Track milestones
    if queue <= 0 and 'milestone' not in tracked:
        tracked['milestone'] = week_num
```

#### 7. Generate Output Excel
- Domain-specific headers (SOC, Radiology, Harbor, Returns Center)
- N data rows (no extra None rows)
- Weeks ascending (verify sorting)
- Raw float values (no rounding)

#### 8. Generate summary.txt
- Milestone week when queue cleared
- Domain-specific narrative
- Word/sentence limits per domain

---

## Workflow B: Daily Multi-Scenario Production Recovery (B2)

### Input Structure
- Harbor DC scenario: Jan 22 – May 1 (100 days)
- Exclude Presidents Day (Feb 19) + Good Friday (Mar 30)
- Capacity: 120 → 135 after Feb 5
- Multi-resource categories (Web/DB/Network) with type-specific start dates
- PO due dates at specific calendar dates
- "On-Time" outcome requires cumulative open ≤ 0

### Step-by-Step Workflow

#### 1. Parse Constraints
```python
constraints = {
    'date_range': (date(2018, 1, 22), date(2018, 5, 1)),
    'holidays': [date(2018, 2, 19), date(2018, 3, 30)],
    'capacity_transition': date(2018, 2, 5),
    'capacity_before': 120,
    'capacity_after': 135,
    'high_capacity': 170,
    'categories': {
        'Web': {'start': date(2018, 1, 22), 'total': 5520, 'po_dates': {...}},
        'DB': {'start': date(2018, 3, 1), 'total': 4035, 'po_dates': {...}},
        'Network': {'start': date(2018, 1, 22), 'min': 1200}
    }
}
```

#### 2. Build Calendar (CRITICAL: Pre-Validation)
```python
from datetime import date, timedelta

def build_calendar(start, end, holidays):
    """Generate working days excluding weekends and holidays."""
    working_days = []
    current = start
    while current <= end:
        if current.weekday() < 5 and current not in holidays:
            working_days.append(current)
        current += timedelta(days=1)
    return working_days

working_days = build_calendar(constraints['date_range'][0],
                              constraints['date_range'][1],
                              constraints['holidays'])

# VALIDATE: Check total demand matches expected totals
total_web_po = sum(constraints['categories']['Web']['po_dates'].values())
assert total_web_po == constraints['categories']['Web']['total'],
    f"PO total {total_web_po} != expected {constraints['categories']['Web']['total']}"
```

#### 3. Calculate Distribution (Analytical, NOT Iterative)
```python
# DO NOT iterate/tweak parameters - use analytical formula
def distribute_total(total, working_days, start_date, capacity_func):
    """Distribute total across valid working days."""
    # Filter days on/after category start
    valid_days = [d for d in working_days if d >= start_date]

    if not valid_days:
        return {}

    # Calculate base distribution
    units_per_day, remainder = divmod(total, len(valid_days))

    # Front-load remainder (first N days get +1)
    distribution = {}
    for i, day in enumerate(valid_days):
        value = units_per_day + (1 if i < remainder else 0)
        # Apply capacity cap if needed
        cap = capacity_func(day)
        distribution[day] = min(value, cap)

    return distribution

def capacity_func(day, is_high_cap=False):
    if is_high_cap:
        return 170
    elif day >= date(2018, 2, 5):
        return 135
    else:
        return 120
```

#### 4. Build Multi-Sheet Workbook
```python
wb = openpyxl.Workbook()
wb.remove(wb.active)  # remove default sheet

for scenario_name in ['Scenario 1', 'Scenario 2', 'Scenario 3']:
    ws = wb.create_sheet(title=scenario_name)

    # Row 1: Blank/title
    # Row 2: Merged headers (category names)
    # Row 3: Column headers ("Date", "Web Prod", "Web PO", "Web Cum", ...)
    # Row 4+: Data rows (start at row 4)

    ws['B3'] = 'Date'  # Column B for dates
    ws['C3'] = 'Web Planned Production'
    ws['D3'] = 'Web PO Due'
    ws['E3'] = 'Web Cumulative Open'
    # ... repeat for DB and Network columns

    # First date (B4) = literal datetime.date
    ws['B4'] = date(2018, 1, 22)  # datetime.date, NOT datetime.datetime

    # Subsequent dates (B5+) = formula
    for row in range(5, 104):
        ws[f'B{row}'] = f'=B{row-1}+1'

    # Daily production = constants (C, F, I columns)
    # PO due = constants (D, G columns)
    # Cumulative = formulas (E, H, J columns)
```

#### 5. Write Formula Columns
```python
# Cumulative PO Variance (Column E for Web)
# Row 4: first cumulative = PO due - Production
ws['E4'] = '=D4-C4'

# Row 5+: subsequent cumulative = previous + new PO - new production
for row in range(5, 104):
    ws[f'E{row}'] = f'=E{row-1}+D{row}-C{row}'
```

#### 6. Verify Weekend/Holiday Production = 0
```python
for day, row in date_to_row.items():
    if day.weekday() >= 5 or day in holidays:
        # Force production = 0
        ws[f'C{row}'] = 0
        ws[f'F{row}'] = 0
        ws[f'I{row}'] = 0
```

#### 7. Validate Totals (CRITICAL: Before Declaring Complete)
```python
# Verify total production equals target
web_total = sum(ws[f'C{row}'].value or 0 for row in range(4, 104))
assert web_total == 5520, f"Web total {web_total} != 5520"

# Verify formula columns
assert str(ws['E4'].value).startswith('='), "E4 should be formula"
assert str(ws['E5'].value).startswith('='), "E5 should be formula"

# Verify date range
first_date = ws['B4'].value
last_date = ws['B103'].value
assert first_date == date(2018, 1, 22), "Start date wrong"
assert last_date == date(2018, 5, 1), "End date wrong"
```

#### 8. Generate summary.md
- Sections with **bold** field labels
- Scenario comparison summary
- "On-Time" outcome validation

---

## Date Handling (CRITICAL: u0 Best Pattern)

### datetime.datetime vs datetime.date Conversion

```python
from datetime import datetime, date

# openpyxl reads/writes dates as datetime.datetime
# Always convert to date before comparison

def to_date(val):
    """Convert openpyxl date value to date object."""
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    return None

# Usage in comparisons
cell_val = ws.cell(row=row, column=col).value
cell_date = to_date(cell_val)
if cell_date == expected_date:
    # ...
```

### First Date Cell = Literal, Subsequent = Formula

```python
# Row 4: literal datetime.date
ws['B4'] = date(2018, 1, 22)  # NOT datetime(2018, 1, 22, 0, 0)

# Row 5+: formula reference
ws['B5'] = '=B4+1'
```

---

## Shift-Window Constraint Isolation (u0 Pattern)

When a scenario has "high-capacity shift days" (e.g., 22 days on/after Feb 1 with capacity up to 170):

```python
# DO NOT apply standard daily caps to shift days
# Isolate shift days and verify separately

shift_days = [d for d in working_days
              if d >= date(2018, 2, 1) and d <= date(2018, 2, 24)]

for day in working_days:
    if day in shift_days:
        # Shift days: separate threshold (up to 170)
        cap = 170
    else:
        # Standard days: tiered capacity
        cap = 135 if day >= date(2018, 2, 5) else 120
```

---

## Verification Checklist (u1 Pattern)

### Before Claiming Complete:
1. **Open and re-read the file** - Don't just trust write operations
2. **Check formula propagation** - Verify first and last row formulas
3. **Validate date coverage** - Confirm all required dates present
4. **Test constraint compliance** - Run programmatic checks on output
5. **Compare against requirements** - Re-read task requirements after creation

### Read Back Actual Output:
```python
# DO NOT assume write operations succeeded
wb = openpyxl.load_workbook(output_path)
ws = wb[scenario_name]

# Verify each constraint programmatically
for row in range(4, 104):
    date_val = ws[f'B{row}'].value
    if date_val and to_date(date_val).weekday() >= 5:
        prod_val = ws[f'C{row}'].value
        assert prod_val == 0, f"Row {row}: weekend production should be 0"
```

---

## Anti-Patterns

### Position Assumption (kimi Failure Mode)
- **DO NOT assume** row 5 is the demand row
- **DO NOT assume** column B is week 1
- **DO NOT skip header verification** - always inspect header row before extracting data

### Iterative Debugging/Tweaking (kimi Failure Mode)
- **DO NOT iterate parameters blindly** when totals don't match
- **DO use analytical calculation**: `divmod(total, len(working_days))` gives exact distribution
- **DO pre-validate totals**: verify `sum(PO dates) == expected total` BEFORE simulation

### Date Type Mismatch
- **DO NOT compare** datetime.datetime directly with date objects
- **DO convert** all openpyxl date values with `.date()` before comparison

### Formula vs Constant Confusion
- **DO NOT write** calculated values in formula columns
- **DO write** formula strings starting with `=` in formula columns
- **DO write** numeric literals in constant columns

### Self-Verification Logic Mismatch
- **DO NOT trust** your verification code matches test requirements
- **DO re-read** task requirements after creation
- **DO compare** cell-by-cell with expected values

### pandas vs openpyxl for Formula Control
- **DO NOT use** pandas ExcelWriter when exact formula strings matter
- **DO use** openpyxl directly: `ws['E5'] = '=E4+D5-C5'`

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| KeyError on row access | Row-index assumption | Find row by label, not position |
| Totals off by small number | Integer division remainder ignored | Use `divmod()` and distribute remainder |
| Cumulative open > 0 | Total production < total POs | Pre-validate totals before simulation |
| Date comparison fails | datetime.datetime vs date mismatch | Convert all values with `.date()` |
| Formulas show as text | Written as strings not formulas | Ensure value starts with `=` |
| PO lookup returns 0/None | Date key mismatch | Use `.date()` for dictionary lookups |
| Weekend values non-zero | Not enforcing constraint | Explicitly set weekend/holiday cells to 0 |
| Self-verify passes, tests fail | Verification logic mismatch | Re-read task requirements, compare cell-by-cell |
| Timeout during simulation | Iterative parameter tweaking | Use analytical calculation, not trial-and-error |

---

## Helper Scripts

- `calculate_catchup.py`: Weekly catch-up simulation with step-down policy
- `daily_recovery.py`: Daily multi-scenario production recovery
- `validate_workbook.py`: Reusable validation helpers for workbook verification

Run scripts with explicit flags:
```bash
python3 scripts/calculate_catchup.py --input input.xlsx --output output.xlsx --params params.json
python3 scripts/daily_recovery.py --constraints constraints.json --output output.xlsx
```

---

## Reference Files

- `variant-patterns.md`: Domain-specific patterns (SOC, Radiology, Harbor, Returns Center)
- `calculation-details.md`: Capacity rules, step-down formulas, edge cases
- `production-planning-patterns.md`: Scenario patterns, formula templates, validation thresholds