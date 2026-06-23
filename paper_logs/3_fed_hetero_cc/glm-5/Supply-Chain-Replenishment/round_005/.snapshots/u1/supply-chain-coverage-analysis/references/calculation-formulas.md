# Calculation Formulas Reference

## Days On Hand

```python
if avg_daily_pull and avg_daily_pull > 0:
    current_doh = cases_on_hand / avg_daily_pull
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

## Date Normalization Helper

openpyxl returns `datetime.datetime` for date cells, not `datetime.date`. Always normalize before comparison.

```python
from datetime import datetime, date

def normalize_date(val):
    """Convert datetime or date to date. Returns None if invalid."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    # Try parsing string if needed
    try:
        return datetime.strptime(str(val), '%Y-%m-%d').date()
    except:
        return None
```

## Inbound Aggregation

### Single-Key Variant (SKU only)

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
    if not isinstance(eta, (datetime, date)):
        continue
    if state in ('Tentative', 'Hold', 'Cancelled'):
        continue
    if normalize_date(eta) > horizon_end:
        continue

    booked_by_sku[sku] = booked_by_sku.get(sku, 0) + cases
```

### Composite-Key Variant (Lane + SKU)

```python
booked_by_key = {}
for row in arrival_board:
    lane = row['lane']
    sku = row['sku']
    eta = row['eta']
    cases = row['cases']
    state = row['load_status']

    if not lane or not sku:
        continue
    if not isinstance(eta, (datetime, date)):
        continue
    if state not in ('Ready', 'Docked'):  # Exclude Draft, Cancelled
        continue
    if normalize_date(eta) > horizon_end:
        continue

    key = (lane, sku)
    booked_by_key[key] = booked_by_key.get(key, 0) + cases
```

### Composite-Key Variant (Branch + Item) with Deduplication

```python
from datetime import datetime, date

def normalize_date(val):
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    return None

# Step 1: Collect all transfers
transfer_rows = []
for row in planned_transfers_sheet.iter_rows(min_row=2, values_only=True):
    transfer_id, branch, item, transfer_date, units, status = row[:6]
    if not branch or not item:
        continue
    td = normalize_date(transfer_date)
    if td is None:
        continue
    transfer_rows.append({
        'transfer_id': transfer_id,
        'branch': branch,
        'item': item,
        'transfer_date': td,
        'units': units or 0,
        'status': status
    })

# Step 2: Deduplicate by Transfer ID (prefer Confirmed over Tentative)
transfers_by_id = {}
for t in transfer_rows:
    tid = t['transfer_id']
    if tid not in transfers_by_id:
        transfers_by_id[tid] = t
    else:
        existing = transfers_by_id[tid]
        # Prefer Confirmed over Tentative
        if t['status'] == 'Confirmed' and existing['status'] == 'Tentative':
            transfers_by_id[tid] = t
        elif t['status'] == existing['status']:
            # Same status, prefer earlier date
            if t['transfer_date'] < existing['transfer_date']:
                transfers_by_id[tid] = t

# Step 3: Aggregate by (Branch, Item) key, filtering for Confirmed and within horizon
inbound_by_key = {}
for t in transfers_by_id.values():
    if t['status'] != 'Confirmed':
        continue
    if t['transfer_date'] > horizon_end:
        continue
    key = (t['branch'], t['item'])
    inbound_by_key[key] = inbound_by_key.get(key, 0) + t['units']
```

## Pallet Calculation

```python
from math import ceil

if additional_units_needed > 0:
    pallets_required = ceil(additional_units_needed / units_per_pallet)
else:
    pallets_required = 0
```

## Earlier Delivery Flag

```python
if required_delivery_date is not None:
    # Compare against earliest valid inbound ETA
    earliest_eta = min((b['eta'] for b in valid_inbounds), default=None)
    earlier_required = (earliest_eta is None) or (earliest_eta > required_delivery_date)
else:
    earlier_required = False
```

## Full Coverage Row Construction

```python
# Build coverage row with raw float values (no rounding)
coverage_row = [
    lane,              # only for lane-snapshot variant
    branch,            # only for branch-stock variant
    sku_ref,           # or item
    cases_on_hand,      # or units_on_hand
    daily_pull,         # or daily_use
    current_doh,        # raw float
    projected_oos,
    inbound_cases,      # or inbound_units
    delivered_doh,      # raw float
    remaining_demand,
    additional_needed,
    pallets_required,
    required_delivery,
    earlier_delivery_required
]
```

## Anti-Pattern: Rounding in Output

```python
# WRONG - loses precision
ws.cell(row=r, column=c, value=round(doh, 2))

# RIGHT - full precision
ws.cell(row=r, column=c, value=doh)
```

## Parsing Grouped Snapshot Data

For Lane Snapshot format with section headers:

```python
def parse_lane_snapshot(ws):
    """Parse grouped lane snapshot with 'Lane: XXXX' section headers."""
    records = []
    current_lane = None
    
    for row in ws.iter_rows(min_row=3, values_only=True):
        cell_a = row[0]
        
        # Section header
        if cell_a and isinstance(cell_a, str) and cell_a.startswith('Lane:'):
            current_lane = cell_a.replace('Lane:', '').strip()
            continue
        
        # Column header row
        if cell_a == 'SKU':
            continue
        
        # Blank row
        if cell_a is None:
            continue
        
        # Data row
        if current_lane:
            sku = cell_a
            cases = row[1] if len(row) > 1 else 0
            daily_pull = row[2] if len(row) > 2 else 0
            records.append({
                'lane': current_lane,
                'sku': sku,
                'cases': cases or 0,
                'daily_pull': daily_pull or 0
            })
    
    return records
```

## Parsing Branch Stock with Metadata in Row 1

For Branch Stock format where row 1 contains AsOfDate and HorizonEnd:

```python
def parse_branch_stock(ws):
    """Parse branch stock with metadata in row 1."""
    from datetime import datetime, date
    
    # Row 1: AsOfDate, <value>, HorizonEnd, <value>
    as_of_raw = ws['B1'].value
    horizon_end_raw = ws['D1'].value
    
    def to_date(val):
        if isinstance(val, datetime):
            return val.date()
        if isinstance(val, date):
            return val
        return None
    
    as_of = to_date(as_of_raw)
    horizon_end = to_date(horizon_end_raw)
    
    # Row 2 is blank, row 3 has headers, data starts row 4
    records = []
    for row in ws.iter_rows(min_row=4, values_only=True):
        branch, item, units, daily_use = row[:4]
        if not branch or not item:
            continue
        records.append({
            'branch': branch,
            'item': item,
            'units': units or 0,
            'daily_use': daily_use or 0
        })
    
    return as_of, horizon_end, records
```