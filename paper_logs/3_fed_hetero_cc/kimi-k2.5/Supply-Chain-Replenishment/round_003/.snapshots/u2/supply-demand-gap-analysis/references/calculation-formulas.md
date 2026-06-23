# Calculation Formulas Reference

## Days On Hand

```python
if avg_daily_pull and avg_daily_pull > 0:
    current_doh = cases_on_rack / avg_daily_pull
else:
    current_doh = None  # or 0 if business rules dictate
```

## Projected Out-of-Stock Date

```python
from datetime import timedelta
from math import floor

if current_doh is not None:
    projected_oos = as_of_date + timedelta(days=floor(current_doh))
else:
    projected_oos = as_of_date  # immediate if no consumption rate
```

## Booking Aggregation

```python
from datetime import datetime

booked_by_sku = {}
for row in booking_feed:
    sku = row['sku_ref']
    eta = row['eta']
    cases = row['booked_cases']
    state = row['booking_state']
    
    if sku is None:
        continue
    if not isinstance(eta, datetime):
        continue
    if state in ('Tentative', 'Hold'):
        continue
    if eta > horizon_end:
        continue
    
    booked_by_sku[sku] = booked_by_sku.get(sku, 0) + cases
```

## Pallet Calculation

```python
from math import ceil

if additional_cases_needed > 0:
    pallets_required = ceil(additional_cases_needed / cases_per_pallet)
else:
    pallets_required = 0
```

## Earlier Delivery Flag

```python
if required_delivery_date is not None:
    earlier_required = required_delivery_date <= as_of_date
else:
    earlier_required = False
```