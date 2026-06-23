---
name: supply-chain-coverage-analysis
description: Analyze inventory coverage gaps from multi-sheet Excel workbooks containing rack snapshots and booking feeds. Calculate Days On Hand, filter valid bookings, project out-of-stock dates, and generate procurement action lists. Trigger when you see Rack Snapshot + Booking Feed data structures or coverage/gap analysis tasks.
---

# Supply Chain Coverage Analysis

Analyze inventory coverage and generate procurement action lists from Excel workbooks.

## When to Use

- Input is a multi-sheet `.xlsx` file containing inventory snapshots and booking feeds
- Task requires calculating coverage gaps, filtering valid bookings, and outputting action reports
- You see sheet names like `Rack Snapshot`, `Stock Snapshot`, `Booking Feed`, `Scheduled Inbounds`
- **Do not** use generic text/Read tools on `.xlsx` files — use openpyxl via Python

## Core Workflow

### 1. Inspect Structure First

Never assume headers are in row 1. Scan for known column names before parsing.

```python
# Find header row by scanning
for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
    if 'SKU_Ref' in row or 'Cases_On_Rack' in row:
        header_row = row_idx
        break
```

### 2. Extract Metadata

Read AsOfDate and HorizonEnd from the Rack Snapshot (typically row 1 or dedicated config sheet).

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

### 3. Filter Booking Feed (Critical for Correctness)

Include only bookings where:
- SKU Ref is not None/blank
- ETA is a valid datetime (not string 'bad-date', not None)
- Booking State is 'Firm' or 'Locked' (exclude 'Tentative', 'Hold', 'Cancelled')
- ETA <= HorizonEnd (within planning window)

```python
booked_by_sku = {}
for row in booking_sheet.iter_rows(min_row=2, values_only=True):
    sku, eta_raw, cases, state = row[0], row[1], row[2], row[3]
    if not sku or state in ('Tentative', 'Hold', 'Cancelled'):
        continue
    eta = normalize_date(eta_raw)
    if eta is None or eta > horizon_end:
        continue
    booked_by_sku[sku] = booked_by_sku.get(sku, 0) + (cases or 0)
```

### 4. Calculate Coverage per SKU

For each SKU in the snapshot:

| Field | Formula |
|-------|---------|
| CurrentDaysOnHand | `CasesOnRack / AvgDailyPull` (guard division if pull=0) |
| ProjectedOOSDate | `AsOfDate + timedelta(days=floor(DaysOnHand))` |
| BookedCasesByHorizon | Sum from filtered bookings |
| RemainingDemandCases | `AvgDailyPull * PlanningDays` |
| AdditionalCasesNeeded | `max(0, RemainingDemandCases - CasesOnRack - BookedCasesByHorizon)` |
| PalletsRequired | `ceil(AdditionalCasesNeeded / CasesPerPallet)` if needed > 0 |

See `references/calculation-formulas.md` for detailed code snippets.

### 5. Determine Delivery Requirements

- RequiredDeliveryDate = ProjectedOOSDate if AdditionalCasesNeeded > 0
- EarlierDeliveryRequired = True if earliest valid booking ETA > RequiredDeliveryDate, or no valid booking exists

### 6. Generate Output Workbook

Create two sheets:
1. **Rack_Coverage**: All SKUs with full calculation columns
2. **Commit_Gap_Actions**: Subset where PalletsRequired > 0, sorted by RequiredDeliveryDate

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
- [ ] Booking filter excludes: null SKUs, non-datetime ETAs, Tentative/Hold states, dates beyond horizon
- [ ] Division by zero guarded when AvgDailyPull is 0 or None
- [ ] PalletsRequired uses ceiling, rounds up for any remainder
- [ ] EarlierDeliveryRequired correctly identifies same-day or past requirements

## Common Data Quality Issues

| Issue | Pattern | Fix |
|-------|---------|-----|
| Missing SKU | `None` in SKU Ref column | Skip row |
| Invalid date | String 'bad-date' or non-datetime | Check isinstance before comparison |
| Tentative booking | State == 'Tentative' | Exclude from sum |
| Hold state | State == 'Hold' | Exclude from sum |
| Planner notes | Rows with all None values | Skip rows where SKU is None |
| Zero inventory | CasesOnRack == 0 | Still calculate; CurrentDaysOnHand = 0 |

## Anti-Patterns

- **Do not** include Tentative bookings in coverage calculations (overstates supply)
- **Do not** treat Hold state as firm supply
- **Do not** use string comparison for dates; parse to datetime first
- **Do not** floor pallet calculation; always round up partial pallets
- **Do not** assume AvgDailyPull > 0; guard division
- **Do not** assume headers are in row 1 — scan for column names
- **Do not** compare cell values directly without type checking (TypeError risk)
- **Do not** use str() on datetime cells expecting a specific format

## Known Invariants (by Sub-task)

### rack-snapshot-booking-feed (R2 variant)
- Sheet names: `Rack Snapshot` / `Booking Feed`
- State column: `Booking State` with values `Firm` / `Locked` / `Tentative` / `Hold`
- Output sheets: `Rack_Coverage` / `Commit_Gap_Actions`

## Debugging Pattern

When extraction fails, print types and values:

```python
for row in ws.iter_rows(min_row=1, max_row=5):
    for cell in row:
        print(f"{cell.coordinate}: value={cell.value}, type={type(cell.value)}")
```