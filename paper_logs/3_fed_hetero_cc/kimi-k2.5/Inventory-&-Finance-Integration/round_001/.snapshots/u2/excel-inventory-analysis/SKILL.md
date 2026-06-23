---
name: excel-inventory-analysis
description: Analyze inventory and shipment data from Excel workbooks, calculate supply gaps, and generate updated shipment plans. Use when tasks involve reading multi-sheet Excel files with inventory, shipment schedules, and ratios, then computing days-on-hand, out-of-stock dates, and additional pallet requirements.
---

# Excel Inventory & Shipment Analysis

## CRITICAL ANTI-PATTERN (kimi-k2.5)

**Tool names must be EXACTLY matched. Never add leading/trailing spaces:**
- CORRECT: `Bash`
- WRONG: `' Bash'` (leading space) — this causes immediate tool rejection
- WRONG: `'Bash '` (trailing space)
- WRONG: `' Bash '` (both)

The harness rejects tool calls with mismatched names. Always verify your tool invocations use exact names.

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
2. **Identify Sheets**: Inspect `wb.sheetnames`. Typical layout: `Current Inventory`, `Incoming Shipments`, `Ratio`.
3. **Normalize Dates**: Excel cells mix `datetime` objects and ISO strings (`YYYY-MM-DD`). Use `scripts/setup_and_load.py` or inline parsing to convert all to `date` objects before arithmetic.
4. **Handle Formulas**: Cells like `=80*C2` are read as strings. Extract multipliers programmatically. Do not assume `data_only=True` will return evaluated numbers unless the source file was saved post-calculation.
5. **Header Row Detection**: Many inventory sheets have metadata rows above actual headers. Check rows 0-3 to find the true header row before processing.

## Calculation Logic

- **Days on Hand (DOH)**: `Current_Cases / Daily_Rate`
- **Projected OOS Date**: `AsOfDate + timedelta(days=DOH)`
- **Inbound Cases**: Sum `Pallets * Cases_Per_Pallet` for deliveries `<= PlanningHorizonEnd`.
- **Remaining Demand**: `Daily_Rate * Remaining_Days_In_Horizon`
- **Additional Cases Needed**: `max(0, Remaining_Demand - (Current_Cases + Inbound_Cases))`
- **Pallets Required**: `math.ceil(Additional_Cases / Cases_Per_Pallet)`
- **Required Delivery Date**: `AsOfDate + timedelta(days=Additional_Cases / Daily_Rate)`
- **Earlier Delivery Required**: `True` if `Required_Delivery_Date < Earliest_Scheduled_Inbound_Date`

## Output Generation

- Create a new workbook with `SKU_Results` (metadata + detailed rows) and `Additional_Shipments_Needed` (summary).
- Write metadata in `A1:B4` (AsOfDate, PlanningHorizonEnd, RemainingDays).
- Place headers at row 6 for `SKU_Results`, row 1 for `Additional_Shipments_Needed`.
- Format all dates as `YYYY-MM-DD` strings to avoid Excel serialization quirks.
- **Verification Step**: Immediately reload the saved workbook. Print sheet names, headers, and row counts. Assert expected structure before finishing.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Anti-Patterns & Troubleshooting

- **Import Error**: `from datetime import datetime, date` followed by `date.timedelta` causes `AttributeError`. Always use `datetime.timedelta` or import `timedelta` directly.
- **Date Parsing**: Never assume uniform formats. Check `isinstance(val, datetime)` first.
- **Formula Evaluation**: `openpyxl` does not evaluate formulas. Parse them manually or compute values in Python before writing.
- **Silent Failures**: Always verify output by reading it back. Mismatched types (e.g., writing `datetime` instead of string) often break downstream verifiers.
- **Tool Name Typos**: Using `' Bash'` (with leading space) instead of `'Bash'` causes immediate rejection. Always verify exact tool names.

## Helper Script

Import or run `scripts/setup_and_load.py` to safely install `openpyxl`, normalize mixed dates, and extract formula multipliers without boilerplate.
