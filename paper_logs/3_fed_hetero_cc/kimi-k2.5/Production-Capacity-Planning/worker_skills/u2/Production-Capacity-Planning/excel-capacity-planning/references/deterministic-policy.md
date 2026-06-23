# Deterministic Policy for Capacity Selection

Follow the policy exactly — do not add "smart" checks or conditional logic that deviates from the specified rules.

## The Policy (apply verbatim)

```
IF reported_start > threshold:
    # Catch-up mode: try 5 days first, then 6
    FOR days IN [5, 6]:
        IF calc_start + demand - capacity(days) <= 0:
            chosen_days = days; BREAK
    ELSE:
        chosen_days = 6
ELSE:
    # Normal mode: demand-based only
    IF demand <= 120: chosen_days = 4
    ELSE: chosen_days = 5
```

## Critical: Do NOT Add Smart Checks

Common mistake: adding logic like "if chosen days would create backlog, switch to catch-up mode".

**Why this is wrong**: The policy is deterministic. Mode is determined by `reported_start > threshold`, NOT by projecting what will happen after the decision. Adding these checks violates the policy and causes verifier failures.

## Examples

| Situation | Wrong (smart check) | Right (policy) |
|-----------|---------------------|----------------|
| No backlog, demand=140 | "Demand exceeds 4-day capacity, but 5 days creates backlog → use 6" | Normal mode, demand > 120 → use 5 days |
| Backlog=5, demand=100 | "6 days clears backlog → use 6" | Catch-up mode, try 5 days first: calc_start + demand - 150 = -45 ≤ 0 → use 5 |

## Key Insight

The policy separates **mode selection** (based on current state) from **capacity selection** (based on mode rules). Do not blur this boundary by projecting future outcomes to override the mode.