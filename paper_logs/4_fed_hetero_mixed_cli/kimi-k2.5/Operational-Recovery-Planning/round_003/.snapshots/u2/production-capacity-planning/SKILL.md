---
name: production-capacity-planning
description: Calculate manufacturing catch-up schedules stepping down from 6-day overtime weeks to 4-day normal operations as backlog clears. Use when analyzing Excel capacity sheets with weekly demand data, calculating backlog clearance timelines, and determining optimal work schedules (4/5/6-day weeks) based on demand thresholds.
---

# Production Capacity Planning

Generate catch-up production schedules that transition from maximum overtime capacity to normal operations as backlog clears.

## Quick Start

If pandas is missing in system Python:
```bash
pip install pandas openpyxl --break-system-packages -q
```

Run the calculator (see `scripts/calculate_catchup.py`):
```bash
python3 scripts/calculate_catchup.py <excel_file> <demand_row_label> <backlog_value_or_label>
```

## Data Extraction

Excel capacity sheets often contain mixed types (numeric data alongside "Total" labels).

```python
import pandas as pd

df = pd.read_excel('capacity_sheet.xlsx', header=None)

# Locate by content, not position
weeks = pd.to_numeric(df.iloc[3, 1:], errors='coerce')
valid_mask = weeks.notna()
weeks = weeks[valid_mask].astype(int)

demand_row = df[df[0] == 'MIG weld Demand Total'].iloc[0, 1:]
demand = pd.to_numeric(demand_row[valid_mask], errors='coerce')
```

**Critical**: Always filter with `pd.to_numeric(errors='coerce')` to exclude summary columns like "Total" that cause type errors in comparisons.

## Calculation Logic

**Capacity Rules:**
- 6-day week: 180 hrs + 20 OT hrs
- 5-day week: 150 hrs + 10 OT hrs
- 4-day week: 120 hrs + 0 OT hrs

**Step-Down Logic:**
1. Start with 6-day weeks until `backlog <= 0`
2. Switch to 5-day weeks while monitoring for demand spikes that recreate backlog
3. Switch to 4-day weeks when demand stabilizes below 120 hrs/week

See `references/calculation-details.md` for full algorithm and edge cases.

## Output Format

Generate two files:
1. **Excel**: Columns `Week`, `Days Worked`, `Scheduled Demand`, `Weekly Capacity`, `Start of Week Past Due`, `End of Week Backlog`, `Overtime Hours`
2. **Summary text**: `First_Week_5_Days`, `First_Week_4_Days`, and narrative summary

## Anti-Patterns

- **Don't hardcode row indices**: Use label-based lookup (`df[df[0] == 'Label']`) because sheet layouts vary
- **Don't assume monotonic step-down**: Demand spikes can force temporary return to 6-day weeks after stepping down (e.g., Week 10 → 5 days, Week 11 → 6 days due to high demand)
- **Don't mix types in comparisons**: Always cast Excel columns to numeric before `>=` or `<` operations

## Validation Checklist

- [ ] Week 4 starts with correct initial backlog (extracted from "MIG PLT 2" or similar past-due row)
- [ ] 6-day weeks continue until backlog first hits zero or negative
- [ ] First 5-day week number matches `First_Week_5_Days` in summary
- [ ] First 4-day week occurs when demand < 120 and no backlog exists
- [ ] Negative backlog values are capped at zero for "Start of Week Past Due" in subsequent weeks