# Violation Types for Cross-Reference Validation

Priority order: report the first matching condition.

## Generic Pattern

| Priority | Violation | Trigger | Applies To |
|----------|-----------|---------|------------|
| 1 | Unknown Entity | Name not in registry | Employees, speakers, customers |
| 2 | Account Mismatch | payment_account ≠ registry | Bank accounts, payment codes |
| 3 | Invalid Reference | ID/code not in approvals | Trip IDs, approval codes |
| 4 | Ownership Mismatch | approval's owner ≠ requester | Traveler/speaker mismatch |
| 5 | Amount Mismatch | |fee difference| > tolerance | Any monetary validation |

---

## Expense/Claim Variants

### 1. Unknown Employee
**Trigger:** Claimant name cannot be matched to employee directory (even fuzzily).

**Check:** Normalize name (lowercase, strip spaces), compute edit distance to all directory names. If min distance > 1: flag.

### 2. Account Mismatch
**Trigger:** Employee found, but `bank_account` in claim ≠ `bank_account` in directory.

**Note:** Verify after employee match succeeds.

### 3. Invalid Trip ID
**Trigger:** `trip_id` in claim not present in approvals/trips database.

### 4. Traveler Mismatch
**Trigger:** Trip exists, but `trip.employee_id` ≠ `claim.employee_id` (the trip belongs to someone else).

**Critical:** This is distinct from Account Mismatch — the employee exists and their account matches, but they're claiming a trip assigned to another employee.

### 5. Amount Mismatch
**Trigger:** `abs(claimed_amount - approved_amount) > 0.01`

---

## Honorarium Variants

### 1. Unknown Speaker
**Trigger:** Speaker name cannot be matched to speaker registry (even fuzzily).

**Example:** "Marisa Cole" not found → flag as Unknown Speaker

**Typo tolerance:** "Dr Evelyn Hart" matches "Dr. Evelyn Hart" with edit distance 1

### 2. Account Mismatch
**Trigger:** Speaker found, but `payment_account` in request ≠ `payment_account` in registry.

**Example:** Request shows "BAD-22" but registry shows "PAY-22" → flag

### 3. Invalid Approval Code
**Trigger:** `approval_code` in request not present in session approvals database.

**Example:** "AP-7999" when only AP-7001 through AP-7006 exist → flag

### 4. Speaker Mismatch
**Trigger:** Approval code exists, but `approval.speaker_id` ≠ `request.speaker_id` (the code belongs to another speaker).

**Example:** Helena Zhou (SPK-25) requests AP-7002, but AP-7002 belongs to Omar Li (SPK-22) → flag

**Critical:** Check `speaker_id` from matched name against `speaker_id` in approval record, not just name string comparison.

### 5. Fee Mismatch
**Trigger:** `abs(requested_fee - approved_fee) > 0.01`

**Example:** Requested $1,700.50 vs approved $1,750.50 → $50 difference exceeds tolerance → flag

---

## Validation Order

Process checks in priority order. If multiple violations exist, the earlier one in this list is typically more fundamental (unknown entity supersedes account mismatch, etc.).

This ordering ensures you don't report "Speaker Mismatch" when the real issue is "Unknown Speaker" due to a typo in the name field.