---
name: load-plan-generation
description: Generate inventory load plans from multi-sheet Excel workbooks with stock snapshots, scheduled inbounds, and configuration. Calculates days on hand, out-of-stock dates, pallet requirements, and delivery timing for supply-chain replenishment planning.
---

# Load Plan Generation

## When to Use
- Reading multi-sheet Excel workbooks for inventory planning
- Handling dates (Excel stores dates as datetime objects)
- Creating calculated fields for supply-chain metrics
- Writing structured output workbooks with Load_Detail and Load_Action_Summary sheets

## Reading Multi-Sheet Workbooks

```python
import openpyxl

wb = openpyxl.load_workbook('/path/to/file.xlsx')
print(wb.sheetnames)  # List all sheets

for sheet_name in wb.sheetnames:
    ws = wb[sheet_name]
    for row in ws.iter_rows(values_only=True):
        print(row)
```

## Date Handling

Excel dates load as `datetime.datetime` objects. Handle explicitly:

```python
from datetime import datetime, timedelta

# Dates from Excel are datetime objects
if isinstance(cell_value, datetime):
    date_str = cell_value.strftime('%Y-%m-%d')
    date_obj = cell_value
```

## Writing Structured Output

For planning/inventory outputs, use this pattern:

1. **Metadata header rows** at top (field-value pairs)
2. **Blank row** separator
3. **Column headers** row
4. **Data rows**
5. **Blank rows** at bottom for Excel table compatibility

```python
from openpyxl.styles import Font

ws = wb.create_sheet('Sheet_Name')

# Metadata
ws['A1'] = 'Field'
ws['B1'] = 'Value'
ws['A2'] = 'AsOfDate'
ws['B2'] = datetime.now().strftime('%Y-%m-%d')

# Headers at row 5
headers = ['Col1', 'Col2', 'Col3']
for col, header in enumerate(headers, 1):
    ws.cell(row=5, column=col, value=header)
    ws.cell(row=5, column=col).font = Font(bold=True)

# Data starting at row 6
for row_idx, data in enumerate(data_rows, 6):
    for col_idx, value in enumerate(data, 1):
        ws.cell(row=row_idx, column=col_idx, value=value)
```

## Core Planning Calculations

- **Days on Hand**: `current_stock / daily_usage`
- **OOS Date**: `as_of_date + timedelta(days=days_on_hand)`
- **Pallets Required**: `ceil(cases / cases_per_pallet)`
- **Remaining Demand**: `planning_days * daily_usage - inbound_cases`
- **Additional Cases Needed**: `max(0, remaining_demand - on_floor - inbound_by_horizon)`
- **Earlier Delivery Required**: True if no inbound arrives before required delivery date

## Verification

Always verify output file creation:
```python
import os
print(f"File exists: {os.path.exists(output_path)}")
print(f"File size: {os.path.getsize(output_path)} bytes")
```

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Anti-Patterns

- Don't assume date format in cells; check `isinstance(value, datetime)`
- Don't forget blank rows at end of data for Excel table compatibility
- Don't use `ws.max_row` for iteration bounds on newly created sheets; track row count manually
- Don't assume `header=0` when metadata rows exist; inspect raw structure first
- Don't forget to validate dates are not `None` before arithmetic

## Known invariants (by sub-task)

### multi-sheet-excel-load-plan (B1)
- Configuration sheet has `AsOfDate`, `HorizonEnd`, `CasesPerPallet` in specific cells (often row 1 or 2)
- Stock Snapshot may have metadata rows before actual headers
- Only count inbounds arriving on or before `HorizonEnd`
- Output sheets: `Load_Detail` (full calculations), `Load_Action_Summary` (filtered items needing action)