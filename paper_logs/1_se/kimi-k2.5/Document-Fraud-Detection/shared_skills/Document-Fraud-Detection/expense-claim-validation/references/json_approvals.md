# JSON Approval Structures

## Nested Depot/Region Pattern

Fleet and field service systems often organize orders by depot or region.

### Example Structure

```json
{
  "depots": [
    {
      "depot_code": "D-NORTH",
      "orders": [
        {"order_id": "MO-9001", "provider_id": "P801", "approved_charge": 1800.0, "lifecycle": "approved"},
        {"order_id": "MO-9002", "provider_id": "P802", "approved_charge": 2400.0, "lifecycle": "approved"}
      ]
    },
    {
      "depot_code": "D-CENTRAL",
      "orders": [
        {"order_id": "MO-9003", "provider_id": "P803", "approved_charge": 1150.0, "lifecycle": "approved"}
      ]
    }
  ]
}
```

### Flattening Pattern

```python
import json

def flatten_depot_orders(json_path):
    """Flatten nested depot structure to order_id -> order_data mapping."""
    with open(json_path) as f:
        data = json.load(f)
    
    orders = {}
    for depot in data.get('depots', []):
        depot_code = depot.get('depot_code', 'UNKNOWN')
        for order in depot.get('orders', []):
            order_id = order['order_id']
            orders[order_id] = {
                'provider_id': order['provider_id'],
                'approved_amount': order['approved_charge'],
                'lifecycle': order['lifecycle'],
                'depot_code': depot_code  # Preserve for context
            }
    
    return orders
```

## Lifecycle Status Values

| Value | Meaning | Validation Action |
|-------|---------|-------------------|
| `approved` | Active and valid | Accept |
| `active` | Active and valid | Accept |
| `closed` | Completed, no longer valid | Reject as "Invalid Order ID" |
| `completed` | Completed, no longer valid | Reject as "Invalid Order ID" |
| `draft` | Not yet approved | Reject as "Invalid Order ID" |
| `pending` | Awaiting approval | Reject as "Invalid Order ID" |
| `rejected` | Denied | Reject as "Invalid Order ID" |

## Provider ID Matching

For fleet/maintenance systems, verify the claim's provider matches the order's assigned provider:

```python
def validate_provider_ownership(order_id, provider_name, orders, providers, aliases):
    """
    Check if the claiming provider owns the specified order.
    Returns (is_valid, reason, expected_provider_id)
    """
    if order_id not in orders:
        return False, "Invalid Order ID", None
    
    order = orders[order_id]
    expected_provider_id = order['provider_id']
    
    # Resolve claiming provider name to ID
    claiming_provider_id = resolve_provider_name(provider_name, providers, aliases)
    
    if claiming_provider_id is None:
        return False, "Unknown Provider", expected_provider_id
    
    if claiming_provider_id != expected_provider_id:
        return False, "Provider Mismatch", expected_provider_id
    
    return True, None, expected_provider_id
```
