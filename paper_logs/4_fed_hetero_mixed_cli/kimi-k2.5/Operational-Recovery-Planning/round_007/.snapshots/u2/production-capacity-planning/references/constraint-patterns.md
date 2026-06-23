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

### Date-Cutoff Distribution (Two-Pass)
For constraints like ">= X before date Y, 0 after":

```python
# Pass 1: Identify eligible working days before cutoff
eligible_indices = [
    i for i, d in enumerate(dates)
    if d < cutoff_date and not is_non_working(d)
]

# Pass 2: Distribute target evenly across eligible days
target = 100  # example
per_day = target // len(eligible_indices)
remainder = target % len(eligible_indices)

for idx, i in enumerate(eligible_indices):
    bulk[i] = per_day + (1 if idx < remainder else 0)

# Pass 3: Zero out all days on/after cutoff
for i, d in enumerate(dates):
    if d >= cutoff_date:
        bulk[i] = 0

# Verify
assert sum(bulk[i] for i in eligible_indices) >= target
assert all(bulk[i] == 0 for i, d in enumerate(dates) if d >= cutoff_date)
```

**Critical**: Exclude holidays from `eligible_indices`. Including them in the count causes under-allocation since holidays get 0 production.

---

## Shift-Day Selection Algorithm

When a scenario allows 20-24 "high-capacity" or "shift" days at elevated capacity (e.g., 160-170 units):

```python
def select_shift_days(dates, threshold_date, category_start_dates, min_days=20, max_days=24, capacity=170):
    """Select shift days on/after threshold AND all category start dates."""
    # CRITICAL: Use the LATEST date among threshold and all category starts
    effective_start = max(threshold_date, *category_start_dates)
    
    eligible = [
        d for d in dates
        if d >= effective_start and not is_non_working(d)
    ]
    
    # Select first N eligible days (or distribute as needed)
    shift_days = eligible[:max_days]
    
    # Validate count
    assert min_days <= len(shift_days) <= max_days
    
    return set(shift_days)

# Example usage:
# threshold_date = Feb 1 (scenario allows shift days from Feb 1)
# category_start_dates = [Feb 20]  # Canola doesn't start until Feb 20
# effective_start = Feb 20 (shift days must respect Canola's start)
shift_days = select_shift_days(
    dates, 
    threshold_date=datetime.date(2018, 2, 1),
    category_start_dates=[datetime.date(2018, 2, 20)]
)

# Apply in production loop
for d in dates:
    if is_non_working(d):
        production = 0
    elif d in shift_days:
        production = 170  # elevated capacity
    else:
        production = standard_capacity(d)
```

**Validation Rules**:
- Shift days must be working days (weekday < 5, not holiday)
- Shift days must be on/after threshold date
- **Shift days must be on/after ALL category start dates** (use `max(threshold, *category_starts)`)
- Shift day count must be within [min_days, max_days] range
- Production on shift days must not exceed elevated cap (e.g., 170)
- Production on non-shift days must respect standard caps (e.g., 120/135)

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
| Shift day count | 20-24, on/after threshold AND all category starts | Re-select eligible days |
| Pre-cutoff sum | >= target | Increase per-day allocation |
| Post-cutoff sum | == 0 | Zero out all post-cutoff days |

---

## Verification Anti-Patterns

### Constraint Verification ≠ Outcome Verification

A common failure mode is verifying that constraints are satisfied (caps, dates, formulas) without verifying the final business outcomes:

```python
# WRONG: Only verify constraints
assert all(production <= capacity for day in days)
assert all(weekend_production == 0 for day in weekends)
# Tests still fail because totals are wrong!

# RIGHT: Verify business outcomes
assert total_wheat_produced == 5520  # exact requirement
assert final_cumulative_open_po <= 0  # on-time delivery
assert on_time_status == "Yes"  # matches expected outcome
```

### Self-Verification Divergence

When your verification code reads from the same data structures you wrote, errors in your logic affect both equally. Always:

1. **Read the actual output file** (not in-memory data)
2. **Compare against expected values** (from spec or test file)
3. **Verify at the business level** (totals, on-time status), not just constraints

```python
# WRONG: Verify from in-memory data
assert my_calculations['total'] == expected_total

# RIGHT: Read actual file and verify
wb = load_workbook('output.xlsx')
# Discover bounds dynamically, don't hardcode row ranges
max_row = ws.max_row
actual_total = sum(ws.cell(row=r, column=3).value for r in range(4, max_row + 1) if ws.cell(row=r, column=3).value is not None)
assert actual_total == expected_total, f"Got {actual_total}, expected {expected_total}"
```

### Hardcoded Row Range Anti-Pattern

Never assume fixed row ranges in verification code. The data may span different ranges depending on the scenario:

```python
# WRONG: Hardcoded range
for row in range(4, 104):  # Assumes exactly 100 data rows
    ...

# RIGHT: Discover bounds dynamically
max_row = ws.max_row
for row in range(4, max_row + 1):
    cell_val = ws.cell(row=row, column=col).value
    if cell_val is None:
        break  # Stop at first empty cell
    ...
```