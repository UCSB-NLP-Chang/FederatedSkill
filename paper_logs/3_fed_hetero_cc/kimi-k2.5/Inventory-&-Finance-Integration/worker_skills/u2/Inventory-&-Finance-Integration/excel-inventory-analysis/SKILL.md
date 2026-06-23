---
name: excel-inventory-analysis
description: Analyze resource planning data from Excel workbooks including inventory, shipments, staffing, fuel/energy refills, or any supply-demand scenario. Calculate coverage gaps, project shortfall dates, and generate procurement/shift plans. Use when tasks involve reading multi-sheet Excel files with current stock/staffing, scheduled deliveries/shifts/refills, and conversion ratios, then computing days of coverage, out-of-stock/understaff dates, and additional requirements. Covers freshness/perishables scenarios with expiring inventory adjustments and stochastic/probabilistic scenarios with safety buffer calculations.
---

# Excel Resource Planning & Gap Analysis

## CRITICAL ANTI-PATTERN (kimi-k2.5)

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
- **Freshness/Perishables**: Meal kits, food boxes, items with expiration dates
- **Fuel/Energy**: Liters, tankers, refills, burn rates with stochastic demand
- **General Pattern**: Current resources + scheduled inbound - demand rate = gap analysis

## Terminology Variants

Different domains use equivalent terms:
- **Days of Coverage (DOC)** = **Days on Hand (DOH)** = **Days of Supply** = **Days Until Stockout**
- **Stockout Date** = **Shortfall Date** = **Run-Out Date** = **Out-of-Stock Date**
- **Units** = **Parts** = **Items** = **Boxes** = **Cases** = **Liters**
- **Crates** = **Pallets** = **Cases** = **Shift Blocks** = **Tankers**
- **Usable Current** = **Current - Expiring** (freshness domain)
- **Minimum RSL** = **Remaining Shelf Life** threshold (freshness domain)
- **Safety Buffer** = **Z * σ * √T** (stochastic demand, service level protection)

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
   - Fuel/Refills: `Current_Fuel_Levels`, `Scheduled_Refills`, `Policy_Parameters`
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
6. **Handle Policy Parameters**: Stochastic scenarios often have separate parameter sheets (e.g., `Liters_Per_Tanker`, `Service_Level_Z`). Extract these as scalars, not dataframes. Common pattern: row 0=headers, row 1=values with `header=None` and `iloc[1]` access.
7. **Zero-Rate Handling**: If `Daily_Rate == 0`, skip gap calculations. Output None for coverage fields to avoid division-by-zero errors.
8. **Skip Header Rows**: Data often starts after metadata rows. Verify row 0 is headers, not data:
   ```python
   # Check if first row contains strings like 'Meal_Kit_ID'
   if str(df.iloc[0, 0]) == 'Meal_Kit_ID':
       df = df.iloc[1:].reset_index(drop=True)
   ```

## Calculation Logic

### Domain-Agnostic Mapping

| Generic | Inventory | Staffing | Maintenance | Freshness | Fuel/Refills |
|---------|-----------|----------|-------------|-----------|--------------|
| Current_Units | Current_Cases | Current_Staff_Hours | Current_Units | Current_Boxes | Current_Liters |
| Usable_Units | (same) | (same) | (same) | Current - Expiring | (same) |
| Daily_Rate | Daily_Case_Rate | Daily_Required_Hours | Daily_Consumption_Units | Daily_Order_Rate_Boxes | Expected_Daily_Burn_Liters |
| Daily_StdDev | (unused) | (unused) | (unused) | (unused) | Daily_Burn_StdDev |
| Inbound_Units | Inbound_Cases | Incoming_Hours | Inbound_Units | Inbound_Boxes | Inbound_Liters |
| Unit_Multiplier | Cases_Per_Pallet | Hours_Per_Shift_Block | Units_Per_Crate | Boxes_Per_Pallet | Liters_Per_Tanker |
| Safety_Buffer | (unused) | (unused) | (unused) | (unused) | Z * σ * √T |
| Output_Units | Pallets | Shift_Blocks | Crates | Pallets | Tankers |

### Core Formulas
- **Usable Current** (freshness): `Current_Units - Boxes_Expiring_By_Horizon`
- **Coverage / Days on Hand (DOC/DOH)**: `Usable_Current_Units / Daily_Rate` (None if Daily_Rate == 0)
- **Projected Shortfall Date**: `AsOfDate + timedelta(days=Coverage)`
- **Inbound Within Horizon**: Sum units where delivery/shift/refill date `<= PlanningHorizonEnd`
- **Remaining Demand**: `Daily_Rate * Remaining_Days_In_Horizon`
- **Safety Buffer** (stochastic): `Service_Level_Z * Daily_Burn_StdDev * sqrt(Remaining_Days)`
- **Total Need**: `Remaining_Demand + Safety_Buffer - (Current_Units + Inbound_Units)`
- **Additional Units Needed**: `max(0, Total_Need)`
- **Output Units Required**: `math.ceil(Additional_Units_Needed / Unit_Multiplier)`
- **Required Delivery/Shift/Refill Date**: `AsOfDate + timedelta(days=Additional_Units_Needed / Daily_Rate)`
- **Earlier Delivery Required**: `True` if `Required_Date < Earliest_Scheduled_Inbound_Date`
- **Rounding Flag**: `True` if `Additional_Needed / Unit_Multiplier` is not an integer.

## Output Generation

Create a new workbook with two sheets:
1. **Detail Sheet** (e.g., `SKU_Results`, `Unit_Results`, `Part_Results`, `Freshness_Results`, `Site_Results`): Metadata + all rows with calculated fields
2. **Summary Sheet** (e.g., `Additional_Shipments_Needed`, `Additional_Shifts_Needed`, `Additional_Resupply_Needed`, `Additional_Refills_Needed`): Only rows where units required > 0

**Structure:**
- Metadata in `A1:B4` (AsOfDate, PlanningHorizonEnd, RemainingDays) - in Key/Value format with 'Field' and 'Value' columns
- Detail headers at row 6, summary headers at row 1
- Format all dates as `YYYY-MM-DD` strings to avoid Excel serialization quirks
- **Type Safety**: Dates as strings. Booleans as native `True`/`False`. Numbers as `int`/`float`.
- Write Python booleans (`True`/`False`) directly—they become Excel booleans

**CRITICAL: Boolean Handling with openpyxl**
When using openpyxl for precise control, set boolean values explicitly:
```python
ws.cell(row=r, column=c, value=True)  # Native bool, not "True"
ws.cell(row=r, column=c, value=False)  # Native bool, not "False"
```

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
| Boolean shows as 1/0 not TRUE/FALSE | Used pandas ExcelWriter | Use openpyxl directly for type control |
| Division by zero | Daily_Rate or Daily_Required_Hours is 0 | Check rate > 0 before computing coverage |
| Horizon boundary mismatch | Used `<` instead of `<=` for horizon end | Use `<=` for planning horizon end dates |
| Date arithmetic with partial days | `timedelta` floors partial days differently | Use `math.floor()` for date offsets when needed |
| Silent output failures | Types mismatch downstream | Always verify by reading back saved workbook |
| Tool call rejected | Leading/trailing space in tool name | Use exact `Bash`, not `' Bash'` |
| Header row in data | Didn't skip metadata rows | Check if row 0 contains column names, skip if so |
| `ValueError: could not convert string to float` | Header strings in numeric columns | Skip header row before numeric conversion |
| Policy params IndexError | Assumed header row exists | Use `header=None` and `iloc[1]` for key-value parameter sheets |

## Edge Cases

- **Zero daily rate**: Coverage days = None, shortfall date = None, all additional needs = 0
- **Zero current units**: Coverage days = 0, shortfall date = AsOfDate
- **All units expiring**: Usable current = 0, DOH = 0, immediate replenishment needed
- **Inbound after horizon**: Exclude from calculations, but track for `Earliest_Scheduled_*_Date`
- **No inbound scheduled**: `Earliest_Scheduled_*_Date` = None
- **Stochastic zero stddev**: Safety buffer = 0, behaves deterministically

## Helper Script

Import or run `scripts/setup_and_load.py` to safely install `openpyxl`, normalize mixed dates (handles both datetime and string formats), extract formula multipliers, and calculate coverage gaps without boilerplate.

## Stochastic/Probabilistic Variants

For scenarios with demand uncertainty (fuel refills, critical supplies):
1. Extract `Service_Level_Z` and `Daily_Burn_StdDev` from source data
2. Calculate safety buffer: `Z * stddev * sqrt(remaining_days)`
3. Add safety buffer to deterministic demand for total required units
4. Output includes: `Safety_Buffer_Liters`, `Additional_Liters_Needed` (with buffer), `Tankers_Required_Rounded_Up`
