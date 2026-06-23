# Amendment and Revision Patterns

## Amendment Systems

Some approval workflows allow post-hoc amendments to approved amounts.

### CSV Amendment Format

```csv
order_id,amendment_no,amended_charge,decision
MO-9003,1,1175.0,approved
MO-9004,1,990.0,rejected
```

### Processing Logic

```python
def apply_amendments(base_orders, amendments_csv):
    """
    Apply approved amendments to base order amounts.
    Rejected amendments are ignored.
    """
    # Index amendments by order_id, keeping only approved decisions
    approved_amendments = {}
    for row in amendments_csv:
        if row['decision'] == 'approved':
            order_id = row['order_id']
            # Keep latest amendment if multiple exist
            amend_no = int(row['amendment_no'])
            if order_id not in approved_amendments or amend_no > approved_amendments[order_id][0]:
                approved_amendments[order_id] = (amend_no, float(row['amended_charge']))
    
    # Apply to orders
    result = {}
    for order_id, order_data in base_orders.items():
        if order_id in approved_amendments:
            _, amended_amount = approved_amendments[order_id]
            result[order_id] = {**order_data, 'approved_amount': amended_amount}
        else:
            result[order_id] = order_data
    
    return result
```

## Revision Systems

Some systems track multiple revisions of the same approval.

### Revision Processing

```python
def get_latest_approved_revision(revisions_df):
    """
    From a dataframe with approval_code, revision_no, approval_state, amount
    return dict of code -> latest approved revision's amount.
    """
    # Filter to approved state only
    approved = revisions_df[revisions_df['approval_state'] == 'approved']
    
    # Group by code, get max revision
    latest = approved.loc[approved.groupby('approval_code')['revision_no'].idxmax()]
    
    return dict(zip(latest['approval_code'], latest['amount']))
```

## Key Decision Rules

1. **Always filter by decision/status** — Don't apply rejected amendments
2. **Track amendment numbers** — Higher amendment_no supersedes lower
3. **Preserve original for audit** — Keep trace of what was amended
4. **Amount comparison tolerance** — Use ≤$0.01 tolerance for float comparison
