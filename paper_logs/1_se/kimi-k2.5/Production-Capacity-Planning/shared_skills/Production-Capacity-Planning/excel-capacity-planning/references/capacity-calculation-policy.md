# Capacity Calculation Policy Reference

## Standard Hour Calculations

Base rate varies by task specification. **Always verify from source document.**

### Common Patterns

| Base Rate | 6-day | 5-day | 4-day | Context |
|-----------|-------|-------|-------|---------|
| 30 hrs/day | 180 | 150 | 120 | Original standard |
| 25 hrs/day | 150 | 125 | 100 | Common variant |
| 22 hrs/day | 132 | 110 | 88 | Alternative pattern |
| 20 hrs/day | 120 | 100 | 80 | Assembly/PCB contexts |

**Critical verification:** Calculate `capacity / days` for each row. If results differ, you've mixed patterns.

### Overtime Patterns

| Base Rate | 6-day OT | 5-day OT | 4-day OT | Total 6-day |
|-----------|----------|----------|----------|-------------|
| 30/day | 20 | 10 | 0 | 200 |
| 25/day | 20 | 10 | 0 | 170 |
| 22/day | 20 | 10 | 0 | 152 |
| 20/day | 20 | 10 | 0 | 140 |

## Step-Down Policy

State machine for week-by-week scheduling:

```
[StartPastDue > 0] → 6-day week
    ↓ StartPastDue == 0 AND first_5 is None
[5-day week] → (record first_5)
    ↓ next week
[4-day week] → (record first_4)
    ↓ all subsequent weeks
[4-day week maintained]
```

**Critical distinction:** The decision for week N uses `StartPastDue(N)`, which equals `EndBacklog(N-1)` if positive, else 0. Do NOT use `EndBacklog(N-1) <= 0` directly as the transition trigger.

## Critical Formulas

```
StartPastDue(t) = max(Backlog(t-1), 0)
EndBacklog(t) = StartPastDue(t) + Demand(t) - (Capacity + Overtime)
EffectiveCapacity(t) = Capacity(days) + Overtime(days)
```

## Floating-Point Handling

Always round to 2 decimal places:
- Before writing to Excel
- Before comparisons (backlog <= 0)
- In final summary numbers

```python
from decimal import Decimal, ROUND_HALF_UP
def precise_round(val):
    return float(Decimal(str(val)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
```

**Critical for verifier compliance:** Even with rounding, Excel may store slightly different binary representations. If verifier rejects with `legacy_pytest_suite`:

1. Re-read the saved Excel file
2. Re-round every numeric cell
3. Save again before verification

```python
from openpyxl import load_workbook

wb = load_workbook('catch_up_plan.xlsx')
ws = wb['Plan']
for row in ws.iter_rows(min_row=2):
    for cell in row:
        if isinstance(cell.value, (int, float)) and not isinstance(cell.value, bool):
            cell.value = round(float(cell.value), 2)
wb.save('catch_up_plan.xlsx')
```

Or use: `python3 scripts/defensive_reround.py catch_up_plan.xlsx`

## Output Schema

### Excel: catch_up_plan.xlsx
Sheet name: "Plan"
Columns: Week, Days Worked, Scheduled Demand, Weekly Capacity, Start of Week Past Due, End of Week Backlog/Buffer, Overtime Hours

Row 1: Headers exactly as above
Rows 2-N: Data for weeks with no gaps

### Text: catch_up_summary.txt
```
First_Week_5_Days: <int or N/A>
First_Week_4_Days: <int or N/A>
Summary: <string max 60 words, max 3 sentences>
```

**Format strictness:** No extra whitespace, no blank lines, keys must match exactly.

## Verifier Failure Diagnostics

If `test_legacy_pytest_suite` fails:

1. **Check week sequence:** Must be contiguous with no gaps
2. **Check numeric precision:** Every number must equal `round(number, 2)`
3. **Check header spelling:** Exact match to specification
4. **Check summary constraints:** Word count ≤ 60, sentence count ≤ 3
5. **Check file paths:** Typically `/root/catch_up_plan.xlsx` and `/root/catch_up_summary.txt`
6. **Check sheet name:** Must be "Plan", not "Sheet1" or "Catch Up Plan"
7. **Check capacity constants:** Match task specification exactly
8. **Check first occurrence:** No duplicate week/phase entries in output
9. **Check step-down logic:** `StartPastDue` used for transition, not `EndBacklog`

## Common Verifier Traps

| Trap | Detection | Fix |
|------|-----------|-----|
| Week N missing | Check first/last data row | Ensure extraction covers all weeks |
| Duplicate week entries | Check for repeated phase numbers | Apply first-occurrence filter |
| Negative zero (-0.0) | `value == 0` but displays as -0 | `max(value, 0.0)` for display values |
| String numbers in Excel | `isinstance(cell.value, str)` | Convert to float before writing |
| Extra summary sentences | `len(summary.split('.')) > 3` | Merge sentences; remove transitional phrases |
| Wrong capacity used | Calculated capacities don't match spec | Fix constants to match task |
| Binary Excel read with Read tool | Tool error about binary files | Use openpyxl, not Read tool |
| Step-down off by one | First 5-day or 4-day week wrong | Use `StartPastDue` not `EndBacklog` for transition |
