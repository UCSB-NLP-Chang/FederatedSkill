# Violation Types for Cross-Reference Validation

Priority order: report the first matching condition.

## Validation Order

| Priority | Violation | Trigger |
|----------|-----------|---------|
| 1 | Unknown Entity | Name not in registry or aliases (after fuzzy match) |
| 2 | Account Mismatch | Record account ≠ entity's registered account |
| 3 | Invalid Reference Code | External code not in crosswalk |
| 4 | Invalid Reference ID | Internal code not in approvals |
| 5 | Invalid Reference Status | Reference exists but status is invalid (closed, inactive) |
| 6 | Entity-Reference Mismatch | Reference's assigned entity ≠ record's entity |
| 7 | Amount Mismatch | abs(claimed - approved) > $0.01 |

---

## Expense/Claim Variants

### 1. Unknown Employee
**Trigger:** Claimant name cannot be matched to employee directory (exact, alias, or fuzzy).
**Check:** Normalize name (lowercase, strip spaces), compute edit distance ≤ 1.

### 2. Account Mismatch
**Trigger:** Employee found, but `bank_account` in claim ≠ directory.
**Note:** Verify after entity match succeeds.

### 3. Invalid Trip ID
**Trigger:** `trip_id` not in approvals database.

### 4. Traveler Mismatch
**Trigger:** Trip exists, but `trip.employee_id` ≠ matched `employee_id`.
**Critical:** Compare IDs, not names.

### 5. Amount Mismatch
**Trigger:** `abs(claimed_amount - approved_amount) > 0.01`

---

## Honorarium Variants

### 1. Unknown Speaker
**Trigger:** Speaker name cannot be matched to registry (exact, alias, or fuzzy).
**Typo tolerance:** Edit distance ≤ 1 accepted.

### 2. Account Mismatch
**Trigger:** Speaker found, but `payment_account` ≠ registry.

### 3. Invalid Approval Code
**Trigger:** `approval_code` not in session approvals.

### 4. Speaker Mismatch
**Trigger:** Approval exists, but `approval.speaker_id` ≠ matched `speaker_id`.
**Critical:** Compare IDs, not names.

### 5. Fee Mismatch
**Trigger:** `abs(requested_fee - approved_fee) > 0.01`

---

## Shift/Clinic Variants

### 1. Unknown Clinician
**Trigger:** Clinician name cannot be matched to directory (exact, alias, or fuzzy).

### 2. Payout Account Mismatch
**Trigger:** Clinician found, but `payout_account` ≠ directory.

### 3. Invalid Shift Code
**Trigger:** `shift_ref` (external code) not in crosswalk.

### 4. Invalid Internal Code
**Trigger:** External code maps but internal code not in authorizations.

### 5. Clinician Mismatch
**Trigger:** Shift authorized, but `authorization.clinician_id` ≠ matched `clinician_id`.
**Critical:** Compare IDs, not names.

### 6. Pay Amount Mismatch
**Trigger:** `abs(requested_pay - approved_pay) > 0.01`

---

## Field Service / Work Order Variants (R3)

### 1. Unknown Contractor
**Trigger:** Contractor name cannot be matched to directory or alias table (exact, alias, or fuzzy).
**Alias check:** Check alias table first before fuzzy matching primary names.

### 2. Payment Account Mismatch
**Trigger:** Contractor found, but `payment_account` ≠ registry.

### 3. Invalid Work Order
**Trigger:** `work_order_id` not in work order database.

### 4. Inactive/Closed Work Order
**Trigger:** Work order exists, but `status` ≠ "active" (closed, cancelled, pending).
**Critical:** State check, not existence check. WO exists but invalid for billing.

### 5. Contractor Mismatch
**Trigger:** Work order exists and active, but `work_order.contractor_id` ≠ matched `contractor_id`.
**Critical:** Compare IDs, not names.

### 6. Amount Mismatch
**Trigger:** `abs(billed_amount - approved_amount) > 0.01`
**Revision Handling:** Use highest approved revision amount, not original.

---

## Revision Handling

If reference has revision history with approval states:
1. Filter to `approval_state='approved'` only
2. Use highest revision number's amount as expected
3. Ignore draft/pending revisions

Example: WO-8807 has rev 1 ($6400, approved) and rev 2 ($6550, approved) → use $6550.

---

## Validation Order by Sub-Task

**Expense claims:** Unknown Employee → Account → Invalid Trip → Traveler → Amount

**Honorarium:** Unknown Speaker → Account → Invalid Approval → Speaker → Fee

**Shift claims:** Unknown Clinician → Account → Invalid Shift → Invalid Internal → Clinician → Pay

**Field service:** Unknown Contractor → Account → Invalid WO → Inactive WO → Contractor → Amount