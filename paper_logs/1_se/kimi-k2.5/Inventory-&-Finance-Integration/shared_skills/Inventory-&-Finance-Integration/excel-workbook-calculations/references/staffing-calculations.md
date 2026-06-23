# Staffing and Resource Planning Calculations

Common formulas for workforce planning, shift scheduling, and coverage projections.

## Core Calculations

### Coverage Days
```python
coverage_days = current_hours / daily_required_hours
# e.g., 320 hours / 80 hours/day = 4 days coverage
```

### Projected Understaff Date
```python
from datetime import timedelta

projected_understaff_date = asof_date + timedelta(days=int(coverage_days))
# Or use math.floor for conservative estimate
```

### Remaining Period Demand
```python
remaining_days = (planning_horizon_end - asof_date).days
remaining_demand_hours = daily_required_hours * remaining_days
```

### Additional Hours Needed
```python
additional_hours = max(0, remaining_demand_hours - current_hours - incoming_hours)
# incoming_hours: scheduled shifts within the planning horizon
```

### Shift Blocks (Round-Up)
```python
import numpy as np

shift_blocks_required = int(np.ceil(additional_hours / hours_per_shift_block))
# e.g., 1616 hours / 24 hours/block = 67.33 -> 68 blocks
```

### Rounding Detection
```python
exact_blocks = additional_hours / hours_per_shift_block
rounding_applied = (exact_blocks != shift_blocks_required) and additional_hours > 0
```

### Required Shift Start Date
```python
required_shift_start = projected_understaff_date
# When coverage runs out
```

### Earlier Shift Required Check
```python
earlier_shift_required = (
    earliest_scheduled_shift_date > required_shift_start 
    if earliest_scheduled_shift_date and required_shift_start 
    else False
)
# True if scheduled arrival is after coverage runs out
```

## Handling Edge Cases

### Zero Daily Requirement
```python
if daily_required_hours == 0:
    coverage_days = None
    projected_understaff_date = None
    additional_hours = 0
    shift_blocks_required = 0
```

### No Incoming Shifts
```python
unit_incoming = df_incoming[df_incoming['Care_Unit'] == unit]
incoming_hours = unit_incoming['Staff Hours'].sum()
earliest_scheduled = unit_incoming['Shift Date'].min() if len(unit_incoming) > 0 else None
```

### Date Filtering Within Horizon
```python
# Only count shifts that occur before planning horizon end
incoming_by_aug31 = unit_incoming[unit_incoming['Shift Date'] <= planning_horizon_end]
incoming_hours = incoming_by_aug31['Staff Hours'].sum()
```

## Multi-Unit Processing Pattern

```python
results = []
for _, row in df_staffing.iterrows():
    unit = row['Care_Unit']
    current = row['Current_Staff_Hours']
    daily_req = row['Daily_Required_Hours']
    
    # Skip header-like rows
    if unit == 'Care_Unit' or pd.isna(unit):
        continue
    
    # Calculations...
    results.append({
        'Care_Unit': unit,
        'Current_Coverage_Days': coverage_days,
        'Projected_Understaff_Date': projected_understaff_date,
        'Shift_Blocks_Required_Rounded_Up': shift_blocks,
        'Earlier_Shift_Required': earlier_shift_required,
        # ... other fields
    })

df_results = pd.DataFrame(results)
```
