# Refund Reserve Data Processing Pipeline

## Complete Processing Flow

```python
from collections import defaultdict

def process_refund_data(json_data, overrides_csv, bucket):
    """Process refund reserve data through full pipeline."""
    
    # Step 1: Extract items for bucket
    items = []
    for segment in json_data['segments']:
        if segment['bucket'] == bucket:
            items.extend(segment['snapshots'])
    
    # Step 2: Filter approved detail rows
    filtered = [
        item for item in items
        if item.get('approved') == True 
        and item.get('row_kind') == 'detail'
    ]
    
    # Step 3: Deduplicate by version (keep highest)
    by_case = defaultdict(list)
    for item in filtered:
        by_case[item['case_id']].append(item)
    
    deduped = []
    for case_id, versions in by_case.items():
        highest = max(versions, key=lambda x: x['version'])
        deduped.append(highest)
    
    # Step 4: Apply overrides/inserts
    # (Implementation depends on patch format)
    
    # Step 5: Sort by customer_name, then case_id
    deduped.sort(key=lambda x: (x['customer_name'], x['case_id']))
    
    return deduped
```

## JSON Structure Reference

```json
{
  "segments": [
    {
      "bucket": "enterprise",
      "snapshots": [
        {
          "case_id": "ER-100",
          "version": 2,
          "approved": true,
          "row_kind": "detail",
          "customer_name": "Apex Media",
          "opening_amount": 0,
          "flow_months": {
            "aug": {"accrued": 6000, "credited": 1500},
            "sep": {"credited": 1500},
            "oct": {"accrued": 2000, "credited": 1750},
            "nov": {"credited": 1750}
          },
          "term_hint": 6,
          "memo_text": "Annual refund reserve",
          "account_code": 2215
        }
      ]
    }
  ]
}
```

## Calculated Ending Balance

For each month, calculate:
```
aug_ending = opening_amount + aug.accrued - aug.credited
sep_ending = aug_ending + sep.accrued - sep.credited
oct_ending = sep_ending + oct.accrued - oct.credited
nov_ending = oct_ending + nov.accrued - nov.credited
```

Note: Some periods may have `accrued=0` (only releases).
