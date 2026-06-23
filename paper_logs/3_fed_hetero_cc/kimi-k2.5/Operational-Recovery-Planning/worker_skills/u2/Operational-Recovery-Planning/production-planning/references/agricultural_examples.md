# Agricultural/Harvest and Automotive Manufacturing Examples

## Domain Characteristics

Agricultural harvest planning and automotive manufacturing tasks share identical patterns:
- **Commodities/Products**: Wheat, Canola, Flax (agricultural) or Crew Cab, Extended Cab, Grill Guard (automotive)
- **Capacity units**: Bin loads, tonnes (agricultural) or Running Boards, units (automotive)
- **Equipment constraints**: Processing equipment, bins (agricultural) or production lines, assembly capacity (automotive)
- **Seasonal/Deadline windows**: Harvest periods (agricultural) or production deadlines, PO cutoffs (automotive)
- **Relocation strategies**: Moving equipment between sites (agricultural) or relocating production lines (automotive)
- **Shift extensions**: 10-hour shifts to increase throughput (both)

## Typical Scenario Structure

### Scenario 1: Current Equipment
- Operate within existing infrastructure
- Conservative production rates
- Later start dates for secondary commodities
- May result in shortfalls

### Scenario 2: Relocated Equipment
- Move processing equipment to temporary location
- Front-load production before relocation date
- Halt production on relocated commodity after move
- Free capacity for primary commodities earlier

### Scenario 3: Extended Shifts
- Implement 10-hour shifts (or other extended hours)
- Requires notification period (e.g., 30 days)
- Higher capacity on/after shift start date
- May achieve on-time for all commodities

## Example Configuration

```python
from datetime import datetime

# Manitoba holidays 2018
HOLIDAYS = {
    datetime(2018, 2, 19),  # Louis Riel Day
    datetime(2018, 3, 30),  # Good Friday
}

COLUMN_MAP = {
    'date': 2,              # B
    'wheat_prod': 3,        # C
    'wheat_po': 4,          # D
    'wheat_cumul': 5,       # E (formula)
    'canola_prod': 6,       # F
    'canola_po': 7,         # G
    'canola_cumul': 8,      # H (formula)
    'flax_prod': 9,         # I
    'total_prod': 10,       # J (formula)
    'notes': 11,            # K
}

SCENARIOS = {
    'Current Equipment and Bins': {
        'date_range': (datetime(2018, 1, 22), datetime(2018, 5, 1)),
        'canola_start': datetime(2018, 3, 1),
        'flax_total_target': 1200,
        'flax_strategy': 'even_distribution',
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 135,
        'ten_hour_shifts': False,
    },
    'Relocated Flax Processing': {
        'date_range': (datetime(2018, 1, 22), datetime(2018, 5, 1)),
        'canola_start': datetime(2018, 2, 20),
        'flax_total_target': 100,
        'flax_strategy': 'front_load_before_feb1',
        'flax_cutoff': datetime(2018, 2, 1),
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 135,
        'ten_hour_shifts': False,
    },
    '10 hr Shift Relocate Flax Proc': {
        'date_range': (datetime(2018, 1, 22), datetime(2018, 5, 1)),
        'canola_start': datetime(2018, 2, 20),
        'flax_total_target': 0,
        'flax_strategy': 'zero_entire_horizon',
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 165,  # 10-hour shift capacity
        'ten_hour_shifts': True,
        'ten_hour_start': datetime(2018, 2, 1),
        'notification_days': 30,
    }
}
```

## Production Logic Patterns

### Front-Load Strategy
```python
def get_flax_production(date_obj, scenario_config):
    """Front-load flax before cutoff date, then zero."""
    cutoff = scenario_config.get('flax_cutoff', datetime.min)
    if date_obj >= cutoff:
        return 0
    
    # Calculate even distribution before cutoff
    working_days_before = count_working_days(start_date, cutoff, holidays)
    daily_rate = scenario_config['flax_total_target'] / working_days_before
    return daily_rate
```

### Shift Day Counting
```python
def count_shift_days(start_date, end_date, shift_start, holidays):
    """Count working days on/after shift start date."""
    count = 0
    current = max(start_date, shift_start)
    while current <= end_date:
        if current.weekday() < 5 and current not in holidays:
            count += 1
        current += timedelta(days=1)
    return count
```

## On-Time Status Calculation

```python
def calculate_on_time_status(final_cumulative):
    """Negative/Zero cumulative = orders fulfilled. Positive = backlog."""
    return "Yes" if final_cumulative <= 0 else "No"
```

## Summary File Template

```markdown
# Harvest Recovery Plan Summary

**Planning Period:** January 22, 2018 -- May 1, 2018 (100 calendar days)
**Reference:** Open Harvest Orders Listing -- Wheat 5,520 total PO, Canola 4,035 total PO

---

## Scenario 1

**Sheet:** Current Equipment and Bins

**Actions:**
- Operate within existing equipment and bin infrastructure with no relocations.
- Wheat production runs at ~73 units/working day across all 70 working days.
- Canola production begins March 1, 2018 at ~84 units/working day across 43 working days.
- Flax processing runs at ~18 units/working day across all 70 working days for a total of 1,260 units.
- Weekend days and Manitoba holidays (Feb 19, Mar 30) have zero production across all commodities.

**Wheat Bin Loads Impact:**
- Total planned production: 5,100 units against 5,520 total PO demand.
- Shortfall of 420 units by May 1.
- Cumulative Open POs (EOD) on May 1: 420.

**Canola Bin Loads Impact:**
- Total planned production: 3,600 units against 4,035 total PO demand.
- Shortfall of 435 units by May 1.
- Cumulative Open POs (EOD) on May 1: 435.

**Flax Processing Impact:**
- Total output: 1,260 units across 70 working days.
- Meets minimum 1,200 unit requirement.

**May PO On-Time: No**

---

## Scenario 2

**Sheet:** Relocated Flax Processing

**Actions:**
- Relocate flax processing equipment to a temporary location.
- Flax processing runs at ~13 units/working day during the 8 working days before February 1 (total 104 units).
- Flax processing halts completely on and after February 1.
- Wheat production runs at 120 units/working day before February 5, then 72 units/working day on/after February 5.
- Canola production begins February 20, 2018 at ~72 units/working day.

**Wheat Bin Loads Impact:**
- Total planned production: 5,520 units, exactly matching total PO demand.
- Cumulative Open POs (EOD) on May 1: 0.

**Canola Bin Loads Impact:**
- Total planned production: 3,600 units against 4,035 total PO demand.
- Shortfall of 435 units by May 1.

**Flax Processing Impact:**
- Total output: 104 units before relocation.
- Meets minimum 100 unit requirement.

**May PO On-Time: No**

---

## Scenario 3

**Sheet:** 10 hr Shift Relocate Flax Proc

**Actions:**
- Implement 10-hour shifts starting February 1, 2018 (requires 30-day notification).
- Flax processing halted entirely.
- Wheat production at 120 units/working day before February 5, then 165 units/working day on/after February 1.
- Canola production begins February 20, 2018 at 85 units/working day.
- 22 shift days total.

**Wheat Bin Loads Impact:**
- Total planned production: 9,990 units against 5,520 total PO demand.
- Surplus of 4,470 units by May 1.
- Cumulative Open POs (EOD) on May 1: -4,470.

**Canola Bin Loads Impact:**
- Total planned production: 4,250 units against 4,035 total PO demand.
- Surplus of 215 units by May 1.
- Cumulative Open POs (EOD) on May 1: -215.

**May PO On-Time: Yes**
```

## Automotive Manufacturing Examples

Automotive manufacturing tasks (e.g., Running Boards, Grill Guards) follow the **same pattern** as agricultural harvest planning with different terminology:

| Agricultural Term | Automotive Term |
|-------------------|------------------|
| Wheat Bin Loads | Crew Cab Running Boards |
| Canola Bin Loads | Extended Cab Running Boards |
| Flax Processing | Grill Guard |
| Bin loads/tonnes | Running Boards/units |

### Column Header Variation (CRITICAL)

Automotive Product C (Grill Guard) may use different column headers than Products A and B:
- **Products A and B**: "Cumulative Open POs (EOD)" (standard 3-column pattern)
- **Product C (Grill Guard)**: May use "Actual Var to PO" instead of "Cumulative"

Always verify task requirements for exact header text — do not assume all products use identical headers.

### Example Automotive Configuration

```python
from datetime import date

# Same Manitoba holidays 2018
HOLIDAYS = {
    date(2018, 2, 19),  # Louis Riel Day
    date(2018, 3, 30),  # Good Friday
}

COLUMN_MAP = {
    'date': 2,              # B
    'crew_prod': 3,         # C - Crew Cab Planned Production
    'crew_po': 4,           # D - Crew Cab Purchase Orders Due
    'crew_cumul': 5,        # E - Crew Cab Cumulative (FORMULA)
    'ext_prod': 6,          # F - Extended Cab Planned Production
    'ext_po': 7,            # G - Extended Cab Purchase Orders Due
    'ext_cumul': 8,         # H - Extended Cab Cumulative (FORMULA)
    'grill_prod': 9,        # I - Grill Guard Planned Production
    'total_prod': 10,       # J - Total Production (FORMULA)
    'notes': 11,            # K
}

SCENARIOS = {
    'Current Equipment and Production': {
        'date_range': (date(2018, 1, 22), date(2018, 5, 1)),
        'extended_start': date(2018, 3, 1),
        'grill_total_target': 1200,
        'grill_strategy': 'even_distribution',
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 135,
    },
    'Relocated Grill Guard Production': {
        'date_range': (date(2018, 1, 22), date(2018, 5, 1)),
        'extended_start': date(2018, 2, 20),
        'grill_total_target': 100,
        'grill_strategy': 'front_load_before_feb1',
        'grill_cutoff': date(2018, 2, 1),
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 135,
    },
    '10 hr Shift Relocate Grill Guar': {  # Truncated to 31 chars
        'date_range': (date(2018, 1, 22), date(2018, 5, 1)),
        'extended_start': date(2018, 2, 20),
        'grill_total_target': 0,
        'grill_strategy': 'zero_entire_horizon',
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 170,  # 10-hour shift capacity
        'ten_hour_shifts': True,
        'ten_hour_start': date(2018, 2, 1),
        'notification_days': 30,
    }
}
```

**Note:** Sheet name "10 hr Shift Relocate Grill Guard" is 35 characters — truncated to "10 hr Shift Relocate Grill Guar" (31 chars). Plan accordingly.
