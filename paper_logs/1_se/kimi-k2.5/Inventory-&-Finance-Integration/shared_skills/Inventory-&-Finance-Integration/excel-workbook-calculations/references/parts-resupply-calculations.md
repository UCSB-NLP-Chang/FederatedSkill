# Parts and Inventory Resupply Calculations

Formulas for maintenance parts, inventory stockout projections, and resupply planning with crate-based rounding.

## Data Model

### Typical Input Sheets

**Current Parts** (irregular header: dates in row 0)
```
Row 0: [empty, AsOfDate, empty, PlanningHorizonEnd]
Row 1: [empty, empty, empty, empty]
Row 2: [Part_Code, Current_Units, Daily_Consumption_Units, empty]
Row 3+: data rows
```

**Scheduled Deliveries**
```
Part_Code | Delivery Date | Crates | Units
```

**Ratio/Conversion**
```
Units_Per_Crate: 55
```

## Core Calculations

### Days on Hand (DOH)

```python
current_doh = current_units / daily_consumption  # float, e.g., 18.64 days
```

### Projected Stockout Date

```python
from datetime import timedelta

projected_stockout_date = asof_date + timedelta(days=int(current_doh))
# Use int() truncation (floor) for conservative estimate
```

### Filter Inbound Deliveries Within Horizon

```python
# Critical: Only count deliveries that arrive ON or BEFORE planning_horizon_end
inbound_mask = (
    (df_deliveries['Part_Code'] == part_code) &
    (df_deliveries['Delivery Date'] <= planning_horizon_end)
)
inbound_deliveries = df_deliveries[inbound_mask]

inbound_units = inbound_deliveries['Units'].sum() if len(inbound_deliveries) > 0 else 0
earliest_scheduled = inbound_deliveries['Delivery Date'].min() if len(inbound_deliveries) > 0 else None
# Note: earliest_scheduled may be None if no deliveries scheduled
```

### Remaining Period Demand

```python
remaining_days = (planning_horizon_end - asof_date).days
remaining_demand_units = daily_consumption * remaining_days
```

### Delivered DOH (Total Coverage with Inbound)

```python
total_units_available = current_units + inbound_units
delivered_doh = total_units_available / daily_consumption
```

### Additional Units Needed

```python
additional_units = max(0, remaining_demand_units - current_units - inbound_units)
```

### Crate-Based Rounding

```python
import numpy as np

crates_required = int(np.ceil(additional_units / units_per_crate))
# 0 if no additional units needed

# Flag if rounding actually occurred (fractional crates existed)
exact_crates = additional_units / units_per_crate
rounding_applied = (
    (exact_crates != crates_required) and additional_units > 0
)
```

### Required Delivery Date

```python
# When stock runs out without resupply
required_delivery_date = projected_stockout_date
```

### Earlier Delivery Required Check

```python
# True if earliest scheduled delivery is AFTER stock runs out
# OR if no deliveries are scheduled (earliest_scheduled is None) and resupply needed
earlier_delivery_required = False
if additional_units > 0:
    if earliest_scheduled is None:
        earlier_delivery_required = True
    elif required_delivery_date is not None:
        earlier_delivery_required = earliest_scheduled > required_delivery_date
```

## Multi-Part Processing Pattern

```python
results = []
for _, part_row in df_parts.iterrows():
    part_code = part_row['Part_Code']
    current_units = part_row['Current_Units']
    daily_consumption = part_row['Daily_Consumption_Units']
    
    # Skip header-like rows
    if part_code == 'Part_Code' or pd.isna(part_code):
        continue
    
    # Calculate DOH and stockout
    current_doh = current_units / daily_consumption
    projected_stockout = asof_date + timedelta(days=int(current_doh))
    
    # Filter inbound for this part within horizon
    part_deliveries = df_deliveries[df_deliveries['Part_Code'] == part_code]
    inbound_by_horizon = part_deliveries[part_deliveries['Delivery Date'] <= planning_horizon_end]
    inbound_units = inbound_by_horizon['Units'].sum() if len(inbound_by_horizon) > 0 else 0
    earliest_scheduled = inbound_by_horizon['Delivery Date'].min() if len(inbound_by_horizon) > 0 else None
    
    # Demand and resupply calculations
    remaining_demand = daily_consumption * remaining_days
    additional_units = max(0, remaining_demand - current_units - inbound_units)
    crates_required = int(np.ceil(additional_units / units_per_crate)) if additional_units > 0 else 0
    
    # Delivery timing
    required_delivery = projected_stockout if additional_units > 0 else None
    earlier_required = False
    if additional_units > 0:
        if earliest_scheduled is None:
            earlier_required = True
        elif required_delivery is not None:
            earlier_required = earliest_scheduled > required_delivery
    
    results.append({
        'Part_Code': part_code,
        'Current_Units': current_units,
        'Daily_Consumption_Units': daily_consumption,
        'Current_DOH': current_doh,
        'Projected_Stockout_Date': projected_stockout,
        'Inbound_Units_By_Horizon': inbound_units,
        'Delivered_DOH_To_Horizon': (current_units + inbound_units) / daily_consumption,
        'Remaining_Demand_Units': remaining_demand,
        'Additional_Units_Needed': additional_units,
        'Crates_Required_Rounded_Up': crates_required,
        'Required_Delivery_Date': required_delivery,
        'Rounding_Applied': rounding_applied,
        'Earlier_Delivery_Required': earlier_required,
        'Earliest_Scheduled_Delivery_Date': earliest_scheduled,
    })

df_results = pd.DataFrame(results)
```

## Secondary Sheet: Additional Resupply Needed

Filter to only parts requiring resupply:

```python
df_resupply = df_results[df_results['Crates_Required_Rounded_Up'] > 0][[
    'Part_Code',
    'Required_Delivery_Date',
    'Crates_Required_Rounded_Up',
    'Additional_Units_Needed',
    'Rounding_Applied',
    'Earlier_Delivery_Required'
]]
```

## Edge Cases

### Zero Daily Consumption

```python
if daily_consumption == 0:
    current_doh = float('inf')
    projected_stockout = None
    remaining_demand = 0
    additional_units = 0
```

### No Scheduled Deliveries

```python
if len(part_deliveries) == 0:
    inbound_units = 0
    earliest_scheduled = None
    # earlier_delivery_required = True if additional_units > 0
```

### Delivery After Planning Horizon

```python
# Exclude deliveries on 2025-10-01 when horizon ends 2025-09-30
deliveries_in_horizon = part_deliveries[part_deliveries['Delivery Date'] <= planning_horizon_end]
# Use <= for inclusive, < for strict
```

## Output Schema

### Part_Results Sheet

| Column | Type | Description |
|--------|------|-------------|
| Part_Code | string | Identifier |
| Current_Units | int | On-hand inventory |
| Daily_Consumption_Units | int | Daily usage rate |
| Current_DOH | float | Days of hand at current consumption |
| Projected_Stockout_Date | date | When inventory runs out |
| Inbound_Units_By_Horizon | int | Scheduled deliveries within planning period |
| Delivered_DOH_To_Horizon | float | Total DOH including inbound |
| Remaining_Demand_Units | int | Total demand for remaining days |
| Additional_Units_Needed | int | Units required after current + inbound |
| Crates_Required_Rounded_Up | int | Crates to order (rounded up) |
| Required_Delivery_Date | date | Latest acceptable delivery date |
| Rounding_Applied | bool | True if fractional crates existed |
| Earlier_Delivery_Required | bool | True if scheduled delivery is too late |
| Earliest_Scheduled_Delivery_Date | date or None | First scheduled delivery for part |

### Additional_Resupply_Needed Sheet

Filtered to `Crates_Required_Rounded_Up > 0`:
- Part_Code
- Required_Delivery_Date
- Crates_Required_Rounded_Up
- Additional_Units_Needed
- Rounding_Applied
- Earlier_Delivery_Required
