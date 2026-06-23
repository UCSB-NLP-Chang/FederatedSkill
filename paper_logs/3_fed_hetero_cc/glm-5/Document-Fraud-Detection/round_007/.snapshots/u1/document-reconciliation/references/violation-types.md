# Violation Types for Document/Claim Screening

Priority order: report the first matching condition.

## 1. Unknown Entity
**Trigger:** Claimant/record name cannot be matched to directory (exact, alias, or fuzzy).

**Check:** 
1. Exact match against entity names
2. Exact match against alias table (includes initial variants like "First L.")
3. Normalize name (lowercase, strip spaces), compute edit distance to all directory names. If min distance > 1: flag.

**Domain Aliases:** Unknown Provider, Unknown Vendor, Unknown Contractor, Unknown Employee, Unknown Recipient, Unknown Carrier

## 2. Account Mismatch
**Trigger:** Entity found, but `account` in record ≠ `account` in directory.

**Note:** Verify after entity match succeeds.

**Domain Aliases:** Bank Token Mismatch, Payment Account Mismatch, Remit Account Mismatch

## 3. Invalid Reference Code
**Trigger:** External reference code (e.g., SHIFT-A1) not found in crosswalk table.

**Context:** Used when records reference external codes that must be translated to internal codes via a crosswalk before validation.

## 4. Invalid Reference ID
**Trigger:** `ref_id` in record not present in authorizations/approvals database.

**Domain Aliases:** Invalid Order ID, Invalid Trip ID, Invalid Work Order, Invalid Award Ref, Invalid Shipment Ref

**Important:** This is for references that do NOT exist at all. If the reference exists but has invalid status, use "Invalid Reference Status" instead.

## 5. Invalid Reference Status
**Trigger:** Reference exists but has invalid status (e.g., draft, closed, inactive, cancelled, archived).

**Context:** Work orders, approvals, authorizations, or shipments may have status fields. Only active/valid statuses should be accepted.

**Field Variants:** `status`, `lifecycle`, `state`, `record_state`, `snapshot_state` — check for values like 'draft', 'closed', 'inactive', 'cancelled', 'archived'

**Valid Status Values:** 'active', 'approved', 'open', 'valid' (varies by domain)

**Example:** SH-7104 exists in authorizations but record_state='draft' → Invalid Reference Status

## 6. Entity-Reference Mismatch
**Trigger:** Reference exists and is valid, but `reference.assigned_entity_id` ≠ `record.entity_id` (the reference belongs to someone else).

**Critical:** This is distinct from Account Mismatch — the entity exists and their account matches, but they're claiming a reference assigned to another entity.

**Domain Aliases:** 
- Provider Mismatch (fleet maintenance: order belongs to different provider)
- Owner Mismatch (work orders: WO assigned to different owner)
- Clinician Mismatch (healthcare: shift assigned to different clinician)
- Traveler Mismatch (travel expenses: trip assigned to different employee)
- Contractor Mismatch (vendor billing: contract assigned to different contractor)
- Recipient Mismatch (stipend/award: award assigned to different recipient)
- Carrier Mismatch (logistics: shipment assigned to different carrier)

## 7. Adjusted Field Mismatch
**Trigger:** Record field value ≠ adjusted value from approved revision/amendment/snapshot.

**Context:** Adjustments may modify fields beyond amounts, such as campus codes, locations, temperature bands, or other attributes. Validate ALL adjusted fields, not just amounts.

**Common Adjusted Fields:**
- `campus_code` — campus or location assignment
- `region` — geographic region
- `department` — organizational unit
- `temperature_band` — shipping temperature requirement
- `cost_center` — billing allocation

**Example:** AWD-3004 original campus_code=CAMP-W, adjustment revision 1 changes to CAMP-C. Request shows CAMP-W → Campus Mismatch

**Check:**
1. Look up reference ID in adjustments/snapshots table
2. Filter to approved entries only
3. Skip null/empty amounts
4. Use highest revision/sequence's field values
5. Compare each adjusted field to record's corresponding field

## 8. Amount Mismatch
**Trigger:** `abs(claimed_amount - expected_amount) > 0.01`

**Note:** Use tolerance, not exact equality. Currency handling: compare as float with full precision.

**Determining Expected Amount (Multi-Source Precedence):**
1. If snapshots exist: use highest approved seq with non-null amount's expected_charge
2. If revisions/amendments exist: use highest approved revision's amount
3. If only authorizations exist: use authorization's expected_charge
4. Never use draft or unapproved values

**Example:** SH-7103 has authorization (730.0) and approved snapshot seq 1 (745.0) → use 745.0 from snapshot

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
3. Status is valid? → Invalid Reference Status if draft/closed/inactive
4. Assigned entity matches record entity? → Entity-Reference Mismatch if not

## Multi-Source Validation Pattern

When both authorizations and snapshots exist:

```
Record.ref_id (SH-7103)
       ↓
1. Check authorizations for EXISTENCE
       ↓ Not found → Invalid Reference ID
       Found → Check record_state
       ↓
2. Check authorization STATUS
       ↓ draft/closed/inactive → Invalid Reference Status
       approved/active → Continue
       ↓
3. Get EXPECTED VALUES from snapshots
       ↓ Filter: snapshot_state='approved'
       ↓ Skip: null/empty amounts
       ↓ Select: highest snapshot_seq
       ↓ Use: expected_charge, carrier_id from snapshot
       ↓
4. Validate carrier assignment
       ↓ Mismatch → Carrier Mismatch
       ↓
5. Validate amount
       ↓ Mismatch → Amount Mismatch
```

**Critical Rules:**
- Authorizations → existence check + status validation
- Snapshots → expected values (amount, carrier_id)
- DO NOT use authorization amount when snapshots exist

## Alias Matching Pattern

When entity names may vary (legal names vs. trading names, typos, abbreviations, initials):

```
Record.contractor_name ("Harbor Electric LLC")
       ↓
   Exact match in aliases table?
       ↓ Yes: Get contractor_id
   No: Check initial variants ("Amara S." → "Amara Singh")
       ↓ No match: Fuzzy match against legal names
```

Build alias lookup: `{alias_name: entity_id}` from separate sheet or file.
Include initial variants in alias table.

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

## Adjustment/Revision Multi-Field Pattern

When adjustments may modify multiple fields:

```
Original: { award_ref: AWD-3004, amount: 1600, campus_code: CAMP-W }
Adjustment: { award_ref: AWD-3004, revision: 1, amount: 1600, campus_code: CAMP-C, state: approved }
       ↓
Expected: { amount: 1600, campus_code: CAMP-C }
```

Implementation:
```python
def get_adjusted_values(ref_id, adjustments):
    """Get all adjusted field values from highest approved revision."""
    ref_adjustments = adjustments[
        (adjustments['ref_id'] == ref_id) & 
        (adjustments['state'] == 'approved')
    ]
    if len(ref_adjustments) == 0:
        return None  # No adjustments, use original
    highest = ref_adjustments.loc[ref_adjustments['revision_no'].idxmax()]
    return {
        'amount': highest['adjusted_value'],
        'campus_code': highest['campus_code'],
        # Include all adjusted fields
    }
```

## Snapshot Processing Pattern

When snapshots provide expected values:

```
Snapshots for SH-7103:
  seq 1: approved, expected_charge=745.0, carrier_id=CR903
  seq 2: approved, expected_charge=(null)
  seq 3: draft, expected_charge=760.0
       ↓
Filter: snapshot_state='approved' → seq 1, 2
Skip: null/empty amounts → seq 1 only
       ↓
Expected: { amount: 745.0, carrier_id: CR903 }
```

Implementation:
```python
def get_snapshot_values(ref_id, snapshots):
    """Get effective values from highest approved non-empty snapshot."""
    approved = snapshots[
        (snapshots['shipment_ref'] == ref_id) &
        (snapshots['snapshot_state'] == 'approved') &
        (snapshots['expected_charge'].notna()) &
        (snapshots['expected_charge'] != '')
    ]
    if len(approved) == 0:
        return None
    highest = approved.loc[approved['snapshot_seq'].idxmax()]
    return {
        'amount': float(highest['expected_charge']),
        'carrier_id': highest['carrier_id']
    }
```