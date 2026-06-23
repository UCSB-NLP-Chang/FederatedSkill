---
name: supply-chain-coverage-analysis
description: Analyze inventory coverage gaps from multi-sheet Excel workbooks containing inventory snapshots and inbound/booking feeds. Calculate Days On Hand, filter valid inbounds, project out-of-stock dates, and generate procurement action lists. Trigger when you see Rack Snapshot, Lane Snapshot, Stock Snapshot, Branch Stock, Booking Feed, Arrival Board, Planned Transfers, Transfer Schedule data structures or coverage/gap analysis tasks.
---

# Supply Chain Coverage Analysis

Analyze inventory coverage and generate procurement action lists from Excel workbooks.

## When to Use

- Input is a multi-sheet `.xlsx` file containing inventory snapshots and inbound/booking feeds
- Task requires calculating coverage gaps, filtering valid inbounds, and outputting action reports
- You see sheet names like `Rack Snapshot`, `Lane Snapshot`, `Stock Snapshot`, `Branch Stock`, `Booking Feed`, `Arrival Board`, `Scheduled Inbounds`, `Planned Transfers`
- **Do not** use generic text/Read tools on `.xlsx` files — use openpyxl via Python

## Core Workflow

### 1. Inspect Structure First

Never assume headers are in row 1. Scan for known column names before parsing.

```python
# Find header row by scanning
for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
    if 'SKU_Ref' in row or 'Cases_On_Rack' in row or 'SKU' in row or 'Branch' in row:
        header_row = row_idx
        break
```

### 2. Detect Data Format Variant

Check sheet names and column headers to identify the variant:

| Variant | Snapshot Sheet | Inbound Sheet | Status Column | Qualifying Values | Key Type |
|---------|-----------------|---------------|--------------|-------------------|----------|
| rack-snapshot-booking-feed | Rack Snapshot | Booking Feed | Booking State | Firm, Locked | SKU |
| lane-snapshot-arrival-board | Lane Snapshot | Arrival Board | Load Status | Ready, Docked | (Lane, SKU) |
| branch-stock-transfer-schedule | Branch Stock | Planned Transfers | Status | Confirmed | (Branch, Item) |

### 3. Handle Grouped/Hierarchical Snapshot Data

Lane Snapshot format groups data by location with section headers:

```python
current_lane = None
for row in ws.iter_rows(min_row=3, values_only=True):
    cell_a = row[0]
    # Check for section header like "Lane: COOLER-A"
    if cell_a and isinstance(cell_a, str) and cell_a.startswith('Lane:'):
        current_lane = cell_a.replace('Lane:', '').strip()
        continue
    # Skip header rows (SKU, Cases, Daily Pull)
    if cell_a == 'SKU':
        continue
    # Data row - use current_lane as context
    if current_lane and cell_a:
        records.append((current_lane, cell_a, row[1], row[2]))
```

### 4. Extract Metadata

Read AsOfDate and HorizonEnd from the snapshot sheet (typically row 1 or dedicated config sheet).

```python
from datetime import datetime, date

cell_value = ws['B1'].value
if isinstance(cell_value, datetime):
    as_of = cell_value.date()
elif isinstance(cell_value, date):
    as_of = cell_value
else:
    as_of = datetime.strptime(str(cell_value), '%Y-%m-%d').date()
```

Calculate: `PlanningDays = (HorizonEnd - AsOfDate).days + 1`

### 5. Filter Inbound Feed (Critical for Correctness)

Include only inbounds where:
- Key (SKU, Lane+SKU, or Branch+Item) is not None/blank
- ETA/Transfer Date is a valid datetime (not string 'bad-date', not None)
- Status is qualifying (Firm/Locked for Booking State; Ready/Docked for Load Status; Confirmed for Status)
- ETA <= HorizonEnd (within planning window)

```python
# Variant-specific qualifying statuses
QUALIFYING_STATUSES = {
    'rack-snapshot-booking-feed': {'Firm', 'Locked'},
    'lane-snapshot-arrival-board': {'Ready', 'Docked'},
    'branch-stock-transfer-schedule': {'Confirmed'}
}
```

### 6. Handle Duplicate Transfer IDs (branch-stock-transfer-schedule variant)

When the same Transfer ID appears multiple times with different statuses or dates:
- Prefer Confirmed over Tentative
- If same status, prefer earlier date

```python
# Deduplicate transfers by ID
transfers_by_id = {}
for row in transfer_rows:
    tid = row['transfer_id']
    if tid not in transfers_by_id:
        transfers_by_id[tid] = row
    else:
        # Prefer Confirmed over Tentative
        existing = transfers_by_id[tid]
        if row['status'] == 'Confirmed' and existing['status'] == 'Tentative':
            transfers_by_id[tid] = row
        elif row['status'] == existing['status']:
            # Same status, prefer earlier date
            if row['transfer_date'] < existing['transfer_date']:
                transfers_by_id[tid] = row
```

### 7. Calculate Coverage per Record

For each record in the snapshot:

| Field | Formula |
|-------|---------|
| CurrentDaysOnHand | `UnitsOnHand / DailyUse` (guard division if use=0) |
| ProjectedOOSDate | `AsOfDate + timedelta(days=floor(DaysOnHand))` |
| InboundUnitsByHorizon | Sum from filtered inbounds |
| RemainingDemandUnits | `DailyUse * PlanningDays` |
| AdditionalUnitsNeeded | `max(0, RemainingDemandUnits - UnitsOnHand - InboundUnitsByHorizon)` |
| PalletsRequired | `ceil(AdditionalUnitsNeeded / UnitsPerPallet)` if needed > 0 |

Note: Some variants use "Cases" terminology, others use "Units" — adapt field names accordingly.

See `references/calculation-formulas.md` for detailed code snippets.

### 8. Determine Delivery Requirements

- RequiredDeliveryDate = ProjectedOOSDate if AdditionalUnitsNeeded > 0
- EarlierDeliveryRequired = True if earliest valid inbound ETA > RequiredDeliveryDate, or no valid inbound exists

### 9. Generate Output Workbook

Create two sheets (names vary by variant):

| Variant | Coverage Sheet | Actions Sheet |
|---------|----------------|---------------|
| rack-snapshot-booking-feed | Rack_Coverage | Commit_Gap_Actions |
| lane-snapshot-arrival-board | Lane_Coverage | Restock_Actions |
| branch-stock-transfer-schedule | Branch_Item_Coverage | Transfer_Gap_List |

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Validation Checklist

- [ ] AsOfDate and HorizonEnd parsed as datetime objects
- [ ] PlanningDays includes both endpoints (difference + 1)
- [ ] Inbound filter excludes: null keys, non-datetime ETAs, non-qualifying states, dates beyond horizon
- [ ] Duplicate Transfer IDs deduplicated (prefer Confirmed over Tentative)
- [ ] Division by zero guarded when DailyPull/DailyUse is 0 or None
- [ ] PalletsRequired uses ceiling, rounds up for any remainder
- [ ] EarlierDeliveryRequired correctly identifies same-day or past requirements
- [ ] Composite keys (Lane+SKU, Branch+Item) handled correctly

## Common Data Quality Issues

| Issue | Pattern | Fix |
|-------|---------|-----|
| Missing SKU/Branch | `None` in key column | Skip row |
| Invalid date | String 'bad-date' or non-datetime | Check isinstance before comparison |
| Non-qualifying status | Draft/Tentative/Hold/Cancelled | Exclude from sum |
| Duplicate Transfer ID | Same ID with different dates/statuses | Prefer Confirmed, then earlier date |
| Planner notes | Rows with all None values | Skip rows where key is None |
| Zero inventory | UnitsOnHand == 0 | Still calculate; CurrentDaysOnHand = 0 |
| Grouped data | "Lane: XXXX" section headers | Track current lane context while parsing |

## Anti-Patterns

- **Do not** include Draft/Tentative/Hold/Cancelled bookings in coverage calculations (overstates supply)
- **Do not** treat Cancelled status as valid supply
- **Do not** use string comparison for dates; parse to datetime first
- **Do not** floor pallet calculation; always round up partial pallets
- **Do not** assume DailyPull > 0; guard division
- **Do not** assume headers are in row 1 — scan for column names
- **Do not** compare cell values directly without type checking (TypeError risk)
- **Do not** use str() on datetime cells expecting a specific format
- **Do not** assume flat table structure — check for grouped/sectioned formats
- **Do not** assume unique Transfer IDs — deduplicate before aggregation

## Known Invariants (by Variant)

### rack-snapshot-booking-feed
- Sheet names: `Rack Snapshot` / `Booking Feed`
- Key: SKU_Ref (single column)
- State column: `Booking State` with values `Firm` / `Locked` / `Tentative` / `Hold`
- Qualifying states: Firm, Locked
- Output sheets: `Rack_Coverage` / `Commit_Gap_Actions`

### lane-snapshot-arrival-board
- Sheet names: `Lane Snapshot` / `Arrival Board`
- Key: (Lane, SKU) composite — Lane from section header, SKU from data row
- State column: `Load Status` with values `Ready` / `Docked` / `Draft` / `Cancelled`
- Qualifying states: Ready, Docked
- Snapshot format: Grouped by lane with "Lane: XXXX" section headers
- Output sheets: `Lane_Coverage` / `Restock_Actions`

### branch-stock-transfer-schedule
- Sheet names: `Branch Stock` / `Planned Transfers`
- Key: (Branch, Item) composite — both from data rows
- State column: `Status` with values `Confirmed` / `Tentative` / `Cancelled`
- Qualifying states: Confirmed only
- Metadata: AsOfDate and HorizonEnd in row 1 of Branch Stock sheet
- Deduplication: Transfer ID may appear multiple times; prefer Confirmed over Tentative
- Terminology: Uses "Units" instead of "Cases"
- Output sheets: `Branch_Item_Coverage` / `Transfer_Gap_List`

## Debugging Pattern

When extraction fails, print types and values:

```python
for row in ws.iter_rows(min_row=1, max_row=5):
    for cell in row:
        print(f"{cell.coordinate}: value={cell.value}, type={type(cell.value)}")
```