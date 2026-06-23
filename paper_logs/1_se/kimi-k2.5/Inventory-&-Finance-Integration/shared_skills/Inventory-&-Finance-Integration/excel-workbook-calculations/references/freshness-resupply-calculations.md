---
name: freshness-resupply-calculations
description: Perishable inventory replenishment with expiration/spoilage considerations and minimum remaining shelf life (RSL) constraints. Use for meal kits, fresh produce, pharmaceuticals, or any inventory with limited shelf life where some current stock expires before planning horizon end.
---

# Freshness/Perishable Inventory Resupply

Perishable inventory replenishment with expiration-based unusable stock and minimum remaining shelf life (RSL) constraints.

**Use for**: Meal kit freshness planning, produce inventory, pharmaceutical stock, any perishable goods where current inventory has expiration dates within the planning horizon.

## Key Differences from Standard Parts Resupply

| Aspect | Parts/Non-Perishable | Fresh/Perishable |
|--------|---------------------|------------------|
| Current inventory usable | 100% of current_units | current_boxes - boxes_expiring_by_horizon |
| Stockout calculation | Based on total current | Based on usable current only |
| Minimum shelf life | Not applicable | Minimum_RSL_Days constraint on delivery timing |
| Expiration tracking | None | boxes_expiring_by_horizon deducted from usable |

## Data Model

### Typical Input Sheets

**Current Inventory** (irregular header with dates in row 0)
```
Row 0: [empty, AsOfDate, empty, PlanningHorizonEnd]
Row 1: [empty, empty, empty, empty]
Row 2: [Meal_Kit_ID, Current_Boxes, Daily_Order_Rate_Boxes, Boxes_Expiring_By_Horizon]
Row 3+: data rows
```

**Incoming Deliveries**
```
Meal_Kit_ID | Delivery Date | Pallets | Boxes
```

**Shelf_Life Configuration**
```
Boxes_Per_Pallet | Minimum_RSL_Days
```

## Core Calculations

### Usable Current Inventory

```python
usable_current = current_boxes - boxes_expiring_by_horizon
# Deduct inventory that will spoil before it can be used
```

### Days on Hand (DOH) and Stockout

```python
from datetime import timedelta

# Current DOH based on USABLE inventory only
current_doh = usable_current / daily_order_rate  # float, e.g., 8.57 days

# Projected out-of-stock date (when usable inventory runs out)
projected_oos_date = asof_date + timedelta(days=int(current_doh))
```

### Inbound Deliveries Within Horizon

Same filtering as parts resupply, but also check RSL constraint:

```python
# Filter deliveries within planning horizon
inbound_by_horizon = df_deliveries[
    (df_deliveries['Meal_Kit_ID'] == meal_kit_id) &
    (df_deliveries['Delivery Date'] <= planning_horizon_end)
]

inbound_boxes = inbound_by_horizon['Boxes'].sum()
earliest_scheduled = inbound_by_horizon['Delivery Date'].min() if len(inbound_by_horizon) > 0 else None
```

### Delivered DOH (Total Coverage)

```python
total_usable_available = usable_current + inbound_boxes
delivered_doh = total_usable_available / daily_order_rate
```

### Remaining Period Demand

```python
remaining_days = (planning_horizon_end - asof_date).days
remaining_demand = daily_order_rate * remaining_days
```

### Additional Units Needed

```python
additional_boxes = max(0, remaining_demand - usable_current - inbound_boxes)
```

### Pallet-Based Rounding

```python
import numpy as np

pallets_required = int(np.ceil(additional_boxes / boxes_per_pallet)) if additional_boxes > 0 else 0

# Detect if rounding was applied
exact_pallets = additional_boxes / boxes_per_pallet if additional_boxes > 0 else 0
rounding_applied = (exact_pallets != pallets_required) and additional_boxes > 0
```

### Required Delivery Date Logic

The required delivery date depends on whether inbound deliveries prevent stockout:

```python
if delivered_doh >= remaining_days:
    # Sufficient coverage with inbound, calculate based on delivered DOH
    required_delivery_date = planning_horizon_end - timedelta(days=int(delivered_doh - remaining_days))
else:
    # Still insufficient even with inbound
    required_delivery_date = projected_oos_date
```

**Alternative simplified approach** (used in trace):
```python
if usable_current + inbound_boxes >= remaining_demand:
    # Covers full period, no additional needed
    required_delivery_date = None
else:
    # Calculate when usable + inbound runs out
    delivered_coverage_days = int((usable_current + inbound_boxes) / daily_order_rate)
    required_delivery_date = asof_date + timedelta(days=delivered_coverage_days)
```

### Earlier Delivery Required

```python
earlier_delivery_required = False
if additional_boxes > 0:
    if earliest_scheduled is None:
        earlier_delivery_required = True
    elif required_delivery_date is not None:
        earlier_delivery_required = earliest_scheduled > required_delivery_date
```

## Multi-Item Processing Pattern

```python
results = []
for _, row in df_inventory.iterrows():
    meal_kit_id = row['Meal_Kit_ID']
    current_boxes = row['Current_Boxes']
    daily_rate = row['Daily_Order_Rate_Boxes']
    expiring_by_horizon = row['Boxes_Expiring_By_Nov30']
    
    # Skip header-like rows
    if meal_kit_id == 'Meal_Kit_ID' or pd.isna(meal_kit_id):
        continue
    
    # Calculate usable inventory
    usable_current = current_boxes - expiring_by_horizon
    
    # DOH and stockout based on USABLE only
    current_doh = usable_current / daily_rate if daily_rate > 0 else float('inf')
    projected_oos = asof_date + timedelta(days=int(current_doh)) if daily_rate > 0 else None
    
    # Filter inbound for this item within horizon
    kit_deliveries = df_deliveries[df_deliveries['Meal_Kit_ID'] == meal_kit_id]
    inbound_by_horizon = kit_deliveries[kit_deliveries['Delivery Date'] <= planning_horizon_end]
    inbound_boxes = inbound_by_horizon['Boxes'].sum() if len(inbound_by_horizon) > 0 else 0
    earliest_scheduled = inbound_by_horizon['Delivery Date'].min() if len(inbound_by_horizon) > 0 else None
    
    # Demand and resupply calculations
    remaining_demand = daily_rate * remaining_days
    additional_boxes = max(0, remaining_demand - usable_current - inbound_boxes)
    pallets_required = int(np.ceil(additional_boxes / boxes_per_pallet)) if additional_boxes > 0 else 0
    
    # Delivery timing analysis
    total_usable = usable_current + inbound_boxes
    if total_usable >= remaining_demand:
        required_delivery = None  # No additional needed
    else:
        coverage_days = int(total_usable / daily_rate)
        required_delivery = asof_date + timedelta(days=coverage_days)
    
    earlier_required = False
    if additional_boxes > 0:
        if earliest_scheduled is None:
            earlier_required = True
        elif required_delivery is not None:
            earlier_required = earliest_scheduled > required_delivery
    
    results.append({
        'Meal_Kit_ID': meal_kit_id,
        'Current_Boxes': current_boxes,
        'Boxes_Expiring_By_Horizon': expiring_by_horizon,
        'Usable_Current_Boxes': usable_current,
        'Daily_Order_Rate_Boxes': daily_rate,
        'Current_DOH': current_doh,
        'Projected_OOS_Date': projected_oos,
        'Inbound_Boxes_By_Horizon': inbound_boxes,
        'Delivered_DOH_To_Horizon': (usable_current + inbound_boxes) / daily_rate if daily_rate > 0 else 0,
        'Remaining_Demand_Boxes': remaining_demand,
        'Additional_Boxes_Needed': additional_boxes,
        'Pallets_Required_Rounded_Up': pallets_required,
        'Required_Delivery_Date': required_delivery,
        'Rounding_Applied': rounding_applied,
        'Earlier_Delivery_Required': earlier_required,
        'Earliest_Scheduled_Inbound_Date': earliest_scheduled,
    })

df_results = pd.DataFrame(results)
```

## Secondary Sheet: Additional Freshness Needed

Filter to items requiring replenishment:

```python
df_resupply = df_results[df_results['Pallets_Required_Rounded_Up'] > 0][[
    'Meal_Kit_ID',
    'Required_Delivery_Date',
    'Pallets_Required_Rounded_Up',
    'Additional_Boxes_Needed',
    'Rounding_Applied',
    'Earlier_Delivery_Required'
]]
```

## Output Schema

### Freshness_Results Sheet

| Column | Type | Description |
|--------|------|-------------|
| Meal_Kit_ID | string | Identifier |
| Current_Boxes | int | Total on-hand (including expiring) |
| Boxes_Expiring_By_Horizon | int | Unusable due to expiration |
| Usable_Current_Boxes | int | Current_Boxes - expiring |
| Daily_Order_Rate_Boxes | int | Daily consumption rate |
| Current_DOH | float | Days of hand based on usable only |
| Projected_OOS_Date | date | When usable inventory runs out |
| Inbound_Boxes_By_Horizon | int | Scheduled deliveries within period |
| Delivered_DOH_To_Horizon | float | Total DOH including inbound |
| Remaining_Demand_Boxes | int | Total demand for remaining days |
| Additional_Boxes_Needed | int | Boxes required after current + inbound |
| Pallets_Required_Rounded_Up | int | Pallets to order (rounded up) |
| Required_Delivery_Date | date or None | Latest acceptable delivery |
| Rounding_Applied | bool | True if fractional pallets existed |
| Earlier_Delivery_Required | bool | True if scheduled delivery too late |
| Earliest_Scheduled_Inbound_Date | date or None | First scheduled delivery |

### Additional_Freshness_Needed Sheet

Filtered to `Pallets_Required_Rounded_Up > 0`:
- Meal_Kit_ID
- Required_Delivery_Date
- Pallets_Required_Rounded_Up
- Additional_Boxes_Needed
- Rounding_Applied
- Earlier_Delivery_Required

## Critical Anti-Patterns

- **Don't** use total current_boxes for DOH/stockout calculations—only usable_current
- **Don't** forget to filter inbound deliveries by horizon AND by item ID
- **Don't** calculate required_delivery_date when no additional units needed (set to None/NaT)
- **Don't** treat earliest_scheduled as valid when inbound_by_horizon is empty (check len() first)
- **Don't** write dates as pandas Timestamps without conversion—use .date() or isoformat()

## Edge Cases

### All Inventory Expiring Before Horizon

```python
if usable_current <= 0:
    current_doh = 0
    projected_oos = asof_date  # Already out of usable stock
```

### No Scheduled Deliveries and Additional Needed

```python
if additional_boxes > 0 and earliest_scheduled is None:
    earlier_delivery_required = True  # Must schedule new delivery
```

### Inbound Sufficient Without Additional Order

```python
if usable_current + inbound_boxes >= remaining_demand:
    additional_boxes = 0
    pallets_required = 0
    required_delivery_date = None  # Or calculate for completeness
```

## See Also

- `parts-resupply-calculations.md` - Non-perishable inventory pattern (no expiration deduction)
- `../scripts/pallet_calculations.py` - Reusable pallet rounding logic
