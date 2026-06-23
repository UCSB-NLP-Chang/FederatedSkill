# Snapshot and Revision Systems with Null Handling

## Overview

Some approval systems use snapshot-based revisions where each snapshot_seq represents a state change. Unlike simple amendments that always provide values, snapshots may contain null/empty values that intentionally override previous values.

## Key Pattern: Null Value Override

In snapshot systems, a later approved snapshot with a null/empty expected_charge effectively removes the charge requirement, even if earlier snapshots had values.

### Example Data

```csv
shipment_ref,snapshot_seq,snapshot_state,expected_charge,carrier_id
SH-7103,1,approved,745.0,CR903
SH-7103,2,approved,,CR903
SH-7103,3,draft,760.0,CR903
```

### Processing Logic

```python
def get_effective_snapshot(snapshots_df, shipment_ref):
    """
    Get effective approved values from snapshot history.
    Later approved snapshots override earlier ones, including null values.
    """
    # Filter to this shipment and approved state
    shipment_snaps = snapshots_df[
        (snapshots_df['shipment_ref'] == shipment_ref) &
        (snapshots_df['snapshot_state'] == 'approved')
    ]
    
    if len(shipment_snaps) == 0:
        return None
    
    # Get maximum snapshot sequence
    latest = shipment_snaps.loc[shipment_snaps['snapshot_seq'].idxmax()]
    
    # Return dict - note that expected_charge may be null/NaN
    return {
        'expected_charge': latest['expected_charge'],  # May be NaN/null
        'carrier_id': latest['carrier_id'],
        'snapshot_seq': latest['snapshot_seq']
    }


def validate_charge_amount(requested_charge, effective_snapshot):
    """
    Validate requested charge against effective snapshot.
    Returns (is_valid, reason)
    """
    expected = effective_snapshot.get('expected_charge')
    
    # Check if expected_charge is null/NaN/empty
    if pd.isna(expected) or expected == '' or expected is None:
        # No approved charge amount exists at latest snapshot
        return False, "Amount Mismatch: no approved charge in latest snapshot"
    
    expected_float = float(expected)
    if abs(requested_charge - expected_float) > 0.01:
        return False, f"Amount Mismatch: requested ${requested_charge}, expected ${expected_float}"
    
    return True, None
```

## Comparison: Amendments vs Snapshots

| Aspect | Amendment System | Snapshot System |
|--------|-----------------|-----------------|
| Null handling | Amendments usually provide values | Snapshots may have null values that override |
| Revision tracking | amendment_no | snapshot_seq |
| State field | decision (approved/rejected) | snapshot_state (approved/draft/pending) |
| Partial updates | Usually complete record | May be sparse (only changed fields) |

## Decision Rules

1. **Check for null in latest approved** — A null expected_charge in the latest approved snapshot means no valid charge exists, regardless of earlier values
2. **Ignore draft snapshots** — Only consider `snapshot_state == 'approved'`
3. **Max sequence wins** — Higher snapshot_seq supersedes lower, even with nulls
4. **Don't backfill from earlier snapshots** — Each snapshot is a complete state replacement

## Carrier Mismatch Pattern

Some systems validate that the requesting carrier matches the shipment's assigned carrier:

```python
def validate_carrier_ownership(shipment_ref, requesting_carrier_name, 
                                snapshots_df, carriers_df, aliases_df):
    """
    Check if requesting carrier owns the shipment.
    Returns (is_valid, reason, expected_carrier_id)
    """
    effective = get_effective_snapshot(snapshots_df, shipment_ref)
    if effective is None:
        return False, "Invalid Shipment Ref", None
    
    expected_carrier_id = effective['carrier_id']
    
    # Resolve requesting carrier name to ID
    requesting_id = resolve_carrier_name(requesting_carrier_name, 
                                         carriers_df, aliases_df)
    
    if requesting_id is None:
        return False, "Unknown Carrier", expected_carrier_id
    
    if requesting_id != expected_carrier_id:
        return False, "Carrier Mismatch", expected_carrier_id
    
    return True, None, expected_carrier_id
```

## Alert Reason Mapping

| Domain | Mismatch Alert |
|--------|---------------|
| Cold-chain logistics | "Carrier Mismatch" |
| Fleet maintenance | "Provider Mismatch" |
| Research stipends | "Recipient Mismatch" |
| Clinic shifts | "Clinician Mismatch" |
