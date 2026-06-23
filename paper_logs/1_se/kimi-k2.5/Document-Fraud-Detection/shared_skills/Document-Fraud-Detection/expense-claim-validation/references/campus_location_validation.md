# Campus and Location Code Validation

## Overview

Some payment request systems include campus, location, or site codes that must match between the request and the approved authorization. These codes may also be subject to amendment.

## Common Patterns

### Research Stipend Example

```csv
# award_authorizations.csv
award_ref,recipient_code,approved_value,campus_code,state
AWD-3004,R504,1600.0,CAMP-W,active

# award_adjustments.csv
award_ref,revision_no,adjusted_value,campus_code,state
AWD-3004,1,1600.0,CAMP-C,approved
```

In this case, the approved campus code is `CAMP-C` (from amendment revision 1), not `CAMP-W` (from base authorization).

## Validation Logic

```python
def get_effective_approval(award_ref, base_auth, amendments):
    """
    Get the effective approved values considering amendments.
    Returns dict with approved_amount and campus_code.
    """
    # Start with base values
    effective = {
        'approved_amount': base_auth['approved_value'],
        'campus_code': base_auth.get('campus_code'),
        'recipient_code': base_auth['recipient_code'],
        'state': base_auth['state']
    }
    
    # Find applicable amendments
    if award_ref in amendments:
        # Get max revision with approved state
        approved_amends = [
            a for a in amendments[award_ref] 
            if a['state'] == 'approved'
        ]
        if approved_amends:
            latest = max(approved_amends, key=lambda x: x['revision_no'])
            effective['approved_amount'] = latest['adjusted_value']
            effective['campus_code'] = latest.get('campus_code', effective['campus_code'])
    
    return effective


def validate_campus(request_campus, effective_approval):
    """Check if requested campus matches approved campus."""
    approved_campus = effective_approval.get('campus_code')
    
    if approved_campus is None:
        return True, None  # No campus requirement
    
    if request_campus != approved_campus:
        return False, f"Campus Mismatch: requested {request_campus}, approved {approved_campus}"
    
    return True, None
```

## Amendment Processing with Multi-Field Updates

When amendments can modify multiple fields:

```python
def apply_revision_amendments(base_orders, amendments_df):
    """
    Apply revision-based amendments that may update amount and/or campus.
    """
    # Group amendments by order_id
    by_order = amendments_df.groupby('award_ref')
    
    result = {}
    for order_id, base in base_orders.items():
        effective = dict(base)
        
        if order_id in by_order.groups:
            order_amends = by_order.get_group(order_id)
            # Filter to approved only
            approved = order_amends[order_amends['state'] == 'approved']
            
            if len(approved) > 0:
                # Get latest revision
                latest = approved.loc[approved['revision_no'].idxmax()]
                effective['approved_value'] = latest['adjusted_value']
                if 'campus_code' in latest and pd.notna(latest['campus_code']):
                    effective['campus_code'] = latest['campus_code']
        
        result[order_id] = effective
    
    return result
```

## Alert Reason Mapping

| Domain | Mismatch Alert |
|--------|---------------|
| Research Stipends | "Campus Mismatch" |
| Multi-site Payroll | "Location Mismatch" |
| Facility Billing | "Site Mismatch" |
| Regional Contracts | "Region Mismatch" |

## Key Decision Rules

1. **Amendments override base** — Always apply approved amendments, even if only campus changes
2. **Check all amended fields** — Don't assume amendments only affect amounts
3. **Null campus handling** — If base has no campus but amendment adds one, use amended value
4. **Rejected amendments** — Ignore completely; don't partially apply
