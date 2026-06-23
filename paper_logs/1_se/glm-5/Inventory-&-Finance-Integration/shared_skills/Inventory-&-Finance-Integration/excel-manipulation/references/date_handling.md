# Excel Date Handling Details

## Date Storage in Excel

Excel stores dates as serial numbers (days since 1899-12-30). openpyxl converts these to Python `datetime` objects when reading.

## Common Date Scenarios

### Scenario 1: Native Excel Dates
When a cell contains a proper Excel date:
```python
from openpyxl import load_workbook

wb = load_workbook('file.xlsx')
ws = wb.active
val = ws['A1'].value  # Returns datetime.datetime(2025, 7, 4, 0, 0)
```

### Scenario 2: String Dates
When dates are entered as text:
```python
val = ws['A1'].value  # Returns '2025-07-04' or '07/04/2025'
```

### Scenario 3: Mixed Formats in Same Column
```python
def normalize_date(val):
    from datetime import datetime
    
    if val is None:
        return None
    
    if isinstance(val, datetime):
        return val.date()
    
    if isinstance(val, str):
        # Try common formats
        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y']:
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
    
    return None
```

## Date Arithmetic

**Critical**: You cannot add integers directly to `date` or `datetime` objects. Always use `timedelta`.

```python
from datetime import date, timedelta

# WRONG - TypeError: unsupported operand type(s) for +: 'datetime.date' and 'int'
future_date = some_date + 7

# CORRECT - Use timedelta for date arithmetic
future_date = some_date + timedelta(days=7)

# Common patterns:
days_until_eom = (end_of_month - today).days  # Get difference in days
delivery_date = today + timedelta(days=lead_time_days)  # Add days to date
oos_date = current_date + timedelta(days=current_doh)  # Project out-of-stock date
```

### Why This Matters
When reading dates from Excel, you often get `datetime.date` objects. Calculations like "add N days" require `timedelta`:
```python
from datetime import datetime, timedelta

# Excel date read as datetime
excel_date = ws['A1'].value  # datetime.datetime(2025, 11, 5, 0, 0)

# Convert to date if needed
as_date = excel_date.date() if isinstance(excel_date, datetime) else excel_date

# Add days - MUST use timedelta
planning_end = as_date + timedelta(days=25)  # Correct
```

## Writing Dates

```python
from datetime import datetime
from openpyxl import Workbook

wb = Workbook()
ws = wb.active

# Write datetime - Excel will format as date
ws['A1'] = datetime(2025, 7, 4)

# Apply date format
ws['A1'].number_format = 'YYYY-MM-DD'
```
