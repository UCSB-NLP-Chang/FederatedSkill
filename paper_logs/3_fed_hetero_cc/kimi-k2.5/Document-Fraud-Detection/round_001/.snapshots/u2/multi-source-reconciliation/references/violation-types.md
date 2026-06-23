# Violation Types for Expense/Claim Screening

Priority order: report the first matching condition.

## 1. Unknown Employee
**Trigger:** Claimant name cannot be matched to employee directory (even fuzzily).

**Check:** Normalize name (lowercase, strip spaces), compute edit distance to all directory names. If min distance > 1: flag.

## 2. Account Mismatch
**Trigger:** Employee found, but `bank_account` in claim ≠ `bank_account` in directory.

**Note:** Verify after employee match succeeds.

## 3. Invalid Trip ID
**Trigger:** `trip_id` in claim not present in approvals/trips database.

## 4. Traveler Mismatch
**Trigger:** Trip exists, but `trip.employee_id` ≠ `claim.employee_id` (the trip belongs to someone else).

**Critical:** This is distinct from Account Mismatch — the employee exists and their account matches, but they're claiming a trip assigned to another employee.

## 5. Amount Mismatch
**Trigger:** `abs(claimed_amount - approved_amount) > 0.01`

**Note:** Use tolerance, not exact equality. Currency handling: compare as float with 2-decimal precision.

## Validation Order

Process checks in the order above. If multiple violations exist, the earlier one in this list is typically more fundamental (unknown employee supersedes account mismatch, etc.).