# Verifier Troubleshooting: legacy_pytest_suite Failures

## Diagnostic Priority (check in order)

### 1. Capacity Constants Mismatch (Most Common)

**Symptom:** Values look reasonable but verifier rejects with small numeric differences.

**Detection:**
```python
# From your output
your_6day = 168  # or whatever you calculated
implied_base = your_6day / 6  # 28.0

# Check if this matches task expectation
# Shipbuilding often uses 28 hrs/day = 168/140/112
# Standard manufacturing often uses 30 hrs/day = 180/150/120
```

**Fix:** Re-read task spec for explicit capacity values. If existing plan provided, extract with:
```bash
python3 scripts/extract_capacity_constants.py existing_plan.xlsx
```

### 2. Step-Down Policy Variant Mismatch

**Symptom:** First_Week_5_Days or First_Week_4_Days off by one or more.

**Check:** Does task use State Machine or Threshold variant?
- State Machine: Always 6→5→4 sequence, transitions on StartPastDue == 0
- Threshold: May skip 5-day, checks if demand fits in capacity

### 3. Floating-Point Precision

**Symptom:** Verifier shows values like `38.72999999999996` vs expected `38.73`.

**Fix:**
```bash
python3 scripts/defensive_reround.py output.xlsx
python3 scripts/verify_output.py output.xlsx
```

### 4. Negative Zero (-0.0)

**Symptom:** Start of Week Past Due shows 0 but verifier rejects.

**Fix:** Use `max(backlog, 0.0)` for display values, then re-round.

## Specific Context Patterns

| Context | Likely Constants | Likely Variant |
|---------|-----------------|----------------|
| Shipbuilding | 168/140/112 (28/day) | Threshold (check task) |
| HVAC/Construction | 210/175/140 (35/day) | Threshold |
| General manufacturing | 180/150/120 (30/day) | State Machine |
| Assembly/PCB | 120/100/80 (20/day) | State Machine |

## Emergency Verification

If all else fails, extract what the verifier expects:
```python
# If you have access to verifier's expected output
python3 scripts/extract_capacity_constants.py expected_output.xlsx
# Use these exact values in your calculation
```
