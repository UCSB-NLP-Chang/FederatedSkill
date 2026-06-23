---
name: stochastic-resupply-planning
description: Probabilistic inventory resupply planning with safety stock buffers. Use when tasks mention service levels (e.g., 95%), Z-scores, burn rate variance/standard deviation, safety buffers, or stochastic/probabilistic fuel/inventory planning. Covers fuel tanker calculations, safety stock with normally distributed demand, and required delivery dates with uncertainty buffers.
---

# Stochastic Resupply Planning

Calculate probabilistic resupply needs with safety stock buffers for variable demand.

## When to Use

- Fuel/energy resupply with variable burn rates
- Inventory planning with demand uncertainty
- Tasks mentioning "service level", "Z-score", "safety stock", "variance", "standard deviation"
- Need to calculate safety buffers: `Z × StdDev × √Days`

## Key Formula: Safety Buffer

```python
import numpy as np

# Safety buffer for remaining period uncertainty
# Z = service level factor (1.65 for 95%, 1.96 for 97.5%, 2.33 for 99%)
# StdDev = daily demand standard deviation
# Days = planning horizon days (or coverage days)

safety_buffer_liters = Z * daily_burn_stddev * np.sqrt(remaining_days)
```

## Core Calculations

### 1. Remaining Period Parameters

```python
from datetime import datetime

asof_date = datetime.strptime('2025-10-04', '%Y-%m-%d').date()
planning_horizon_end = datetime.strptime('2025-10-31', '%Y-%m-%d').date()
remaining_days = (planning_horizon_end - asof_date).days  # 27

remaining_burn_liters = expected_daily_burn * remaining_days
```

### 2. Days on Hand (DOH) with Variance Context

```python
current_doh = current_liters / expected_daily_burn  # float, e.g., 12.73
projected_runout = asof_date + timedelta(days=int(current_doh))
```

### 3. Safety Buffer (Stochastic Component)

```python
Z = 1.65  # 95% service level from policy parameters
safety_buffer = Z * daily_burn_stddev * np.sqrt(remaining_days)

# Alternative: buffer for coverage period instead of remaining period
# coverage_days = current_liters / expected_daily_burn
# safety_buffer = Z * daily_burn_stddev * np.sqrt(coverage_days)
```

**Zero Variance Edge Case**: When `StdDev = 0`, safety buffer = 0. This is valid.

### 4. Net Position and Additional Units

```python
# Include scheduled inbound deliveries within horizon
inbound_by_horizon = scheduled_refills[
    (scheduled_refills['Site_ID'] == site_id) &
    (scheduled_refills['Refill Date'] <= planning_horizon_end)
]
inbound_liters = inbound_by_horizon['Liters'].sum()

# Total available including inbound
total_available = current_liters + inbound_liters
delivered_doh = total_available / expected_daily_burn

# Additional needed = remaining_demand + safety_buffer - current - inbound
additional_liters = max(0, remaining_burn_liters + safety_buffer - current_liters - inbound_liters)
```

### 5. Vehicle/Tanker Rounding

```python
import numpy as np

liters_per_tanker = 1200  # from policy parameters
tankers_required = int(np.ceil(additional_liters / liters_per_tanker)) if additional_liters > 0 else 0

# Detect rounding
exact_tankers = additional_liters / liters_per_tanker
rounding_applied = (exact_tankers != tankers_required) and additional_liters > 0
```

### 6. Required Delivery Date

```python
if total_available >= (remaining_burn_liters + safety_buffer):
    # Sufficient coverage, no additional needed
    required_refill_date = None
else:
    # Calculate when current + inbound runs out
    coverage_days = int(total_available / expected_daily_burn)
    required_refill_date = asof_date + timedelta(days=coverage_days)
```

### 7. Earlier Delivery Check

```python
earliest_scheduled = inbound_by_horizon['Refill Date'].min() if len(inbound_by_horizon) > 0 else None

earlier_refill_required = False
if additional_liters > 0:
    if earliest_scheduled is None:
        earlier_refill_required = True
    elif required_refill_date is not None:
        earlier_refill_required = earliest_scheduled > required_refill_date
```

## Reading Irregular Headers with Dates in Column Names

**Pattern**: Dates stored as column headers, not cell values.

```python
# Row 0: ['', '2025-10-04', '', '2025-10-31']
# Row 1: empty
# Row 2: actual column headers
# Row 3+: data

header_rows = pd.read_excel(file, sheet_name='Current Fuel', nrows=3, header=None)
asof_date = pd.to_datetime(header_rows.iloc[0, 1]).date()  # From column header
planning_horizon_end = pd.to_datetime(header_rows.iloc[0, 3]).date()

# Read data with proper skip
df = pd.read_excel(file, sheet_name='Current Fuel', skiprows=2)
df = df.iloc[1:].reset_index(drop=True)  # Skip the header text row
```

See `references/safety-buffer-formulas.md` for detailed Z-score reference.

## Output Schema

### Primary Sheet: Site_Results

| Column | Type | Description |
|--------|------|-------------|
| Site_ID | string | Site identifier |
| Current_Liters | int | On-hand inventory |
| Expected_Daily_Burn_Liters | int | Mean daily consumption |
| Daily_Burn_StdDev | int | Demand variability |
| Current_DOH | float | Days on hand |
| Projected_Runout_Date | date | When stock depletes |
| Inbound_Liters_By_Horizon | int | Scheduled deliveries |
| Delivered_DOH_To_Horizon | float | Total DOH with inbound |
| Remaining_October_Burn_Liters | int | Total demand for period |
| Safety_Buffer_Liters | float | Z × StdDev × √Days |
| Additional_Liters_Needed | float | After current + inbound |
| Tankers_Required_Rounded_Up | int | Rounded up to vehicle capacity |
| Required_Refill_Date | date/None | Latest acceptable delivery |
| Rounding_Applied | bool | True if fractional tankers |
| Earlier_Refill_Required | bool | True if scheduled too late |
| Earliest_Scheduled_Refill_Date | date/None | First scheduled delivery |

### Secondary Sheet: Additional_Refills_Needed

Filtered to `Tankers_Required_Rounded_Up > 0`:
- Site_ID, Required_Refill_Date, Tankers_Required_Rounded_Up, Additional_Liters_Needed, Safety_Buffer_Liters, Rounding_Applied, Earlier_Refill_Required

## Anti-Patterns

- **Don't** skip the safety buffer calculation when StdDev is present in source data
- **Don't** use remaining_days directly in DOH; use it only for safety buffer √Days
- **Don't** forget to filter inbound deliveries by planning horizon AND by site
- **Don't** calculate required_refill_date when no additional units needed (None/NaT)
- **Don't** treat dates in Excel column headers as data cells

## Edge Cases

| Scenario | Handling |
|----------|----------|
| StdDev = 0 | Safety buffer = 0 (deterministic demand) |
| Zero burn rate | Skip calculations, DOH = infinite or N/A |
| Zero current + zero burn | No refills needed (no demand) |
| Inbound sufficient alone | Additional_liters = 0, required_date = None |
| No scheduled deliveries | earliest_scheduled = None, earlier_refill = True if needed |

## Validation

1. Verify Z-score matches service level in requirements (1.65 = 95%)
2. Check safety buffer uses √remaining_days, not linear days
3. Confirm inbound filtering excludes deliveries after horizon
4. Verify tanker rounding uses np.ceil, not round()
5. Check required_refill_date is None when no additional needed
6. Ensure boolean columns are native Python bool, not numpy bool_

## See Also

- `references/safety-buffer-formulas.md` - Z-score tables and safety stock theory
- `../excel-workbook-calculations/` - Base Excel writing patterns
- `../excel-workbook-calculations/references/date-handling.md` - Date extraction patterns
