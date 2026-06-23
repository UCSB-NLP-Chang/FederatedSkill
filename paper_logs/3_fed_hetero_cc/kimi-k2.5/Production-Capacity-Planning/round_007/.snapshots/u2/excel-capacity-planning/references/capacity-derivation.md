# Extracting Capacity Rules from Task Prompts

The most common source of verifier failures is incorrect capacity values. This guide shows how to extract the correct values from any task prompt.

## Step 1: Find the Capacity Table

Look for tables or lists with these keywords:
- "capacity"
- "hours per week"
- "production rate"
- "days worked"
- "standard hours"
- "overtime"

## Step 2: Identify the Pattern

### Pattern A: Direct Totals (Most Reliable)

The task gives total capacity directly:

```
| Days Worked | Weekly Capacity (Std Hrs) | Overtime Hours |
|-------------|---------------------------|----------------|
| 6           | 152                       | 20             |
| 5           | 120                       | 10             |
| 4           | 88                        | 0              |
```

**Use these exact values.** Do not recalculate.

### Pattern B: Rate-Based with OT Formula

The task gives hourly rate and OT formula:

```
The production rate is 22 hours per day. Overtime is 10 hours for each day beyond 4.
```

Calculate:
```python
rate = 22  # From task
ot_per_extra_day = 10  # From task

CAPACITY_RULES = {
    6: {"std": 6 * rate, "ot": 2 * ot_per_extra_day, "total": 6 * rate + 2 * ot_per_extra_day},
    5: {"std": 5 * rate, "ot": 1 * ot_per_extra_day, "total": 5 * rate + 1 * ot_per_extra_day},
    4: {"std": 4 * rate, "ot": 0, "total": 4 * rate}
}
```

### Pattern C: Mixed (Most Dangerous)

The task gives some totals and some rates. **Always prefer explicit totals over calculated values.**

Example:
```
Standard capacity is 25 hours per day. With 6 days, overtime adds 20 hours.
```

Here the 6-day total might be explicitly 170 (150+20) or calculated as 170. Use 170.

## Step 3: Verify Your Extraction

Before running the planner, print and verify:

```python
print("Extracted capacity rules:")
for days, rule in CAPACITY_RULES.items():
    print(f"  {days} days: std={rule['std']}, ot={rule['ot']}, total={rule['total']}")

# Verify against task prompt
expected_6_day = 152  # From your task
if CAPACITY_RULES[6]['total'] != expected_6_day:
    print(f"WARNING: 6-day capacity {CAPACITY_RULES[6]['total']} != expected {expected_6_day}")
```

## Step 4: Find the Threshold for 4-Day Selection

In normal mode (no backlog), the policy chooses 4 vs 5 days based on demand.

Look for:
- "if demand is less than or equal to X, work 4 days"
- "4-day capacity is sufficient for demands up to X"
- Implicit in the 4-day total capacity value

Common values: 72, 80, 88, 100, 110, 120

## Common Mistakes

| Mistake | Example | Why Wrong |
|---------|---------|-----------|
| Using wrong rate | Using 25 when task says 22 | Capacity totals will be wrong |
| Ignoring explicit totals | Calculating 6*22=132 when task says 152 | Task may include OT differently |
| Wrong OT formula | Using 10*(days-4) when task specifies fixed values | OT may not be linear |
| Assuming 4-day threshold | Using 88 when task implies 100 | Demand comparison will be wrong |

## Fallback: When Values Are Ambiguous

If the task prompt is unclear:

1. Look for example calculations in the prompt
2. Check if totals sum cleanly (e.g., 152 = 132 + 20 suggests rate=22, ot=20)
3. Use the most conservative interpretation that matches any examples given
4. Document your assumption in code comments