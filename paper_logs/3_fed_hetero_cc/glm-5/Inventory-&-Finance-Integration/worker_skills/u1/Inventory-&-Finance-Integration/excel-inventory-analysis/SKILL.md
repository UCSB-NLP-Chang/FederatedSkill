---
name: excel-inventory-analysis
description: Analyze resource planning data from Excel workbooks including inventory, shipments, staffing, or any supply-demand scenario. Calculate coverage gaps, project shortfall dates, and generate procurement/shift plans. Use when tasks involve reading multi-sheet Excel files with current stock/staffing, scheduled deliveries/shifts, and conversion ratios, then computing days of coverage, out-of-stock/understaff dates, and additional requirements. Also handles freshness/expiry scenarios where inventory has a shelf-life constraint, and stochastic demand scenarios with demand uncertainty requiring safety buffers.
---

# Excel Resource Planning & Gap Analysis

## CRITICAL ANTI-PATTERN

**Tool names must be EXACTLY matched. Never add leading/trailing spaces:**
- CORRECT: `Bash`
- WRONG: `' Bash'` (leading space) — this causes immediate tool rejection
- WRONG: `'Bash '` (trailing space)
- WRONG: `' Bash '` (both)

The harness rejects tool calls with mismatched names. Always verify your tool invocations use exact names.

## Domain Coverage

This skill handles resource planning analysis across domains:
- **Inventory/Supply**: Cases, pallets, SKUs, shipments
- **Staffing/Workforce**: Hours, shift blocks, care units, schedules
- **Maintenance/Parts**: Units, crates, components, deliveries
- **Perishable/Freshness**: Meal kits, fresh produce, time-limited inventory with expiry dates
- **Fuel/Energy**: Liters, gallons, tanker deliveries, burn rates
- **Stochastic Demand**: Scenarios with demand uncertainty (mean ± std dev) requiring safety buffers
- **General Pattern**: Current resources + scheduled inbound - demand rate = gap analysis

## Terminology Variants

Different domains use equivalent terms:
- **Days of Coverage (DOC)** = **Days of Hand (DOH)** = **Days of Supply**
- **Stockout Date** = **Shortfall Date** = **Run-Out Date**
- **Units** = **Parts** = **Items** = **Boxes** = **Liters**
- **Crates** = **Pallets** = **Cases** = **Shift Blocks** = **Tankers**

All calculation logic is identical regardless of terminology.

## Environment Setup

### Venv-first pattern (recommended)
Modern Debian/Ubuntu systems reject direct `pip install` with PEP 668 errors:
```bash
python3 -m venv /tmp/venv
/tmp/venv/bin/pip install openpyxl -q
```

Run all Python through the venv:
```bash
/tmp/venv/bin/python3 << 'PYEOF'
# your code here
PYEOF
```

### Alternative: break-system-packages
For isolated agent runs where venv is unnecessary:
```bash
pip install openpyxl -q --break-system-packages
```

### Library preference
Prefer `openpyxl` over `pandas` for this domain. It preserves cell types, formulas, and allows precise row/column placement required by verifiers.

## Data Extraction Workflow

1. **Load Workbook**: `wb = openpyxl.load_workbook(path, data_only=False)`
2. **Identify Sheets**: Inspect `wb.sheetnames`. Typical layouts:
   - Inventory: `Current Inventory`, `Incoming Shipments`, `Ratio`
   - Staffing: `Current Staffing`, `Incoming Shifts`, `Ratio`
   - Maintenance: `Current Parts`, `Scheduled Deliveries`, `Ratio`
   - Freshness: `Current Inventory`, `Incoming Deliveries`, `Shelf_Life`
   - Fuel/Stochastic: `Current Fuel`, `Scheduled Refills`, `Policy Parameters`
3. **Extract Metadata from Header Rows**: Dates often appear in row 1-2 (e.g., AsOfDate in B1, PlanningHorizonEnd in D1). Don't assume data starts at row 1.
4. **Normalize Dates**: Excel cells mix `datetime` objects and ISO strings (`YYYY-MM-DD`). **CRITICAL**: Never assume date cells are datetime objects. They may be strings. Always check both types:
   ```python
   if isinstance(val, datetime):
       return val.date()
   elif isinstance(val, str):
       return datetime.strptime(val, '%Y-%m-%d').date()
   ```
   Use `scripts/setup_and_load.py` or inline parsing to convert all to `date` objects before arithmetic.
5. **Handle Formulas**: Cells like `=80*C2` or `=24*A2` are read as strings. Extract multipliers programmatically. Do not assume `data_only=True` will return evaluated numbers unless the source file was saved post-calculation.
6. **Zero-Rate Handling**: If `Daily_Rate == 0`, skip gap calculations. Output None for coverage fields to avoid division-by-zero errors.
7. **Skip Header Rows**: Data often starts after metadata rows. Verify the first data row contains actual data, not headers:
   ```python
   # Check if first row contains strings like 'Meal_Kit_ID' (header)
   first_cell = str(ws.cell(row=1, column=1).value or '')
   if first_cell in ['Meal_Kit_ID', 'SKU', 'Item_ID', 'Site_ID']:
       data_start_row = 2  # Skip header row
   ```

## Stochastic Demand Analysis (Safety Buffer Pattern)

When demand has uncertainty (mean ± standard deviation), apply safety buffer calculations:

### Key Concept: Safety Stock
**Safety Buffer = Z × σ_demand × √(days_in_horizon)**

Where:
- Z = Service level factor (e.g., 1.65 for 95% service level)
- σ_demand = Daily demand standard deviation
- days_in_horizon = Remaining days in planning period

### Stochastic Calculation Workflow

1. **Extract parameters**: Look for columns like `Expected_Daily_Burn_Liters`, `Daily_Burn_StdDev` and policy parameters like `Service_Level_Z`, `Liters_Per_Tanker`
2. **Calculate safety buffer**: `Safety_Buffer = Z * StdDev * sqrt(Remaining_Days)`
3. **Compute total demand with safety**: `Total_Demand_With_Safety = (Mean_Daily_Rate * Remaining_Days) + Safety_Buffer`
4. **Calculate gap**: `Additional_Needed = max(0, Total_Demand_With_Safety - Current_Units - Inbound_Units)`
5. **Round up to order units**: `Order_Units = ceil(Additional_Needed / Units_Per_Order)`
6. **Flag rounding**: `Rounding_Applied = (Additional_Needed % Units_Per_Order) != 0`
7. **Check earlier delivery needed**: Compare `Required_Delivery_Date` against `Earliest_Scheduled_Delivery_Date`

### Stochastic Output Columns

| Column | Description | Formula |
|--------|-------------|----------|
| Current_Units | Current inventory | From source |
| Mean_Daily_Rate | Expected daily consumption | From source |
| Daily_Rate_StdDev | Demand uncertainty | From source |
| Current_DOH | Days of coverage at mean rate | Current / Mean_Rate |
| Projected_Runout_Date | When stock runs out at mean rate | AsOf + DOH days |
| Inbound_Units_By_Horizon | Scheduled deliveries in window | Sum where date <= horizon |
| Delivered_DOH | Total coverage including inbound | (Current + Inbound) / Mean_Rate |
| Remaining_Demand | Mean demand in horizon | Mean_Rate * Remaining_Days |
| Safety_Buffer_Units | Safety stock for service level | Z * StdDev * sqrt(Days) |
| Additional_Units_Needed | Gap including safety | max(0, Demand + Safety - Current - Inbound) |
| Order_Units_Required | Whole orders needed | ceil(Additional / Units_Per_Order) |
| Required_Delivery_Date | When new stock must arrive | AsOf + (Additional / Mean_Rate) days |
| Rounding_Applied | Whether order rounding occurred | Additional % Order_Size != 0 |
| Earlier_Delivery_Required | New delivery before scheduled | Required_Date < Earliest_Scheduled |

### Edge Case: Zero Demand Uncertainty
If `StdDev == 0`, safety buffer = 0. This reduces to deterministic gap analysis.

### Edge Case: Zero Current Inventory
If `Current_Units == 0` and `Mean_Rate > 0`:
- Current_DOH = 0
- Projected_Runout_Date = AsOfDate (immediate shortage)
- All demand must be met by inbound or new orders

## Freshness/Expiry-Aware Inventory Analysis

When inventory has a shelf-life or expiry constraint, apply this pattern:

### Key Concept: Usable Inventory
**Usable inventory = Current inventory - Units expiring within planning horizon**

This is critical for perishable goods (meal kits, fresh produce, pharmaceuticals) where some current stock will become unusable before the planning period ends.

### Freshness Calculation Workflow

1. **Extract expiry data**: Look for columns like `Boxes_Expiring_By_Nov30` or `Units_Expiring_By_Horizon_End`
2. **Calculate usable current units**: `Usable_Current = Current_Boxes - Boxes_Expiring_By_Horizon_End`
3. **Compute coverage on usable units**: `Current_DOH = Usable_Current / Daily_Order_Rate`
4. **Project out-of-stock date**: `Projected_OOS_Date = AsOfDate + timedelta(days=Current_DOH)`
5. **Sum inbound within horizon**: Only count deliveries with date <= PlanningHorizonEnd
6. **Calculate delivered DOH**: `(Usable_Current + Inbound_Within_Horizon) / Daily_Order_Rate`
7. **Compute additional units needed**: `max(0, Remaining_Demand - (Usable_Current + Inbound_Within_Horizon))`

### Freshness Output Columns

| Column | Description | Formula |
|--------|-------------|----------|
| Current_Boxes | Total current inventory | From source |
| Boxes_Expiring_By_Horizon | Units that will expire | From source |
| Usable_Current_Boxes | Non-expiring inventory | Current - Expiring |
| Current_DOH | Days of coverage from usable | Usable_Current / Daily_Rate |
| Projected_OOS_Date | When usable stock runs out | AsOf + DOH days |
| Inbound_Boxes_By_Horizon | Scheduled deliveries in window | Sum where date <= horizon |
| Delivered_DOH | Total coverage including inbound | (Usable + Inbound) / Rate |
| Remaining_Demand | Total demand in horizon | Daily_Rate * Remaining_Days |
| Additional_Boxes_Needed | Gap to fill | max(0, Demand - Usable - Inbound) |
| Pallets_Required_Rounded_Up | Whole pallets needed | ceil(Boxes / Boxes_Per_Pallet) |
| Required_Delivery_Date | When new stock must arrive | AsOf + (Additional / Rate) days |
| Rounding_Applied | Whether pallet rounding occurred | Additional % Pallet_Size != 0 |
| Earlier_Delivery_Required | New delivery before scheduled | Required_Date < Earliest_Scheduled |

### Edge Case: Zero Usable Inventory
If all current inventory expires (Usable_Current = 0):
- Current_DOH = 0
- Projected_OOS_Date = AsOfDate (immediate shortage)
- All demand must be met by inbound or new orders

## Calculation Logic

### Domain-Agnostic Mapping

| Generic | Inventory Domain | Staffing Domain | Maintenance Domain | Freshness Domain | Fuel/Stochastic Domain |
|---------|------------------|-----------------|--------------------|-----------------|----------------------|
| Current_Units | Current_Cases | Current_Staff_Hours | Current_Units | Current_Boxes | Current_Liters |
| Daily_Rate | Daily_Case_Rate | Daily_Required_Hours | Daily_Consumption_Units | Daily_Order_Rate | Expected_Daily_Burn |
| Rate_StdDev | (rarely used) | (rarely used) | (rarely used) | (rarely used) | Daily_Burn_StdDev |
| Inbound_Units | Inbound_Cases | Incoming_Hours | Inbound_Units | Inbound_Boxes | Inbound_Liters |
| Unit_Multiplier | Cases_Per_Pallet | Hours_Per_Shift_Block | Units_Per_Crate | Boxes_Per_Pallet | Liters_Per_Tanker |
| Output_Units | Pallets | Shift_Blocks | Crates | Pallets | Tankers |

### Core Formulas
- **Coverage / Days on Hand**: `Current_Units / Daily_Rate` (None if Daily_Rate == 0)
- **Projected Shortfall Date**: `AsOfDate + timedelta(days=Coverage)`
- **Inbound Within Horizon**: Sum units where delivery/shift date `<= PlanningHorizonEnd`
- **Remaining Demand**: `Daily_Rate * Remaining_Days_In_Horizon`
- **Safety Buffer (Stochastic)**: `Z * StdDev * sqrt(Remaining_Days)`
- **Additional Units Needed**: `max(0, Remaining_Demand + Safety_Buffer - Current_Units - Inbound_Units)`
- **Output Units Required**: `math.ceil(Additional_Units_Needed / Unit_Multiplier)`
- **Required Delivery/Shift Date**: `AsOfDate + timedelta(days=Additional_Units_Needed / Daily_Rate)`
- **Earlier Delivery Required**: `True` if `Required_Date < Earliest_Scheduled_Inbound_Date`
- **Rounding Flag**: `True` if `Additional_Needed / Unit_Multiplier` is not an integer.

## Output Generation

Create a new workbook with two sheets:
1. **Detail Sheet** (e.g., `SKU_Results`, `Unit_Results`, `Part_Results`, `Freshness_Results`, `Site_Results`): Metadata + all rows with calculated fields
2. **Summary Sheet** (e.g., `Additional_Shipments_Needed`, `Additional_Shifts_Needed`, `Additional_Refills_Needed`): Only rows where units required > 0

**Structure:**
- Metadata in `A1:B4` (AsOfDate, PlanningHorizonEnd, RemainingDays)
- Detail headers at row 6, summary headers at row 1
- Format all dates as `YYYY-MM-DD` strings to avoid Excel serialization quirks
- **Type Safety**: Dates as strings. Booleans as native `True`/`False`. Numbers as `int`/`float`.
- Write Python booleans (`True`/`False`) directly—they become Excel booleans

**Verification Step**: Immediately reload the saved workbook. Print sheet names, headers, and row counts. Assert expected structure and cell types before finishing.

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Anti-Patterns & Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `TypeError: unsupported operand type(s) for -: 'str' and 'str'` | Date cells are strings, not datetime | Check `isinstance(val, str)` and parse with `strptime` |
| `AttributeError: type object 'date' has no attribute 'timedelta'` | Used `date.timedelta` instead of `datetime.timedelta` | Import `timedelta` directly or use `datetime.timedelta` |
| `ValueError: day is out of range for month` | Used `date.replace(day=old_day + n)` for date arithmetic | **Always use `timedelta`**: `as_of_date + timedelta(days=n)` |
| Formula cells show as strings like `=24*C2` | `data_only=False` reads formulas raw | Parse multipliers manually or compute in Python |
| Boolean fields rejected by verifier | Wrote string `"True"` instead of Python `True` | Pass raw bool values to `ws.cell()` |
| Division by zero | Daily_Rate or Daily_Required_Hours is 0 | Check rate > 0 before computing coverage |
| Horizon boundary mismatch | Used `<` instead of `<=` for horizon end | Use `<=` for planning horizon end dates |
| Date arithmetic with partial days | `timedelta` floors partial days differently | Use `math.floor()` for date offsets when needed |
| Silent output failures | Types mismatch downstream | Always verify by reading back saved workbook |
| Tool call rejected | Leading/trailing space in tool name | Use exact `Bash`, not `' Bash'` |
| Negative usable inventory | Expiring > Current | Clamp to 0: `max(0, Current - Expiring)` |
| Inbound after horizon counted | Used `<` instead of `<=` | Filter: `item['date'] <= horizon_end` |
| Header row in data | Didn't skip metadata rows | Check if row 0 contains column names, skip if so |
| `ValueError: could not convert string to float` | Header strings in numeric columns | Skip header row before numeric conversion |
| Safety buffer too small | Forgot sqrt(days) factor | Safety = Z * σ * √(days), not Z * σ * days |

## Edge Cases

- **Zero daily rate**: Coverage days = None, shortfall date = None, all additional needs = 0
- **Zero current units**: Coverage days = 0, shortfall date = AsOfDate
- **All inventory expiring**: Usable = 0, DOH = 0, immediate shortage
- **Zero demand uncertainty**: Safety buffer = 0, reduces to deterministic analysis
- **Inbound after horizon**: Exclude from calculations, but track for `Earliest_Scheduled_*_Date`
- **No inbound scheduled**: `Earliest_Scheduled_*_Date` = None

## Helper Script

Import or run `scripts/setup_and_load.py` to safely install `openpyxl`, normalize mixed dates (handles both datetime and string formats), extract formula multipliers, and calculate coverage gaps without boilerplate.
