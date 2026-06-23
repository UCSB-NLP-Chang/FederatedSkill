# Violation Types for Document/Claim Screening

Priority order: report the first matching condition.

## 1. Unknown Entity
**Trigger:** Claimant/record name cannot be matched to directory (exact, alias, or fuzzy).

**Check:** 
1. Exact match against entity names
2. Exact match against alias table
3. Normalize name (lowercase, strip spaces), compute edit distance to all directory names. If min distance > 1: flag.

**Domain Aliases:** Unknown Provider, Unknown Vendor, Unknown Contractor, Unknown Employee

## 2. Account Mismatch
**Trigger:** Entity found, but `account` in record ≠ `account` in directory.

**Note:** Verify after entity match succeeds.

## 3. Invalid Reference Code
**Trigger:** External reference code (e.g., SHIFT-A1) not found in crosswalk table.

**Context:** Used when records reference external codes that must be translated to internal codes via a crosswalk before validation.

## 4. Invalid Reference ID
**Trigger:** `ref_id` in record not present in approvals/references database.

**Domain Aliases:** Invalid Order ID, Invalid Trip ID, Invalid Work Order

**Note:** If using a crosswalk, this check applies to the internal code after crosswalk lookup.

## 5. Invalid Reference Status
**Trigger:** Reference exists but has invalid status (e.g., closed, inactive, cancelled).

**Context:** Work orders, approvals, or authorizations may have status fields. Only active/valid statuses should be accepted.

**Field Variants:** `status`, `lifecycle`, `state` — check for values like 'closed', 'inactive', 'cancelled'

**Example:** MO-9006 exists but lifecycle='closed' → Invalid Order

## 6. Entity-Reference Mismatch
**Trigger:** Reference exists, but `reference.assigned_entity_id` ≠ `record.entity_id` (the reference belongs to someone else).

**Critical:** This is distinct from Account Mismatch — the entity exists and their account matches, but they're claiming a reference assigned to another entity.

**Domain Aliases:** 
- Provider Mismatch (fleet maintenance: order belongs to different provider)
- Owner Mismatch (work orders: WO assigned to different owner)
- Clinician Mismatch (healthcare: shift assigned to different clinician)
- Traveler Mismatch (travel expenses: trip assigned to different employee)
- Contractor Mismatch (vendor billing: contract assigned to different contractor)

## 7. Amount Mismatch
**Trigger:** `abs(claimed_amount - approved_amount) > 0.01`

**Note:** Use tolerance, not exact equality. Currency handling: compare as float with full precision.

**Revision/Amendment Handling:** If reference has revision history or amendments with approval states:
1. Filter to revisions with `approval_state='approved'` OR amendments with `decision='approved'`
2. Use the highest revision/amendment number's amount as approved_amount
3. If no approved revisions/amendments, use original amount

**Example:** MO-9003 original $1150, amendment 1 for $1175 approved → use $1175

## Validation Order

Process checks in the order above. If multiple violations exist, the earlier one in this list is typically more fundamental (unknown entity supersedes account mismatch, etc.).

## Multi-Hop Reference Pattern

When records use external codes that require translation:

```
Record.shift_ref (SHIFT-A1)
       ↓
   Crosswalk lookup
       ↓
Internal code (INT-5101)
       ↓
   Authorization lookup
       ↓
Approved amount + assigned entity
```

Validation checks at each hop:
1. External code in crosswalk? → Invalid Reference Code if not found
2. Internal code in authorizations? → Invalid Reference ID if not found
3. Assigned entity matches record entity? → Entity-Reference Mismatch if not

## Alias Matching Pattern

When entity names may vary (legal names vs. trading names, typos, abbreviations):

```
Record.contractor_name ("Harbor Electric LLC")
       ↓
   Exact match in aliases table?
       ↓ Yes: Get contractor_id
   No: Fuzzy match against legal names
```

Build alias lookup: `{alias_name: entity_id}` from separate sheet or file.

## Nested JSON Flattening Pattern

When reference data has nested structure:

```
JSON: { depots: [ { orders: [...] }, { orders: [...] } ] }
       ↓
Flatten: { order_id: { ...order, depot_code } }
```

Implementation:
```python
orders = {}
for depot in data['depots']:
    for order in depot['orders']:
        orders[order['order_id']] = {**order, 'depot_code': depot['depot_code']}
```
