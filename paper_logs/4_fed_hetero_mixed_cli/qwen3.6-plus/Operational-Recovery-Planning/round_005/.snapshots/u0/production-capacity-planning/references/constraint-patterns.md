# Constraint Patterns for Production Planning

Reference for common constraint patterns in capacity planning and recovery analysis tasks.

## Distribution Algorithm

### Front-Load Remainder (B2 Standard)
```python
# Calculate even distribution
units_per_day, remainder = divmod(total_units, len(working_days))

# Front-load remainder across first N days
for i, day in enumerate(working_days):
    value = units_per_day + (1 if i < remainder else 0)
    # Apply capacity caps as needed
```

**Decision Rule**: If remainder != 0, front-load remainder days (first N days get +1) rather than spreading decimals.

### Analytical Capacity Calculation (Anti-Iterative)
```python
# Do NOT iterate; calculate required capacity directly
remaining_production = total_demand - already_produced
remaining_days = total_days - days_passed
required_daily = remaining_production / remaining_days

# If exceeds capacity, identify high-cap days needed
high_cap_needed = ceil((required_daily - standard_capacity) * remaining_days / (high_cap - standard_cap))
```

---

## Scenario Patterns (Harbor DC B2)

### Scenario 1: Standard Capacity
- Capacity: 120 → 135 after Feb 5
- Categories start at different times (Web immediate, DB March 1)
- Network: distributed to meet minimum (>= 1200)
- Result: May miss PO deadlines

### Scenario 2: Front-Load Non-Critical
- Front-load Network before Feb 1 (100 units), 0 after
- Other categories start earlier than Scenario 1
- Result: Partial deadline recovery

### Scenario 3: High-Capacity Window
- 20-24 "high-cap" days allowed on/after Feb 1
- Capacity tiers: Normal 135, High-cap 170
- Trade-off: Network eliminated (= 0)
- Result: All deadlines met with extended hours

---

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

---

## Formula Patterns

### Cumulative PO Variance (Column E for Web)
- Row 4: `=D4-C4` (First day: PO due - Produced)
- Row 5+: `=E4+D5-C5` (Previous cum + today's PO - today's production)

### Total Production
- `=C4+F4+I4` (Web + DB + Network for row 4)

---

## Validation Thresholds

| Check | Requirement | Action if Failed |
|-------|-------------|------------------|
| Total Web | Exact 5520 | Redistribute remainder |
| Total DB | Exact 4035 | Adjust last working day |
| Network min | >= 0 (scenario dependent) | Verify scenario logic |
| High-cap days | 20-24 range | Adjust selection window |
| Weekend values | Exactly 0 | Force overwrite |