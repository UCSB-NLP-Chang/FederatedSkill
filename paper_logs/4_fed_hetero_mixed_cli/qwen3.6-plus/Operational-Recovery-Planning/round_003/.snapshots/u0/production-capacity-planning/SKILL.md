---
name: production-capacity-planning
description: Calculate manufacturing catch-up schedules stepping down from 6-day overtime weeks to 4-day normal operations as backlog clears. Use when analyzing Excel capacity sheets with weekly demand data, calculating backlog clearance timelines, and determining optimal work schedules (4/5/6-day weeks) based on demand thresholds.
---

# Production Capacity Planning

Generate catch-up production schedules that transition from maximum overtime capacity to normal operations as backlog clears.

## When to Use
- Tasks requiring weekly production/capacity planning spreadsheets
- Backlog clearance calculations with overtime
- Step-down capacity transitions (e.g., 6→5→4 days/week)
- Manufacturing catch-up scenarios with Excel deliverables
- Excel sheets with weekly demand data in columns

## Workflow

### 1. Discover sheet structure
```python
import openpyxl
wb = openpyxl.load_workbook('path.xlsx', data_only=True)
print(wb.sheetnames)
ws = wb['SheetName']
print(f'Max row: {ws.max_row}, Max col: {ws.max_column}')
```

### 2. Locate target row by label (not position)
```python
for row in ws.iter_rows(min_row=1, max_row=ws.max_row, values_only=False):
    if row[0].value == 'Exact Label':
        values = [c.value for c in row[1:]]
        break
```

### 3. Verify column-to-week mapping (CRITICAL)
**Do not assume** the number of values matches the expected time range. This is the #1 failure pattern.

```python
# Verify header row contains week numbers
header_row = [c.value for c in ws[3]]  # adjust row number
print(f'Header weeks: {header_row[1:]}')  # skip first column label

# Count expected periods from header
valid_weeks = [w for w in header_row[1:] if isinstance(w, (int, float))]
print(f'Valid week columns: {len(valid_weeks)}')
print(f'Extracted values count: {len(values)}')

# MUST match before proceeding
if len(values) != len(valid_weeks):
    # Inspect header to find the correct slice - do NOT drop values blindly
    print("MISMATCH - inspect header row to determine correct columns")
```

**Anti-pattern**: "Do not drop values without verifying". If extracted count ≠ expected, inspect headers to find the correct slice. Do not assume extra values are "future weeks" without checking.

### 4. Extract data with type filtering
Excel capacity sheets often contain mixed types (numeric data alongside "Total" labels).

```python
import pandas as pd
df = pd.read_excel('capacity_sheet.xlsx', header=None)

# Filter to numeric, exclude "Total" columns
weeks = pd.to_numeric(df.iloc[3, 1:], errors='coerce')
valid_mask = weeks.notna()
weeks = weeks[valid_mask].astype(int)

demand_row = df[df[0] == 'MIG weld Demand Total'].iloc[0, 1:]
demand = pd.to_numeric(demand_row[valid_mask], errors='coerce')
```

### 5. Derive initial conditions
- Read task specification for initial state formulas
- Cross-reference with sheet data (e.g., "Grand Total" rows, prior week carryover)
- Compute from the given formula, not from assumptions

### 6. Simulate week-by-week with step-down logic
Run the calculator script:
```bash
python3 scripts/calculate_catchup.py <excel_file> <demand_row_label> <backlog_source>
```

**Capacity Rules (default):**
- 6-day week: 180 hrs + 20 OT hrs = 200 total
- 5-day week: 150 hrs + 10 OT hrs = 160 total
- 4-day week: 120 hrs + 0 OT hrs = 120 total

**Step-Down Logic:**
1. Start with 6-day weeks until `backlog <= 0`
2. Switch to 5-day weeks; monitor for demand spikes that recreate backlog
3. Switch to 4-day weeks when demand stabilizes below 120 hrs/week

See `references/calculation-details.md` for full algorithm and edge cases.

### 7. Generate outputs
**Excel:**
- Columns: `Week`, `Days Worked`, `Scheduled Demand`, `Weekly Capacity`, `Start of Week Past Due`, `End of Week Backlog`, `Overtime Hours`
- No extra None/empty rows at end
- Sheet name matches specification exactly

**Summary text:**
- Key-value format: `First_Week_5_Days: <value>`
- Word/sentence count constraints per specification

### 8. Validate before submission
Run verification script:
```bash
python3 scripts/verify_outputs.py <plan.xlsx> <summary.txt> [start_week] [end_week]
```

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Anti-Patterns
- **Do not drop values without verifying**: If extracted count ≠ expected, inspect headers first
- **Do not round during computation**: Keep full float precision; round only at output time per verifier tolerance
- **Do not assume column alignment**: Column B is not always week 1. Verify from header row
- **Do not hardcode row indices**: Use label-based lookup because sheet layouts vary
- **Do not assume monotonic step-down**: Demand spikes can force temporary return to 6-day weeks
- **Do not mix types in comparisons**: Always cast Excel columns to numeric before `>=` or `<` operations
- **Do not skip verification**: Always run a post-generation check before marking complete

## Known invariants (by sub-task)

### SOC queue recovery
- 40 weeks, 28hr/day capacity
- Week 4 start, initial backlog from sheet cross-ref

### Radiology queue recovery
- 49 weeks, 26hr/day capacity
- Weeks 6-54 range
- Header row at row 3 or 4 typically

### Harbor GDP
- 36 weeks

### Returns Center
- Weeks 3-45, 32hr/day capacity
- Demand may be sum of multiple rows (Exception Review + Standard Return Intake)

## Common Pitfalls
- **Extra None/empty rows**: When using openpyxl, verify row count matches expected
- **Header placement**: Ensure headers in row 1, data starts row 2
- **Sheet naming**: Use exact sheet name from specification
- **Backlog sign convention**: Negative backlog = buffer capacity available

## Scripts
- `scripts/calculate_catchup.py` — main calculation script
- `scripts/verify_outputs.py` — post-generation validation

## References
- `references/calculation-details.md` — capacity rules, step-down logic, edge cases