# Step-Down Transition Examples

## Example 1: Backlog Clears Exactly at Step-Down

**Scenario:** Phase 15 ends with backlog = 24.56. Phase 16 demand = 50.78. Capacity: 120/6-day, 100/5-day.

**Decision for Phase 16:**
- StartPastDue = 24.56 (positive)
- Try 5-day: 24.56 + 50.78 - 100 = -24.66 ≤ 0 ✓ clears backlog
- But policy says: IF StartPastDue > 0 → 6-day week
- Result: **6-day week**, EndBacklog = 24.56 + 50.78 - 120 = -44.66

Wait—this contradicts. Let me recalculate correctly:

Actually, the policy checks `StartPastDue` to determine days, not whether capacity clears.

| Phase | StartPastDue | Days | Calculation | EndBacklog |
|-------|--------------|------|-------------|------------|
| 15 | 71.77 | 6 | 71.77 + 72.79 - 120 | 24.56 |
| 16 | 24.56 | **6** | 24.56 + 50.78 - 120 | -44.66 |
| 17 | 0 | **5** | 0 + 64.86 - 100 | -35.14 |

**Result:** First 5-day week is 17, not 16, because Phase 16 still had positive StartPastDue.

## Example 2: 5-Day Week Clears Backlog

**Scenario:** Phase 15 ends with backlog = 24.56. Phase 16 demand = 50.78.

**Alternative interpretation (if task spec differs):**
Some task specs use: "first week where backlog would clear with normal capacity"

In that case:
- Try 5-day first: 24.56 + 50.78 - 100 = -24.66 ≤ 0 ✓
- Result: **5-day week**, First_5_Days = 16

**Always verify from task specification which interpretation to use.**

## Example 3: Immediate Step-Down

**Scenario:** Initial backlog = 0, Week 1 demand = 60. Capacity: 120/6-day, 100/5-day, 80/4-day.

| Week | StartPastDue | Days | Reason |
|------|--------------|------|--------|
| 1 | 0 | 5 | No backlog, first_5 is None |
| 2 | 0 | 4 | No backlog, first_5 set, first_4 is None |
| 3+ | 0 | 4 | Maintain 4-day |

**Result:** First_5_Days = 1, First_4_Days = 2

## Example 4: Never Steps Down

**Scenario:** Demand always exceeds 4-day capacity, so backlog never fully clears.

| Week | StartPastDue | Days | Reason |
|------|--------------|------|--------|
| All | >0 | 6 | Always backlog |

**Result:** First_5_Days = N/A, First_4_Days = N/A

## Decision Rule Summary

```python
def determine_days(start_past_due, first_5, first_4):
    if start_past_due > 0:
        return 6  # Must clear backlog first
    elif first_5 is None:
        return 5  # First week with no starting backlog
    elif first_4 is None:
        return 4  # Week after first 5-day
    else:
        return 4  # Maintain
```

**Critical:** `start_past_due` for week N is `max(end_backlog of week N-1, 0)`, not the raw `end_backlog`.
