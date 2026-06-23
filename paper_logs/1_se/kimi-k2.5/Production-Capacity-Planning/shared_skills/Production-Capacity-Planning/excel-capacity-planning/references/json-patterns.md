# JSON Input Patterns for Capacity Planning

## Chemical/Reactor Style Format

```json
[
  {
    "week": 10,
    "data": {
      "demand_per_week": 253.06
    },
    "priority": "HIGH"
  },
  {
    "week": 15,
    "data": {
      "demand_per_week": 260.92
    },
    "priority": "HIGH"
  },
  {
    "week": 15,
    "data": {
      "demand_per_week": 310.0
    },
    "priority": "LOW"
  },
  {
    "week": 20,
    "data": {
      "demand_per_week": 170.17
    },
    "priority": "MED"
  },
  {
    "week": 20,
    "data": {
      "demand_per_week": null
    },
    "priority": "NORMAL"
  }
]
```

## Key Processing Rules

### 1. Duplicate Handling by Priority

When multiple entries exist for the same week, select by priority:

| Priority | Rank | Use When |
|----------|------|----------|
| HIGH | 0 | Default for production demand |
| MED/MEDIUM | 1 | Secondary demand |
| NORMAL | 2 | Fallback |
| LOW | 3 | Lowest priority, often ignored |

**Rule:** Keep the entry with the lowest numeric rank. If ranks equal, keep first encountered.

### 2. Null Demand Filtering

Entries with `demand_per_week: null` or missing `data.demand_per_week` must be excluded entirely.

```python
if demand is None:
    continue  # Skip this entry
```

### 3. Week Sorting

Always process weeks in ascending numeric order, regardless of input order.

```python
sorted_entries = sorted(entries, key=lambda x: x['week'])
```

## Initial Condition Patterns

### Pattern: Explicit Sum
```
Start of Phase Past Due + Scheduled Demand = 1453.06
```

Extraction:
```python
initial_backlog = 1453.06 - first_week_demand
```

### Pattern: Explicit Starting Value
```
Starting backlog: 1200 hours
```

Use directly as `initial_backlog`.

## Common Variants

### Phase-Based (vs Week-Based)
Some tasks use "Phase" instead of "Week". The logic remains identical—just treat phase numbers as the time index.

### Embedded Capacity Constants
Rarely, JSON may include capacity metadata:
```json
{
  "metadata": {
    "capacity_6_day": 240,
    "capacity_5_day": 200,
    "capacity_4_day": 160
  },
  "demand": [...]
}
```

Always check for this structure before assuming standard constants.
