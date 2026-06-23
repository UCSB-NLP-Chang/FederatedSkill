---
name: excel-manipulation
description: Create, read, and modify Excel workbooks with specific structural requirements, formulas, and data validation. Use when tasks involve .xlsx files with named sheets, header rows, formula columns, date ranges, or constraint-based data generation. Critical for production planning, order fulfillment, or any scenario requiring cumulative calculations against target obligations.
---

# Excel Workbook Manipulation with openpyxl

## When to Use This Skill

- Creating structured Excel workbooks with multiple sheets
- Reading data from existing .xlsx files (never use `Read` tool on binary Excel files)
- Building workbooks with mixed constant and formula columns
- **Production planning with cumulative constraints** (PO fulfillment, running balances against targets)
- Validating workbook structure against requirements

## Critical Setup

### Reading Excel Files

**ALWAYS** use Python with openpyxl. The `Read` tool cannot parse binary Excel files.

```python
import openpyxl
wb = openpyxl.load_workbook('/path/to/file.xlsx')
# Access sheets, cells, formulas as needed
```

### Writing Robust Python in Bash

**AVOID** semicolons in inline Python strings passed to bash. Use heredocs with `PYEOF` or similar unique delimiters:

```bash
python3 << 'PYEOF'
import openpyxl
# Python code here - no semicolon chaining needed
# Use proper newlines and indentation
PYEOF
```

**DON'T** do this:
```bash
python3 -c "import openpyxl; wb = openpyxl.load_workbook('file.xlsx'); print(wb.sheetnames)"
# Fragile: quote escaping, semicolon limits, unreadable errors
```

## Deriving Requirements from Source Data

**Before building any constraint-based workbook**, extract and calculate requirements:

```python
# Example: Production planning from PO data
wb = openpyxl.load_workbook('purchase_orders.xlsx')
ws = wb.active

# Extract PO obligations with dates and quantities
po_obligations = {}
for row in range(2, ws.max_row + 1):
    date = ws.cell(row=row, column=1).value
    quantity = ws.cell(row=row, column=2).value
    if date and quantity:
        po_obligations[date] = quantity

total_required = sum(po_obligations.values())
print(f"Total PO obligation: {total_required}")

# Calculate required daily rate over available days
available_days = 70  # or calculate from date range
required_rate = total_required / available_days
print(f"Required daily production rate: {required_rate:.1f}")
```

**Never guess production rates** - calculate from obligations divided by capacity.

## Common Workbook Patterns

### Multi-Sheet Structure with Headers

```python
from openpyxl import Workbook
from openpyxl.styles import Font

wb = Workbook()

for sheet_name in ['Sheet A', 'Sheet B', 'Sheet C']:
    ws = wb.create_sheet(title=sheet_name)
    
    # Row 2: Category headers at specific columns
    ws['C2'] = 'Category A'
    ws['F2'] = 'Category B' 
    ws['I2'] = 'Category C'
    for cell in ['C2', 'F2', 'I2']:
        ws[cell].font = Font(bold=True)
    
    # Row 3: Sub-headers spanning C3:K3
    sub_headers = ['Planned', 'Due', 'CumOpen', 'Planned', 'Due', 'CumOpen', 'Planned', 'Total', 'Notes']
    for idx, header in enumerate(sub_headers, start=3):  # C=3
        ws.cell(row=3, column=idx, value=header)
```

### Date Sequence Generation

```python
from datetime import datetime, timedelta

start_date = datetime(2018, 1, 22)
for row in range(4, 104):  # 100 rows of dates
    if row == 4:
        ws.cell(row=row, column=2, value=start_date)  # First date constant
    else:
        ws.cell(row=row, column=2, value=f'=B{row-1}+1')  # Formula for subsequent
```

### Mapping Dates to Rows

When placing data at specific calendar dates, calculate row numbers from dates. See `references/date_row_mapping.md` for the full pattern and verification steps.

```python
start_date = datetime(2018, 1, 22)
start_row = 4
target_date = datetime(2018, 2, 1)
row = start_row + (target_date - start_date).days  # Row 14
```

### Mixed Constant/Formula Columns

Common pattern: columns C,D,F,G,I hold constants; E,H,J hold formulas:

```python
# Constants
ws.cell(row=r, column=3, value=120)   # C: Express Planned (constant)
ws.cell(row=r, column=4, value=855)   # D: Express PO Due (constant)
ws.cell(row=r, column=6, value=0)     # F: Standard Planned (constant)

# Formulas with relative references
ws.cell(row=r, column=5, value=f'=E{r-1}-C{r}+D{r}')   # E: Cumulative
ws.cell(row=r, column=8, value=f'=H{r-1}-F{r}+G{r}')   # H: Cumulative  
ws.cell(row=r, column=10, value=f'=C{r}+F{r}+I{r}')    # J: Total
```

## Cumulative Constraint Validation (Critical for PO Fulfillment)

When workbooks track cumulative fulfillment against obligations:

### Calculate Required Totals Before Building

```python
# Sum all PO obligations by category
crew_pos = {
    datetime(2018, 1, 22): 1065,
    datetime(2018, 2, 1): 855,
    # ... etc
total_crew_required = sum(crew_pos.values())  # 5520

# Verify your production plan achieves this
planned_crew_total = sum(planned_daily_rates)  # Must be >= 5520 for on-time
```

### Verify Cumulative End State

```python
# Load and calculate final cumulative without relying on Excel calc
wb = openpyxl.load_workbook('output.xlsx', data_only=False)
ws = wb['Sheet1']

# Calculate cumulative manually from constants
planned_col = 3  # C
po_due_col = 4   # D
cumulative_col = 5  # E

cumulative = 0
for row in range(4, 104):
    planned = ws.cell(row=row, column=planned_col).value or 0
    po_due = ws.cell(row=row, column=po_due_col).value or 0
    # Formula is: =E{prev}-C{row}+D{row}
    cumulative = cumulative - planned + po_due
    
    # Verify against actual formula if checking mid-points
    actual_formula = ws.cell(row=row, column=cumulative_col).value
    print(f"Row {row}: calc={cumulative}, formula={actual_formula}")

# Final cumulative must be <= 0 for "on-time" fulfillment
print(f"Final cumulative: {cumulative} (<=0 means on-time)")
```

### Formula Pattern for Running Balance

```python
# First row: starting cumulative (usually =D4-C4 or explicit start)
ws.cell(row=4, column=5, value=f'=D4-C4')

# Subsequent rows: previous cumulative - planned + received
for row in range(5, last_row + 1):
    ws.cell(row=row, column=5, value=f'=E{row-1}-C{row}+D{row}')
```

## Validation Checklist

Always verify these structural elements:

1. **Sheet names** match exactly (case-sensitive)
2. **Header cells** at expected positions (C2, F2, I2, etc.)
3. **Date range** covers required span with correct start date
4. **Formula columns** actually contain formulas (check `cell.value` starts with `=`)
5. **Constant columns** contain numeric values, not formula strings
6. **Cross-row dependencies** reference correct previous rows (r-1, not hardcoded)
7. **Date-to-row mappings** place PO dates at correct row numbers (verify with calculated offsets)
8. **Cumulative end states** satisfy constraint requirements (<=0 for on-time fulfillment)

### Business Logic Verification Script

```python
import openpyxl
from datetime import datetime

wb = openpyxl.load_workbook('output.xlsx', data_only=False)

for sheet_name in wb.sheetnames:
    ws = wb[sheet_name]
    print(f"\n=== {sheet_name} ===")
    
    # Structural check
    print(f"C2: {ws['C2'].value}")
    print(f"Row 3 headers: {[ws.cell(row=3, column=c).value for c in range(3, 12)]}")
    print(f"B4 (first date): {ws['B4'].value}")
    
    # Cumulative verification (columns C=3 planned, D=4 po_due, E=5 cumulative)
    total_planned = 0
    total_po = 0
    cumulative = 0
    
    for row in range(4, ws.max_row + 1):
        planned = ws.cell(row=row, column=3).value
        po_due = ws.cell(row=row, column=4).value
        
        if isinstance(planned, (int, float)):
            total_planned += planned
        if isinstance(po_due, (int, float)):
            total_po += po_due
    
    final_cumulative = total_po - total_planned  # Simplified; use actual formula logic
    print(f"Total planned: {total_planned}, Total PO: {total_po}")
    print(f"Final cumulative: {final_cumulative} (<=0 means on-time)")
```

## Anti-Patterns to Avoid

| Anti-Pattern | Why It Fails | Better Approach |
|-------------|--------------|-----------------|
| `Read` tool on .xlsx | Binary file, tool can't parse | Always use `python3` with openpyxl |
| Semicolons in `-c` Python | Quote escaping hell, syntax errors | Use heredoc with `<< 'EOF'` |
| Hardcoded row numbers in formulas | Brittle, breaks if rows added | Use f-string with variable: `f'=B{r-1}+1'` |
| `data_only=True` when checking formulas | Returns calculated values, hides formula errors | Use `data_only=False` to inspect formula strings |
| Saving before validation | Silent errors in formulas | Verify structure before final save |
| Assuming column order | Requirements may specify non-sequential | Map explicitly: C=3, D=4, etc. |
| Manual row counting for dates | Off-by-one errors, missed dates | Calculate from date delta: `start_row + (date - start_date).days` |
| **Trial-and-error production rates** | ** Brittle, may not converge to correct constraint satisfaction** | **Calculate required rate = total_obligation / available_days** |
| **Guessing cumulative targets** | **Silent failures in PO fulfillment** | **Calculate cumulative end state explicitly from source data** |
| **Validating only structure** | **Formulas correct but business logic wrong** | **Verify cumulative calculations against PO obligations** |

## Troubleshooting

### "SyntaxError: invalid syntax" in bash Python

Your inline Python has unescaped quotes or semicolon overload. Switch to heredoc immediately.

### Formulas show as text in Excel

Cell value doesn't start with `=`. Ensure you're setting `cell.value = '=A1+B1'` not `'=A1+B1'` with extra quotes.

### Dates appear as integers

Excel stores dates as serial numbers. openpyxl handles conversion, but verify you're passing `datetime` objects, not strings.

### Formulas not calculating

Excel needs recalculation. This is normal. Check formulas with `data_only=False` to verify they're correctly stored.

### Cross-sheet references broken

Use explicit sheet names in formulas: `'Sheet Name'!A1`. Quote sheet names with spaces.

### PO dates in wrong rows

Recalculate using `(target_date - start_date).days + start_row`. Verify by printing all date-row mappings before writing. See `references/date_row_mapping.md`.

### Cumulative calculation shows wrong on-time status

1. Verify your source PO obligations are correctly extracted
2. Check that planned production totals meet or exceed obligations
3. Recalculate cumulative manually in Python to verify formula logic
4. Ensure date-to-row mapping places PO due dates at correct rows

## Fallback: When Constraint Satisfaction Fails

If you cannot achieve target cumulative states:

1. **Recalculate from first principles**: Extract all PO data, sum obligations, verify available days
2. **Check for hidden constraints**: Max daily rates, minimum batch sizes, shift changes
3. **Document the gap**: If requirements are genuinely infeasible, record calculated deficit in output
4. **Use scripts/verify_workbook.py** for automated structural checks

See `references/constraint_satisfaction.md` for detailed constraint validation patterns.