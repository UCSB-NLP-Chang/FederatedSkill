# Amendment, Revision, and Snapshot Processing

## Overview

Reference data often changes over time. Three common patterns for tracking changes:

- **Amendments**: Separate table of modifications to base records (common in maintenance orders)
- **Revisions**: Versioned records with revision numbers (common in awards/stipends)
- **Snapshots**: Changelog/audit tables with sequence numbers (common in shipment tracking)

## Core Rule

**Always use the highest approved revision/amendment/snapshot.**

Unapproved states (`draft`, `pending`, `cancelled`) are never valid for validation.

## Amendment Pattern (Maintenance Orders)

```
order_id | amendment_no | decision  | amended_charge
MO-9003  | 1            | approved  | 1175.00
MO-9003  | 2            | pending   | 1200.00
```

Processing:
- Filter to `decision='approved'` only
- Select highest `amendment_no` (1 in this case, not 2)
- Use `amended_charge` from that row

## Revision Pattern (Research Awards)

```
award_ref | revision_no | state    | adjusted_value | campus_code
AWD-3004  | 0           | approved | 1600.00        | CAMP-W
AWD-3004  | 1           | approved | 1600.00        | CAMP-C
```

Processing:
- Filter to `state='approved'` only
- Select highest `revision_no`
- Use ALL fields from that revision (amount, campus, etc.)

## Snapshot Pattern (Cold-Chain Shipments)

```
shipment_ref | snapshot_seq | snapshot_state | expected_charge | carrier_id
SH-7103      | 1            | approved       | 745.0           | CR903
SH-7103      | 2            | approved       | (null/empty)    | CR903
SH-7103      | 3            | draft          | 760.0           | CR903
```

Processing:
- Filter to `snapshot_state='approved'` only (excludes seq 3)
- Skip entries with null/empty amounts (excludes seq 2)
- Select highest remaining `snapshot_seq` (1 in this case)
- Use `expected_charge` from that row

**Key difference**: Snapshots may have empty amounts. Always check for null/empty and skip.

## Version Pattern (Clinical Trial Releases)

```
award_ref | version_no | approval_state | version_amount | participant_code
AR-5002   | 1          | approved       | 1450.0          | PC1002
AR-5002   | 2          | approved       | (null/empty)    | PC1002
AR-5005   | 1          | rejected       | 900.0           | PC1005
```

Processing:
- Filter to `approval_state='approved'` only (excludes AR-5005)
- Skip entries with null/empty amounts (excludes version 2)
- Select highest remaining `version_no`
- Use `version_amount` and `participant_code` from that row

## Input Record Deduplication Pattern

When input records (PDF pages, form submissions) have their own revision system:

```
Page 2: packet_id=PKT-01, revision=1, participant=Aiden Moore
Page 3: packet_id=PKT-01, revision=2, participant=Aiden Moore
Page 10: packet_id=PKT-07, revision=1, participant=Eli Grant
Page 11: packet_id=PKT-07, revision=1, participant=Eli Grant
```

Processing:
- Group records by `packet_id`
- Within each group, keep only the highest `revision`
- If same revision appears multiple times, keep the last occurrence (later page supersedes)
- Validate only retained records

Result: Pages 3 and 11 retained; Pages 2 and 10 discarded as superseded.

## Multi-Source Precedence Rule

When BOTH authorizations AND snapshots exist for the same reference:

1. **Authorization**: Use for EXISTENCE check and STATUS validation only
2. **Snapshot**: Use for EXPECTED VALUES (amount, carrier_id, etc.)

```
Authorization for SH-7103:
  - record_state: 'approved'  ← CHECK THIS for validity
  - expected_charge: 730.0    ← DO NOT USE for amount validation

Snapshot for SH-7103:
  - snapshot_state: 'approved', seq 1: expected_charge 745.0  ← USE THIS
```

If only one source exists, use it for both existence and values.

## Implementation Pattern

```python
def get_snapshot_values(shipment_ref, snapshots_df):
    """Get effective values from highest approved non-empty snapshot."""
    approved = snapshots_df[
        (snapshots_df['shipment_ref'] == shipment_ref) &
        (snapshots_df['snapshot_state'] == 'approved') &
        (snapshots_df['expected_charge'].notna()) &
        (snapshots_df['expected_charge'] != '')
    ]
    if len(approved) == 0:
        return None
    highest = approved.loc[approved['snapshot_seq'].idxmax()]
    return {
        'amount': float(highest['expected_charge']),
        'carrier_id': highest['carrier_id']
    }

def get_version_values(award_ref, versions_df):
    """Get effective values from highest approved non-empty version."""
    approved = versions_df[
        (versions_df['award_ref'] == award_ref) &
        (versions_df['approval_state'] == 'approved') &
        (versions_df['version_amount'].notna()) &
        (versions_df['version_amount'] != '')
    ]
    if len(approved) == 0:
        return None
    highest = approved.loc[approved['version_no'].idxmax()]
    return {
        'amount': float(highest['version_amount']),
        'participant_code': highest['participant_code']
    }

def deduplicate_input_records(records):
    """Keep only highest revision per packet_id."""
    packets = {}
    for record in records:
        packet_id = record.get('packet_id')
        revision = record.get('revision', 0)
        if packet_id not in packets:
            packets[packet_id] = record
        else:
            existing_rev = packets[packet_id].get('revision', 0)
            if revision > existing_rev:
                packets[packet_id] = record  # Higher revision replaces
            elif revision == existing_rev:
                packets[packet_id] = record  # Same revision, later record wins
    return list(packets.values())

def check_authorization_status(ref_id, authorizations_df):
    """Check if reference exists and has valid status."""
    auth = authorizations_df[authorizations_df['shipment_ref'] == ref_id]
    if len(auth) == 0:
        return 'not_found'
    state = auth.iloc[0]['record_state']
    if state in ['draft', 'closed', 'inactive', 'archived']:
        return 'invalid_status'
    return 'valid'
```

## State Field Variants

Different domains use different state field names:

| Domain | State Field | Valid Values | Invalid Values |
|--------|-------------|--------------|----------------|
| Maintenance | `lifecycle` | `active`, `approved` | `closed`, `cancelled` |
| Awards | `state` | `approved` | `archived`, `draft`, `pending` |
| Shipments | `snapshot_state` | `approved` | `draft`, `pending` |
| Authorizations | `record_state` | `approved` | `draft`, `closed` |
| Clinical Trials | `status` | `active` | `archived`, `closed` |
| Versions | `approval_state` | `approved` | `rejected`, `pending`, `draft` |

Always check the actual field name in your data source.