# Step-Down Policy Variants

## Variant A: State Machine (Standard)

Most common in manufacturing capacity planning. Uses `StartPastDue` to determine days.

### Decision Logic
```python
def determine_days_state_machine(start_past_due, first_5, first_4):
    if start_past_due > 0:
        return 6  # Must clear backlog first
    elif first_5 is None:
        return 5  # First week with no starting backlog
    elif first_4 is None:
        return 4  # Week after first 5-day
    else:
        return 4  # Maintain
```

### Characteristics
- Always produces First_Week_5_Days (unless never clears backlog)
- 6-day → 5-day → 4-day sequence guaranteed
- Transition trigger: `StartPastDue == 0`

### When Used
- Original capacity planning tasks
- Tasks mentioning "step down after backlog clears"
- Standard 30/25/22/20 hrs/day patterns

## Variant B: Threshold-Based (HVAC-style)

Used when task specifies checking if demand fits within capacity at each level.

### Decision Logic
```python
def determine_days_threshold(start_past_due, demand, capacity, threshold=0.01):
    if start_past_due > threshold:
        return 6  # Still have backlog
    
    # No backlog - choose smallest days where demand fits
    if demand <= capacity[4]:
        return 4
    elif demand <= capacity[5]:
        return 5
    else:
        return 6
```

### Characteristics
- May skip 5-day entirely if demand permits 4-day when backlog clears
- First_Week_5_Days may be N/A
- More aggressive capacity optimization

### When Used
- HVAC, construction, or infrastructure tasks
- Task mentions "choose smallest schedule that can handle demand"
- Non-standard capacity constants (e.g., 35 hrs/day)

## Identifying Which Variant to Use

| Indicator | Likely Variant |
|-----------|---------------|
| "step down to 5-day, then 4-day" | State Machine (A) |
| "smallest schedule that can handle the demand" | Threshold (B) |
| Capacity constants 30/25/22/20 | Either (check wording) |
| Capacity constants 35 or other non-standard | Threshold (B) |
| HVAC, construction, infrastructure context | Threshold (B) |
| Task provides existing plan with skipped 5-day | Threshold (B) |

## First_Week_5_Days = N/A Scenarios

### Valid N/A Cases

1. **Threshold variant:** Demand low enough for 4-day when backlog clears
2. **Backlog never clears:** Always 6-day weeks
3. **Task error:** Check if First_Week_4_Days present instead

### Invalid N/A Cases

1. **State machine with cleared backlog:** Should have First_Week_5_Days
2. **Off-by-one error:** Check if logic uses `>=` vs `>`

## Verification

When task provides `existing_plan.xlsx`:
```bash
python3 scripts/extract_capacity_constants.py existing_plan.xlsx
```

This reveals:
- Which capacity constants to use
- Which variant (check if 5-day weeks exist in plan)
- Correct overtime values