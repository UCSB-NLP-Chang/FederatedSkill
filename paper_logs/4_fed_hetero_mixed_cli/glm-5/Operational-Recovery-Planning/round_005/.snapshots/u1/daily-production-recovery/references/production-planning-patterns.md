# Production Planning Constraint Patterns

Reference for common constraint patterns seen in capacity planning and recovery analysis tasks.

## Scenario Patterns

### Scenario 1: Standard Capacity
- **Constraint**: Standard daily capacity (e.g., 120 before date X, 135 after)
- **Start dates**: Categories start at different times (e.g., Web immediately, DB March 1)
- **Network**: Distributed across all days to meet minimum (e.g., ≥1200)
- **Result**: May miss PO deadlines

### Scenario 2: Front-Load Non-Critical
- **Constraint**: Front-load one category (Network) before critical date (Feb 1)
- **Mechanism**: 100 units before Feb 1, 0 after
- **Other categories**: Start earlier than Scenario 1 (e.g., DB starts Feb 20)
- **Result**: Partial deadline recovery

### Scenario 3: High-Capacity Window
- **Constraint**: 20-24 "high-capacity" days allowed on/after Feb 1
- **Capacity tiers**: 
  - Normal: 135 units/day
  - High-cap: up to 170 units/day
- **Trade-off**: One category eliminated (Network = 0)
- **Result**: All deadlines met with extended hours

## Date Logic

### Manitoba Holidays 2018
- February 19 (Louis Riel Day)
- March 30 (Good Friday)

### Capacity Transition
```python
def get_capacity(date, is_high_cap_day=False):
    if is_high_cap_day:
        return 170
    elif date >= datetime(2018, 2, 5):
        return 135
    else:
        return 120
```

## Formula Patterns

### Cumulative PO Variance (Column E for Web)
- Row 4: `=D4-C4` (First day: PO due - Produced)
- Row 5+: `=E4+D5-C5` (Previous cum + today's PO - today's production)

### Total Production (Column J)
- `=C4+F4+I4` (Web + DB + Network for row 4)

## Validation Thresholds

| Check | Tolerance | Action if Failed |
|-------|-----------|------------------|
| Total Web | Exact 5520 | Redistribute remainder |
| Total DB | Exact 4035 | Adjust last working day |
| Network min | ≥ 0 (scenario dependent) | Verify scenario logic |
| High-cap days | 20-24 range | Adjust selection window |
| Weekend values | Exactly 0 | Force overwrite |