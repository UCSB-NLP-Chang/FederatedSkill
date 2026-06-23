---
name: excel-inventory-analysis
description: Analyze resource planning data from Excel workbooks including inventory, shipments, staffing, or any supply-demand scenario. Calculate coverage gaps, project shortfall dates, and generate procurement/shift plans. Use when tasks involve reading multi-sheet Excel files with current stock/staffing, scheduled deliveries/shifts, and conversion ratios, then computing days of coverage, out-of-stock/understaff dates, and additional requirements.
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
- **General Pattern**: Current resources + scheduled inbound - demand rate = gap analysis

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
3. **Normalize Dates**: Excel cells mix `datetime` objects and ISO strings (`YYYY-MM-DD`). **CRITICAL**: Never assume date cells are datetime objects. They may be strings. Always check both types:
   ```python
   if isinstance(val, datetime):
       return val.date()
   elif isinstance(val, str):
       return datetime.strptime(val, '%Y-%m-%d').date()
   ```
   Use `scripts/setup_and_load.py` or inline parsing to convert all to `date` objects before arithmetic.
4. **Handle Formulas**: Cells like `=80*C2` or `=24*A2` are read as strings. Extract multipliers programmatically. Do not assume `data_only=True` will return evaluated numbers unless the source file was saved post-calculation.
5. **Header Row Detection**: Many sheets have metadata rows above actual headers. Check rows 0-3 to find the true header row before processing.

## Calculation Logic (Domain-Agnostic)

Map your domain terms to these generic concepts:

| Generic | Inventory Domain | Staffing Domain |
|---------|------------------|-----------------|
| Current_Units | Current_Cases | Current_Staff_Hours |
| Daily_Rate | Daily_Case_Rate | Daily_Required_Hours |
| Inbound_Units | Inbound_Cases | Incoming_Hours |
| Unit_Multiplier | Cases_Per_Pallet | Hours_Per_Shift_Block |
| Output_Units | Pallets | Shift_Blocks |

**Core Formulas:**
- **Coverage Days**: `Current_Units / Daily_Rate` (None if Daily_Rate == 0)
- **Projected Shortfall Date**: `AsOfDate + timedelta(days=Coverage_Days)`
- **Inbound Within Horizon**: Sum units where delivery/shift date `<= PlanningHorizonEnd`
- **Remaining Demand**: `Daily_Rate * Remaining_Days_In_Horizon`
- **Additional Units Needed**: `max(0, Remaining_Demand - (Current_Units + Inbound_Units))`
- **Output Units Required**: `math.ceil(Additional_Units_Needed / Unit_Multiplier)`
- **Required Delivery/Shift Date**: `AsOfDate + timedelta(days=Additional_Units_Needed / Daily_Rate)`
- **Earlier Delivery Required**: `True` if `Required_Date < Earliest_Scheduled_Inbound_Date`

**Boolean Fields:**
- `Rounding_Applied`: True if `Output_Units_Required > 0` (meaning we rounded up)
- `Earlier_*_Required`: True if required date precedes earliest scheduled inbound

## Output Generation

Create a new workbook with two sheets:
1. **Detail Sheet** (e.g., `SKU_Results`, `Unit_Results`): Metadata + all rows with calculated fields
2. **Summary Sheet** (e.g., `Additional_Shipments_Needed`, `Additional_Shifts_Needed`): Only rows where units required > 0

**Structure:**
- Metadata in `A1:B4` (AsOfDate, PlanningHorizonEnd, RemainingDays)
- Detail headers at row 6, summary headers at row 1
- Format all dates as `YYYY-MM-DD` strings to avoid Excel serialization quirks
- Write Python booleans (`True`/`False`) directly—they become Excel booleans

**Verification Step**: Immediately reload the saved workbook. Print sheet names, headers, and row counts. Assert expected structure before finishing.

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
| Formula cells show as strings like `=24*C2` | `data_only=False` reads formulas raw | Parse multipliers manually or compute in Python |
| Boolean fields rejected by verifier | Wrote string `"True"` instead of Python `True` | Pass raw bool values to `ws.cell()` |
| Silent output failures | Types mismatch downstream | Always verify by reading back saved workbook |
| Tool call rejected | Leading/trailing space in tool name | Use exact `Bash`, not `' Bash'` |

## Edge Cases

- **Zero daily rate**: Coverage days = None, shortfall date = None, all additional needs = 0
- **Zero current units**: Coverage days = 0, shortfall date = AsOfDate
- **Inbound after horizon**: Exclude from calculations, but track for `Earliest_Scheduled_*_Date`
- **No inbound scheduled**: `Earliest_Scheduled_*_Date` = None

## Helper Script

Import or run `scripts/setup_and_load.py` to safely install `openpyxl`, normalize mixed dates (handles both datetime and string formats), and extract formula multipliers without boilerplate.