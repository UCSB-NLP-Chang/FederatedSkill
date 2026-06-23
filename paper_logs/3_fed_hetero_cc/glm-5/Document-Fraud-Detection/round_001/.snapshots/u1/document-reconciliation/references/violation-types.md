# Violation Types for Document/Claim Screening

Priority order: report the first matching condition.

## 1. Unknown Entity
**Trigger:** Claimant/record name cannot be matched to directory (even fuzzily).

**Check:** Normalize name (lowercase, strip spaces), compute edit distance to all directory names. If min distance > 1: flag.

## 2. Account Mismatch
**Trigger:** Entity found, but `account` in record ≠ `account` in directory.

**Note:** Verify after entity match succeeds.

## 3. Invalid Reference ID
**Trigger:** `ref_id` in record not present in approvals/references database.

## 4. Owner Mismatch
**Trigger:** Reference exists, but `reference.owner_id` ≠ `record.entity_id` (the reference belongs to someone else).

**Critical:** This is distinct from Account Mismatch — the entity exists and their account matches, but they're claiming a reference assigned to another entity.

## 5. Amount Mismatch
**Trigger:** `abs(claimed_amount - approved_amount) > 0.01`

**Note:** Use tolerance, not exact equality. Currency handling: compare as float with full precision.

## Validation Order

Process checks in the order above. If multiple violations exist, the earlier one in this list is typically more fundamental (unknown entity supersedes account mismatch, etc.).