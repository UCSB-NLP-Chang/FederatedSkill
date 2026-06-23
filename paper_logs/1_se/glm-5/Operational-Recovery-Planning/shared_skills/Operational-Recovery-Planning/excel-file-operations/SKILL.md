---
name: excel-file-operations
description: Read and write Excel files using openpyxl when pandas is unavailable. Use for tasks involving .xlsx file input/output, data extraction from spreadsheets, generating formatted Excel reports, production planning calculations, working day calculations with holidays, cumulative formula construction, capacity-constrained scheduling, and multi-scenario workbook generation. Supports both row-oriented and column-oriented data extraction.
---

# Excel File Operations

## When to Use
- Reading data from .xlsx files when pandas is not installed
- Writing data to Excel with formatting (headers, fonts)
- Extracting row/column data from spreadsheet inputs
- Generating structured Excel reports
- Processing spreadsheets with data organized by columns instead of rows
- Creating production planning or scheduling spreadsheets
- Calculating working days excluding weekends and holidays
- Building cumulative/running total formulas
- Capacity-constrained production schedules with outcome targets
- Multi-scenario workbooks with shared structure but different parameters

## Reading Excel Files

```python
import openpyxl

# Load workbook
wb = openpyxl.load_workbook('/path/to/file.xlsx')
ws = wb.active  # or wb['SheetName']

# Read all rows as list of lists
for row in ws.iter_rows(values_only=True):
    print(row)

# Read specific cell
value = ws['A1'].value

# Read row by index (1-based)
row_values = [cell.value for cell in ws[1]]

# Read column by letter
col_values = [cell.value for cell in ws['A']]
```

## Date Handling from Excel

Excel date cells can return `datetime.datetime` objects, `datetime.date` objects, or strings depending on cell formatting. Always normalize before comparison:

```python
from datetime import datetime, date

def normalize_date(val):
    """Convert datetime.datetime, string, or other to date, or return None."""
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        # Try parsing common Excel date formats
        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d-%b-%Y', '%Y/%m/%d']:
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
        return None
    return None

# Safe comparison with dates from Excel
cell_date = normalize_date(ws['A1'].value)
target_date = date(2018, 2, 5)
if cell_date == target_date:
    print("Match")

# When iterating rows with dates
for row in ws.iter_rows(values_only=True):
    row_date = normalize_date(row[0])
    if row_date and row_date < cutoff_date:
        process(row)
```

## Finding Rows by Content

When spreadsheets have labeled rows instead of standard headers:

```python
# Find a row by searching for a label in column A
target_row = None
for row in ws.iter_rows(values_only=True):
    if row[0] == 'Target Label':
        target_row = row
        break

# Get all values from that row (excluding the label)
data_values = target_row[1:]  # Skip first column (label)
```

## Column-Oriented Data

When data is organized with time periods or categories as columns:

```python
# Read column headers from a specific row
week_numbers = [cell.value for cell in ws[3]]  # Row 3 has week numbers

# Read data values from a labeled row
for row in ws.iter_rows(values_only=True):
    if row[0] == 'Reading Load Forecast Total':
        forecast_values = row[1:]  # All values after the label
        break

# Pair column headers with row values
data_by_week = dict(zip(week_numbers[1:], forecast_values))
```

## Multi-Row Columnar Layouts

When multiple rows contain different metrics for the same columns (e.g., week numbers in row 3, values in rows 4-6):

```python
# Step 1: Identify the structure by inspecting first few rows
for i, row in enumerate(ws.iter_rows(values_only=True), 1):
    print(f"Row {i}: {row[:5]}...")  # Preview first 5 columns
    if i >= 10:
        break

# Step 2: Extract column headers (e.g., week numbers)
week_row = [cell.value for cell in ws[3]]  # Row 3 has week numbers
weeks = week_row[1:]  # Skip column A (row label)

# Step 3: Extract each metric row by label
metrics = {}
for row in ws.iter_rows(values_only=True):
    label = row[0]
    if label in ['Training Reserve Hours', 'Exception Review Hours', 'Standard Return Intake Hours']:
        metrics[label] = row[1:]  # Skip label column

# Step 4: Verify alignment by checking first value from each source
print(f"Weeks start: {weeks[0]}, end: {weeks[-1]}")
for name, values in metrics.items():
    print(f"{name}: first={values[0]}, count={len(values)}")

# Step 5: Build aligned dataset
for i, week in enumerate(weeks):
    total = sum(metrics[m][i] for m in metrics if metrics[m][i] is not None)
    print(f"Week {week}: total={total}")
```

## Writing Excel Files

```python
import openpyxl
from openpyxl.styles import Font

wb = openpyxl.Workbook()
ws = wb.active
ws.title = 'SheetName'

# Write header row with bold font
headers = ['Column1', 'Column2', 'Column3']
for col, header in enumerate(headers, 1):
    cell = ws.cell(row=1, column=col, value=header)
    cell.font = Font(bold=True)

# Write data rows
for row_idx, row_data in enumerate(data_rows, 2):
    for col_idx, value in enumerate(row_data, 1):
        ws.cell(row=row_idx, column=col_idx, value=value)

wb.save('/path/to/output.xlsx')
```

## Working Day Calculations

When calculating production schedules or deadlines excluding weekends and holidays:

```python
from datetime import datetime, timedelta

def is_working_day(date, holidays=None):
    """Check if a date is a working day (not weekend or holiday)."""
    if holidays is None:
        holidays = set()
    # Saturday=5, Sunday=6
    if date.weekday() >= 5:
        return False
    if date in holidays:
        return False
    return True

def get_working_days_between(start_date, end_date, holidays=None):
    """Count working days between two dates (inclusive)."""
    if holidays is None:
        holidays = set()
    count = 0
    current = start_date
    while current <= end_date:
        if is_working_day(current, holidays):
            count += 1
        current += timedelta(days=1)
    return count

# Example: Manitoba holidays for 2018
holidays = {
    datetime(2018, 2, 19).date(),  # Louis Riel Day
    datetime(2018, 3, 30).date(),   # Good Friday
}
```

## Production Planning with Capacity Constraints

When building schedules that must meet specific outcomes:

```python
# 1. Extract PO requirements from source data
# 2. Calculate working days in planning horizon
# 3. Apply capacity limits only on working days
# 4. Build cumulative formulas for running totals
# 5. Verify outcomes match requirements
# 6. Iterate if needed - adjust production to hit target backlogs

def calculate_production_schedule(start_date, end_date, daily_capacity, holidays, po_due_by_date):
    """Generate production schedule respecting capacity and working days."""
    schedule = []
    current = start_date
    while current <= end_date:
        if is_working_day(current, holidays):
            production = daily_capacity
        else:
            production = 0
        po_due = po_due_by_date.get(current, 0)
        schedule.append((current, production, po_due))
        current += timedelta(days=1)
    return schedule

# When outcomes must match targets, calculate required production:
def calculate_required_production(total_po_due, target_backlog, working_days, max_daily_capacity):
    """Determine if target backlog is achievable within capacity."""
    required_production = total_po_due - target_backlog
    daily_needed = required_production / working_days
    feasible = daily_needed <= max_daily_capacity
    return required_production, feasible
```

## Cumulative Formula Construction

When building running totals or cumulative columns:

```python
# First row: simple difference
ws['E4'] = '=D4-C4'  # Cumulative = PO - Production

# Subsequent rows: add to previous cumulative
ws['E5'] = '=E4+D5-C5'

# Pattern for setting formulas across many rows
for row in range(5, max_row + 1):
    ws.cell(row=row, column=5, value=f'=E{row-1}+D{row}-C{row}')
```

## Date-Based Conditional Logic

When different rules apply before/after specific dates:

```python
from datetime import datetime

capacity_change_date = datetime(2018, 2, 5).date()

for row_idx, date in enumerate(dates, start=4):  # Start at row 4
    if date < capacity_change_date:
        capacity = 120  # Old capacity
    else:
        capacity = 135  # New capacity
    
    # Apply capacity only on working days
    if is_working_day(date, holidays):
        production = min(backlog, capacity)
    else:
        production = 0
```

## Multi-Sheet Workbooks

When creating multiple scenarios in one workbook:

```python
wb = openpyxl.Workbook()

# First sheet (default)
ws1 = wb.active
ws1.title = 'Scenario 1'

# Additional sheets
ws2 = wb.create_sheet('Scenario 2')
ws3 = wb.create_sheet('Scenario 3')

# Apply same structure to all sheets
for ws in [ws1, ws2, ws3]:
    # Write headers, set up structure
    write_headers(ws)
    # Sheet-specific data will be filled separately

wb.save('/path/to/multi_scenario.xlsx')
```

## Multi-Scenario Validation

When generating multiple scenarios with different constraints, validate each independently:

```python
scenarios = [
    {'name': 'Scenario 1', 'flax_total': 1200, 'canola_start': date(2018, 3, 1)},
    {'name': 'Scenario 2', 'flax_total': 100, 'canola_start': date(2018, 2, 20)},
    {'name': 'Scenario 3', 'flax_total': 0, 'ten_hour_days': 22},
]

for scenario in scenarios:
    ws = wb[scenario['name']]
    # Validate scenario-specific constraints
    flax_sum = sum(ws.cell(row=r, column=9).value or 0 for r in range(4, max_row+1))
    assert flax_sum == scenario['flax_total'], f"{scenario['name']}: Flax total {flax_sum} != {scenario['flax_total']}"
    
    # Validate common constraints
    for row in ws.iter_rows(min_row=4, values_only=True):
        date_val = normalize_date(row[0])
        if date_val and not is_working_day(date_val, holidays):
            assert row[2] == 0, f"{scenario['name']}: Non-zero production on non-working day {date_val}"
```

## Validating Generated Data

After writing calculated data to Excel, always verify logical correctness—not just file structure:

```python
# After generating output, check for data sanity
wb = openpyxl.load_workbook('/path/to/output.xlsx')
ws = wb.active

# Check for unexpected negative values in columns that should be non-negative
for row in ws.iter_rows(min_row=2, values_only=True):
    backlog = row[5]  # Example: column F is backlog
    if backlog is not None and backlog < -100:  # Allow small negative buffers
        print(f"WARNING: Unexpected backlog value: {backlog}")

# Check for reasonable ranges
for row in ws.iter_rows(min_row=2, values_only=True):
    days_worked = row[1]
    if days_worked not in [4, 5, 6, 7]:
        print(f"WARNING: Unusual days_worked value: {days_worked}")

# Spot-check first and last rows for logical progression
first_data_row = list(ws.iter_rows(min_row=2, max_row=2, values_only=True))[0]
last_data_row = list(ws.iter_rows(min_row=ws.max_row, values_only=True))[0]
print(f"First row: {first_data_row}")
print(f"Last row: {last_data_row}")
```

## Validating Extraction Alignment

When extracting data from multi-row layouts, verify alignment before proceeding with calculations:

```python
# After extracting multiple rows, cross-check against source
# Example: if row 4 says "Do Not Use", verify you're NOT using it
for row in ws.iter_rows(values_only=True):
    if row[0] and 'do not use' in str(row[0]).lower():
        print(f"NOTICE: Row labeled '{row[0]}' - verify this is excluded from calculations")

# Verify extracted values match visible source values
# Spot-check first column of each extracted row
source_check = ws.cell(row=2, column=2).value  # Row 2, column B
extracted_check = metrics['Training Reserve Hours'][0]  # First value
if source_check != extracted_check:
    print(f"ERROR: Extraction misaligned! Source={source_check}, Extracted={extracted_check}")

# Verify calculated totals are reasonable
for i, week in enumerate(weeks[:3]):  # Check first 3 weeks
    calculated_total = sum(metrics[m][i] for m in metrics)
    print(f"Week {week} calculated total: {calculated_total}")
    # Compare against any reference totals if available
```

## Iterative Constraint Satisfaction

When production schedules must achieve specific backlog targets, use iterative adjustment:

```python
# 1. Calculate total PO demand and working days
# 2. Determine if target backlog is achievable with available capacity
# 3. If not, identify which constraints can be relaxed
# 4. Adjust production values and re-validate
# 5. Repeat until all constraints are satisfied

def validate_backlog_targets(ws, targets, start_row, end_row):
    """Verify each scenario meets its backlog target."""
    results = {}
    for scenario_name, target in targets.items():
        # Calculate final cumulative from formulas or values
        final_backlog = ws.cell(row=end_row, column=5).value  # Example column
        results[scenario_name] = {
            'actual': final_backlog,
            'target': target,
            'on_time': final_backlog <= 0 if target == 0 else final_backlog <= target
        }
    return results

# If validation fails, adjust production and regenerate
# Common adjustments: reduce production in early days, shift capacity between products
```

## Common Patterns

### Extract row data by header name
```python
# Get header row
headers = [cell.value for cell in ws[1]]

# Build dict for each data row
for row in ws.iter_rows(min_row=2, values_only=True):
    row_dict = dict(zip(headers, row))
```

### Check dimensions
```python
max_row = ws.max_row
max_col = ws.max_column
```

### Iterate with row numbers
```python
for row_num, row in enumerate(ws.iter_rows(values_only=True), 1):
    print(f"Row {row_num}: {row}")
```

## Troubleshooting
- **ModuleNotFoundError: pandas**: Use openpyxl instead - it's often available when pandas isn't
- **Empty cells return None**: Check `if cell.value is not None` before processing
- **Row/column indices are 1-based**: Unlike Python lists, Excel indices start at 1
- **Mixed data orientations**: Check whether your data is organized by rows or columns before extracting; inspect a few sample rows first with `list(ws.iter_rows(values_only=True))[:5]`
- **Labels in first column**: If row labels are in column A, skip index 0 when extracting data values
- **Generated data looks wrong**: Verify calculations by checking first/last rows and looking for values outside expected ranges (e.g., massive negative numbers in a backlog column indicate a logic error in the generation algorithm)
- **Variable name typos**: When refactoring code, ensure all variable references are updated consistently; use find-and-replace or IDE refactoring tools
- **Column misalignment**: When extracting from multiple rows, verify each row's values align with the same columns by checking that all extracted arrays have the same length and that spot-checked values match the source spreadsheet
- **Wrong row used**: If a row is labeled "Do Not Use" or "Illustrative", exclude it from calculations and compute totals from component rows instead
- **Extraction vs calculation mismatch**: After extracting data, print the first few calculated values and manually verify them against the visible spreadsheet values before proceeding with the full analysis
- **Cumulative formula errors**: When building running totals, the first row should be a simple formula (e.g., `=D4-C4`), subsequent rows reference the previous row (e.g., `=E4+D5-C5`)
- **Date comparison issues**: Excel returns `datetime.datetime` objects, strings, or `datetime.date` objects. Always normalize with the `normalize_date()` function before comparing. See the Date Handling section for the complete normalization pattern.
- **Holiday list incomplete**: When calculating working days, verify the holiday list matches the jurisdiction/region for the task
- **Constraint validation missed**: After generating data, verify ALL constraints are met (totals, date ranges, capacity limits) before declaring completion
- **Outcome mismatch**: When production must achieve specific backlog targets, calculate required production first and verify feasibility against capacity constraints before building the schedule
- **Self-validation insufficient**: When verifier tests fail despite passing local checks, re-examine the task requirements for misinterpreted constraints, missing deliverables, or format requirements not captured in self-validation
- **Multi-scenario consistency**: When generating multiple scenarios, verify each scenario independently against its specific constraints, not just against common patterns
- **values_only=True with .value access**: When using `ws.iter_rows(values_only=True)`, each row is a tuple of values, not cell objects. Access values directly as `row[0]`, not `row[0].value`. If you need cell properties (formatting, formulas), omit `values_only=True` and access `.value` on each cell object.
- **String dates from Excel**: Excel cells with dates can return strings instead of datetime objects depending on cell formatting. Always use `normalize_date()` which handles strings, datetime, and date objects.
- **Binary file read error**: The `Read` tool cannot read binary .xlsx files. Use openpyxl via `Skill: excel-file-operations` or direct Python with `openpyxl.load_workbook()` instead.
