---
name: supply-chain-coverage-analysis
description: Analyze inventory coverage gaps from multi-sheet Excel workbooks containing inventory snapshots and inbound/booking feeds. Calculate Days On Hand, filter valid inbounds, project out-of-stock dates, and generate procurement action lists. Trigger when you see Rack Snapshot, Lane Snapshot, Stock Snapshot, Booking Feed, Arrival Board data structures or coverage/gap analysis tasks.
---

# Supply Chain Coverage Analysis

Analyze inventory coverage and generate procurement action lists from Excel workbooks.

## When to Use

- Input is a multi-sheet `.xlsx` file containing inventory snapshots and inbound/booking feeds
- Task requires calculating coverage gaps, filtering valid inbounds, and outputting action reports
- You see sheet names like `Rack Snapshot`, `Lane Snapshot`, `Stock Snapshot`, `Booking Feed`, `Arrival Board`, `Scheduled Inbounds`
- **Do not** use generic text/Read tools on `.xlsx` files — use openpyxl via Python

## Core Workflow

### 1. Inspect Structure First

Never assume headers are in row 1. Scan for known column names before parsing.

```python
# Find header row by scanning
for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
    if 'SKU_Ref' in row or 'Cases_On_Rack' in row or 'SKU' in row:
        header_row = row_idx
        break
```

### 2. Detect Data Format Variant

Check sheet names and column headers to identify the variant:

| Variant | Snapshot Sheet | Inbound Sheet | Status Column | Qualifying Values |
|---------|-----------------|---------------|--------------|-------------------|
| rack-snapshot-booking-feed | Rack Snapshot | Booking Feed | Booking State | Firm, Locked |
| lane-snapshot-arrival-board | Lane Snapshot | Arrival Board | Load Status | Ready, Docked |

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
- SKU/Lane key is not None/blank
- ETA is a valid datetime (not string 'bad-date', not None)
- Status is qualifying (Firm/Locked for Booking State; Ready/Docked for Load Status)
- ETA <= HorizonEnd (within planning window)

```python
# Variant-specific qualifying statuses
QUALIFYING_STATUSES = {
    'rack-snapshot-booking-feed': {'Firm', 'Locked'},
    'lane-snapshot-arrival-board': {'Ready', 'Docked'}
}

booked_by_key = {}
for row in inbound_sheet.iter_rows(min_row=2, values_only=True):
    # Adjust column indices based on variant
    key = (row[0], row[1]) if variant == 'lane-snapshot-arrival-board' else row[0]  # (Lane, SKU) or SKU
    eta_raw, cases, state = row[2], row[3], row[4]

    if not key or state not in QUALIFYING_STATUSES[variant]:
        continue
    eta = normalize_date(eta_raw)
    if eta is None or eta > horizon_end:
        continue
    booked_by_key[key] = booked_by_key.get(key, 0) + (cases or 0)
```

### 6. Calculate Coverage per Record

For each record in the snapshot:

| Field | Formula |
|-------|---------|
| CurrentDaysOnHand | `CasesOnHand / DailyPull` (guard division if pull=0) |
| ProjectedOOSDate | `AsOfDate + timedelta(days=floor(DaysOnHand))` |
| InboundCasesByHorizon | Sum from filtered inbounds |
| RemainingDemandCases | `DailyPull * PlanningDays` |
| AdditionalCasesNeeded | `max(0, RemainingDemandCases - CasesOnHand - InboundCasesByHorizon)` |
| PalletsRequired | `ceil(AdditionalCasesNeeded / CasesPerPallet)` if needed > 0 |

See `references/calculation-formulas.md` for detailed code snippets.

### 7. Determine Delivery Requirements

- RequiredDeliveryDate = ProjectedOOSDate if AdditionalCasesNeeded > 0
- EarlierDeliveryRequired = True if earliest valid inbound ETA > RequiredDeliveryDate, or no valid inbound exists

### 8. Generate Output Workbook

Create two sheets (names vary by variant):

| Variant | Coverage Sheet | Actions Sheet |
|---------|----------------|---------------|
| rack-snapshot-booking-feed | Rack_Coverage | Commit_Gap_Actions |
| lane-snapshot-arrival-board | Lane_Coverage | Restock_Actions |

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
- [ ] Division by zero guarded when DailyPull is 0 or None
- [ ] PalletsRequired uses ceiling, rounds up for any remainder
- [ ] EarlierDeliveryRequired correctly identifies same-day or past requirements
- [ ] Composite keys (Lane+SKU) handled correctly for lane-snapshot variant

## Common Data Quality Issues

| Issue | Pattern | Fix |
|-------|---------|-----|
| Missing SKU | `None` in SKU column | Skip row |
| Invalid date | String 'bad-date' or non-datetime | Check isinstance before comparison |
| Non-qualifying status | Draft/Tentative/Hold/Cancelled | Exclude from sum |
| Planner notes | Rows with all None values | Skip rows where key is None |
| Zero inventory | CasesOnHand == 0 | Still calculate; CurrentDaysOnHand = 0 |
| Grouped data | "Lane: XXXX" section headers | Track current lane context while parsing |

## Anti-Patterns

- **Do not** include Draft/Tentative/Hold bookings in coverage calculations (overstates supply)
- **Do not** treat Cancelled status as valid supply
- **Do not** use string comparison for dates; parse to datetime first
- **Do not** floor pallet calculation; always round up partial pallets
- **Do not** assume DailyPull > 0; guard division
- **Do not** assume headers are in row 1 — scan for column names
- **Do not** compare cell values directly without type checking (TypeError risk)
- **Do not** use str() on datetime cells expecting a specific format
- **Do not** assume flat table structure — check for grouped/sectioned formats

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
- Fixed pallet size: 54 cases (produce standard)

## Helper Resources

- **scripts/calculate_coverage.py**: Deterministic baseline for rack-snapshot variant. Usage: `python3 scripts/calculate_coverage.py <input.xlsx> <output.xlsx>`
- **scripts/calculate_lane_coverage.py**: Deterministic baseline for lane-snapshot variant. Usage: `python3 scripts/calculate_lane_coverage.py <lane_snapshot.xlsx> <arrival_board.xlsx> <output.xlsx>`
- **references/calculation-formulas.md**: Detailed formulas for each calculation step, including composite-key handling.
- **references/excel-datetime-handling.md**: Patterns for handling datetime.datetime vs datetime.date type issues with openpyxl.

## Debugging Pattern

When extraction fails, print types and values:

```python
for row in ws.iter_rows(min_row=1, max_row=5):
    for cell in row:
        print(f"{cell.coordinate}: value={cell.value}, type={type(cell.value)}")
```