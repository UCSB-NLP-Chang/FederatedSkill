---
name: queue-recovery-planning
description: Create workforce capacity plans to clear alert/ticket backlogs over multi-week horizons with step-down scheduling (6→5→4 day weeks). Use for SOC queue recovery, helpdesk backlog clearance, or any Excel-based capacity planning requiring constrained executive summaries (strict word/sentence counts).
---

# Queue Recovery Planning with Excel

## When to use
- Input is an Excel file with weekly demand forecasts (e.g., alert load, ticket volume)
- Must model backlog clearance week-by-week with varying daily capacity
- Policy requires stepping down workdays as backlog decreases (e.g., 6-day weeks → 5-day → 4-day)
- Output requires both detailed Excel worksheet and a constrained text summary (specific word count, sentence count, mandatory milestone mentions)

## Workflow

### Step 1: Read Input Data
Use `openpyxl` to read the input Excel file:
```python
import openpyxl
wb = openpyxl.load_workbook('/path/to/input.xlsx')
ws = wb.active
# Extract demand row (typically a row with weekly values)
demand_row = next(ws.iter_rows(min_row=3, max_row=3, values_only=True))
weekly_demand = list(demand_row[1:])  # Skip label column, get 40 values
```

### Step 2: Initialize Simulation State
Maintain two queue values:
- `actual_queue`: Signed carryover (allows negative buffer). Carry this forward week-to-week.
- `display_queue`: `max(0, actual_queue)` for reporting columns only.

```python
actual_queue = 0  # Start at 0, carry signed state forward
first_5day_week = None
first_4day_week = None
```

### Step 3: Run Weekly Loop
For each week (1..40), apply the step-down policy:

```python
STANDARD_DAILY_CAPACITY = 28  # Analyst hours per day
OVERTIME_HOURS = {6: 16, 5: 8, 4: 0}

results = []
for week_num, demand in enumerate(weekly_demand, start=1):
    # Determine days based on policy
    if actual_queue > 0:
        days = 6
    elif demand > 112:  # 4-day capacity threshold
        days = 5
    else:
        days = 4

    # Track milestones (first transition to each state)
    if first_5day_week is None and days == 5 and actual_queue <= 0:
        first_5day_week = week_num
    if first_4day_week is None and days == 4:
        first_4day_week = week_num

    # Calculate weekly metrics
    capacity = days * STANDARD_DAILY_CAPACITY
    start_queue = actual_queue
    actual_queue = start_queue + demand - capacity  # Signed, allows negative

    results.append({
        'week': week_num,
        'days': days,
        'demand': demand,
        'capacity': capacity,
        'start_queue': start_queue,
        'end_queue': actual_queue,
        'overtime': OVERTIME_HOURS[days]
    })
```

### Step 4: Write Excel Output
Create `plan.xlsx` with sheet "Plan" and exactly 40 data rows:
```python
wb_out = openpyxl.Workbook()
ws_out = wb_out.active
ws_out.title = "Plan"

headers = [
    "Week", "On-Call Days", "Forecast Alert Load (Analyst Hrs)",
    "Weekly Triage Capacity (Analyst Hrs)", "Start-of-Week Alert Queue (Analyst Hrs)",
    "End-of-Week Alert Queue/Buffer (Analyst Hrs)", "Burnout Overtime Hours"
]
ws_out.append(headers)

for r in results:
    row = [
        r['week'], r['days'], round(r['demand'], 2), round(r['capacity'], 2),
        round(r['start_queue'], 2), round(r['end_queue'], 2), r['overtime']
    ]
    ws_out.append(row)

wb_out.save('/path/to/plan.xlsx')
```

### Step 5: Write Text Summary
Create `summary.txt` with exactly 3 lines, strict format:
```
First_Week_5_Days: <int>
First_Week_4_Days: <int>
Summary: <exactly 2 sentences, ≤31 words total, mentioning Week X and Week Y milestones>
```

Example:
```
First_Week_5_Days: 4
First_Week_4_Days: 7
Summary: The backlog clears by Week 4, triggering transition to 5-day weeks. Demand stabilizes enough for 4-day weeks starting Week 7.
```

### Step 6: Verify Outputs
Run the verification script before finalizing:
```bash
python3 scripts/verify_outputs.py summary.txt plan.xlsx
```

## Output Precision
Excel numeric cells must display exactly 2 decimal places. The verifier expects clean 2-decimal values, not floating-point artifacts.

- **DO**: Use `round(value, 2)` when writing to Excel cells to prevent artifacts like `4.499999972`
- **DO NOT**: Write raw floats directly — they may have floating-point drift
- **Intermediate calculations**: Use full precision (no rounding) to avoid cumulative errors
- **Display only**: Round at the final write step, not during calculation

Example of correct pattern:
```python
# Good: full precision during calc, round at display
end_queue = actual_queue + demand - capacity  # full precision
ws.cell(row=r, column=6, value=round(end_queue, 2))  # round for display

# Bad: rounding during calculation causes drift
capacity = round(days * 28, 2)  # WRONG — round at display, not calc
```

## Known Invariants (by sub-task)

### queue-recovery-simulation
- End-of-Week Queue/Buffer column may contain negative values — do NOT clamp to zero
- `actual_queue` (signed) determines policy transitions; `display_queue` (clamped) is for output only
- Summary line 3 must be exactly 2 sentences, ≤31 words total
- Lines 1-2 must match format `First_Week_N_Days: <int>` exactly (no extra spaces)
- Excel must have exactly 40 data rows (Weeks 1-40), plus header row
- Column headers must match required naming exactly (check spelling and capitalization)

## Anti-Patterns
- **Do NOT clamp `actual_queue` to zero.** Negative values represent "ahead of schedule" buffer and must carry forward to determine step-down eligibility correctly.
- **Do NOT hardcode milestone week numbers.** Calculate dynamically based on policy rules; specific weeks vary by input data.
- **Do NOT count sentences by splitting on `.` alone.** Use `text.count('. ')` or similar to handle the space after periods.
- **Do NOT skip the verify step.** Run `verify_outputs.py` before finalizing to catch constraint violations.
