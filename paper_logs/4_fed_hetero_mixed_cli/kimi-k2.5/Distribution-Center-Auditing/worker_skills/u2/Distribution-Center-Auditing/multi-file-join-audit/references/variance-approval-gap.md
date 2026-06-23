# Variance-Based Approval Gap Pattern

## Overview
When auditing planned quantities against actual counts with an allowed variance threshold, and approval is required for out-of-tolerance variances, use this pattern to compute the Approval Gap flag.

## Business Rule

**Approval Gap** = `1` if ALL of the following are true:
1. `Approval Needed` column equals `'YES'` (case-insensitive)
2. A qualifying final event exists for the key
3. `abs(Expected Qty - Count Qty) > Allowed Variance`

Otherwise, Approval Gap = `0`.

**Important**: The comparison is strictly greater than (`>`), not greater than or equal (`>=`). If the absolute difference equals the allowed variance, it is NOT an approval gap.

## Implementation

```python
def compute_approval_gap(approval_needed, expected_qty, count_qty, allowed_variance):
    """
    Returns 1 if approval was needed but variance exceeded threshold, else 0.
    """
    if approval_needed is None:
        return 0
    if str(approval_needed).strip().upper() != 'YES':
        return 0
    if count_qty is None:
        return 0  # No valid count to compare
    return 1 if abs(expected_qty - count_qty) > allowed_variance else 0
```

## Common Pitfalls

1. **Using `>=` instead of `>`**: The rule is strictly greater than. If `abs(diff) == allowed_variance`, it is within tolerance and NOT an approval gap.
2. **Not checking for None Count Qty**: If the final event has a blank/None count quantity, there is no valid count to compare against. This should result in Missing Final Count = 1, not Approval Gap.
3. **Case sensitivity**: Approval Needed values may be 'YES', 'Yes', 'yes'. Always normalize with `.strip().upper()`.
4. **Integer vs float comparison**: Allowed Variance and quantities may be integers or floats. Use `abs()` for comparison to avoid sign issues.

## Example

| Expected Qty | Count Qty | Allowed Variance | Approval Needed | Approval Gap |
|---|---|---|---|---|
| 30 | 27 | 1 | YES | 1 (|30-27|=3 > 1) |
| 25 | 23 | 0 | YES | 1 (|25-23|=2 > 0) |
| 30 | 31 | 1 | YES | 0 (|30-31|=1 is NOT > 1) |
| 50 | 48 | 2 | NO | 0 (Approval not needed) |
| 60 | None | 4 | NO | 0 (No valid count; Missing Final Count = 1 instead) |
