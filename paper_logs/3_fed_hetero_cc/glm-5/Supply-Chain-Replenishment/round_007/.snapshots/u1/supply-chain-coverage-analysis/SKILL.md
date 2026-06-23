---
name: supply-chain-coverage-analysis
description: Analyze supply chain inventory snapshots and inbound feeds to calculate coverage gaps and generate dispatch workbooks. Handles rack/zone stock, booking/lane/branch arrivals, alias resolution, and deduplication. Use when given stock snapshots and delivery/transfers feeds requiring coverage math and gap reports.
---

# Supply Chain Coverage Analysis

## When to Use
- Multi-sheet Excel → coverage + gap report
- Stock snapshot + inbound feed → days-on-hand, OOS projections, pallet requirements
- Any task with inventory data + planned arrivals + gap/dispatch output

## Anti-Pattern: Read Tool on Binary Excel
The Read tool cannot read binary .xlsx files. Attempting to use it will fail.
**Always use Python with openpyxl for Excel files.**
```bash
python3 -c "import openpyxl; print('openpyxl available')" 2>/dev/null || pip install openpyxl
```

## Workflow

### 1. Load Input Workbooks
```python
import openpyxl
from openpyxl import Workbook
from datetime import datetime, date, timedelta
from math import ceil

# Load all input workbooks with data_only=True
wb_stock = openpyxl.load_workbook(stock_path, data_only=True)
wb_feed = openpyxl.load_workbook(feed_path, data_only=True)
```

### 2. Detect Data Format Variant
Inspect sheet names and column headers to identify the variant:

| Variant | Stock Sheet | Feed Sheet | Key Type | Qualifying States | Pallet Size |
|---------|------------|------------|----------|-------------------|-------------|
| B1: Rack+Booking | Inventory Snapshot | Bookings/Inbounds | SKU | Firm/Confirmed | 36 |
| B2: Lane+Arrival | Lane Snapshot (section-based) | Arrival Board | Lane+SKU | Confirmed | 36 |
| B3: Branch+Transfer | Branch Stock | Planned Transfers | Branch+Item | Confirmed | 36 |
| B4: Zone+Feed+Alias | Zone Snapshot | Zone Feed | Zone+SKU | Released/Staged | 36 |

### 3. Parse Metadata
```python
def parse_date(val):
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    try:
        return datetime.strptime(str(val).strip(), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None

# B1/B4: metadata in specific cells
as_of_date = parse_date(ws_stock['B1'].value)
horizon_end = parse_date(ws_stock['D1'].value)
planning_days = (horizon_end - as_of_date).days
```

### 4. Parse Stock Data
```python
# Standard tabular (B1, B3, B4): data rows with Zone/Branch/SKU, On_Hand, Daily_Demand
stock_rows = []
for row in ws_stock.iter_rows(min_row=4, values_only=True):
    zone, sku, on_hand, daily_demand = row
    if zone is None:
        break
    stock_rows.append({'zone': zone, 'sku': sku, 'on_hand': on_hand, 'daily': daily_demand})

# Section-based (B2): Lane headers followed by SKU rows
current_lane = None
stock_rows = []
for row in ws_lane.iter_rows(min_row=2, values_only=True):
    if row[0] and 'Lane' in str(row[0]):
        current_lane = str(row[0]).replace('Lane: ', '').strip()
    elif current_lane and row[1]:
        stock_rows.append({'zone': current_lane, 'sku': row[1], 'on_hand': row[2], 'daily': row[3]})
```

### 5. Process Inbound Feed
```python
# B4: Alias resolution required
if variant == 'B4':
    alias_map = {}
    for row in ws_alias.iter_rows(min_row=2, values_only=True):
        alias_val, canonical = row
        if alias_val is None:
            break
        alias_map[alias_val] = canonical

# Filter and validate feed rows
raw_feed = []
for row in ws_feed.iter_rows(min_row=2, values_only=True):
    # B4: Record Type filter
    if variant == 'B4':
        rec_type = row[0]
        if rec_type != 'DELIVERY':
            continue
        dispatch_ref, revision, zone_alias, sku_code, eta, units, release_state = row[1:]
    else:
        # B1/B2/B3: adapt column positions
        dispatch_ref, sku_code, eta, units, release_state = row[0], row[1], row[2], row[3], row[4]
        revision = None
        zone_alias = None

    # Skip blank SKU
    if sku_code is None or str(sku_code).strip() == '':
        continue
    # Validate ETA
    eta_date = parse_date(eta)
    if eta_date is None:
        continue

    raw_feed.append({
        'dispatch_ref': dispatch_ref,
        'revision': revision if revision is not None else 0,
        'zone_alias': zone_alias,
        'sku': sku_code,
        'eta': eta_date,
        'units': units,
        'state': release_state,
    })

# B4: Deduplicate by Dispatch_Ref (keep highest Revision)
if variant == 'B4':
    deduped = {}
    for r in raw_feed:
        key = r['dispatch_ref']
        if key not in deduped or r['revision'] > deduped[key]['revision']:
            deduped[key] = r
    raw_feed = list(deduped.values())

# B3: Deduplicate by Transfer ID (keep max date, prefer Confirmed)
if variant == 'B3':
    deduped = {}
    for r in raw_feed:
        key = r['dispatch_ref']
        if key not in deduped:
            deduped[key] = r
        else:
            if r['state'] == 'Confirmed' and deduped[key]['state'] != 'Confirmed':
                deduped[key] = r
            elif r['eta'] > deduped[key]['eta']:
                deduped[key] = r
    raw_feed = list(deduped.values())

# Filter by qualifying states
qualifying = []
for r in raw_feed:
    if variant == 'B4':
        if r['state'] not in ('Released', 'Staged'):
            continue
        canonical_zone = alias_map.get(r['zone_alias'])
        if canonical_zone is None:
            continue
        r['zone'] = canonical_zone
    elif variant == 'B3':
        if r['state'] != 'Confirmed':
            continue
    elif variant in ('B1', 'B2'):
        if r['state'] not in ('Firm', 'Confirmed'):
            continue
    # B4: drop deliveries beyond horizon
    if variant == 'B4' and r['eta'] > horizon_end:
        continue
    qualifying.append(r)
```

### 6. Calculate Coverage
```python
PALLET_SIZE = 36

coverage = []
for s in stock_rows:
    zone, sku = s['zone'], s['sku']
    on_hand = s['on_hand']
    daily = s['daily']

    days_on_hand = on_hand / daily
    oos_date = as_of_date + timedelta(days=days_on_hand)

    inbound_units = sum(r['units'] for r in qualifying if r['zone'] == zone and r['sku'] == sku)
    delivered_days = inbound_units / daily
    remaining_demand = daily * planning_days
    additional_needed = max(0, remaining_demand - on_hand - inbound_units)
    pallets = ceil(additional_needed / PALLET_SIZE) if additional_needed > 0 else 0

    req_date = oos_date if oos_date <= horizon_end else horizon_end

    earliest_inbound = min(
        (r['eta'] for r in qualifying if r['zone'] == zone and r['sku'] == sku),
        default=None
    )
    earlier_req = False
    if pallets > 0:
        if inbound_units == 0:
            earlier_req = True
        elif earliest_inbound and earliest_inbound > req_date:
            earlier_req = True

    coverage.append({
        'Zone': zone, 'SKU': sku,
        'Units_On_Hand': on_hand, 'Daily_Demand_Units_Per_Day': daily,
        'Current_Days_On_Hand': days_on_hand, 'Projected_OOS_Date': oos_date,
        'Inbound_Units_By_Horizon': inbound_units,
        'Delivered_Days_On_Hand': delivered_days,
        'Remaining_Demand_Units': remaining_demand,
        'Additional_Units_Needed': additional_needed,
        'Pallets_Required': pallets,
        'Required_Delivery_Date': req_date,
        'Earlier_Delivery_Required': earlier_req,
    })
```

### 7. Generate Output Workbook
```python
out_wb = Workbook()

# Coverage sheet
ws_cov = out_wb.active
ws_cov.title = 'Zone_Coverage'  # Adapt per variant
ws_cov.append(['Field', 'Value'])
ws_cov.append(['AsOfDate', as_of_date])
ws_cov.append(['HorizonEnd', horizon_end])
ws_cov.append(['PlanningDays', planning_days])
ws_cov.append([])
headers = ['Zone', 'SKU', 'Units_On_Hand', 'Daily_Demand_Units_Per_Day',
           'Current_Days_On_Hand', 'Projected_OOS_Date', 'Inbound_Units_By_Horizon',
           'Delivered_Days_On_Hand', 'Remaining_Demand_Units',
           'Additional_Units_Needed', 'Pallets_Required',
           'Required_Delivery_Date', 'Earlier_Delivery_Required']
ws_cov.append(headers)
for c in coverage:
    ws_cov.append([c[h] for h in headers])

# Gap list sheet
ws_gap = out_wb.create_sheet('Dispatch_Gap_List')
gap_headers = ['Zone', 'SKU', 'Required_Delivery_Date', 'Pallets_Required',
               'Additional_Units_Needed', 'Earlier_Delivery_Required']
ws_gap.append(gap_headers)
for c in coverage:
    if c['Pallets_Required'] > 0:
        ws_gap.append([c[h] for h in gap_headers])

out_wb.save(output_path)
```

### 8. Verify Output
```python
wb_check = openpyxl.load_workbook(output_path, data_only=True)
for sheet_name in wb_check.sheetnames:
    print(f"=== {sheet_name} ===")
    for row in wb_check[sheet_name].iter_rows(values_only=True):
        print(row)
```

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### B1: rack-snapshot + booking-feed
- Exclude null SKUs and invalid ETAs from bookings
- Count only Firm/Confirmed states; Tentative/Hold must be excluded
- datetime.datetime vs datetime.date TypeError: always normalize with `.date()`

### B2: lane-snapshot + arrival-board
- Parse section headers (Lane: XXXX) with current_lane tracking
- Aggregate by composite key (Lane + SKU), not SKU alone
- Exclude Draft/Cancelled arrival states

### B3: branch-stock + planned-transfers
- Data starts row 4+ (metadata row 1)
- Deduplicate by Transfer ID BEFORE filtering by status (keep max date per ID)
- Filter Status=Confirmed only; Tentative excluded
- Aggregate by composite key (Branch + Item), not Item alone

### B4: zone-snapshot + feed + alias-map
- Record Type must be 'DELIVERY' — exclude MESSAGE, NOTE, and all other types
- Deduplicate by Dispatch_Ref keeping highest Revision
- Release State: only 'Released' or 'Staged' — exclude Pending, Hold, ignore
- Resolve Zone Alias via alias map; skip unmapped zones (do not hard-fail)
- ETA must be <= HorizonEnd after validation
- Pallet size = 36
- Output sheet names: Zone_Coverage, Dispatch_Gap_List
