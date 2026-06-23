# Production Planning Scenario Templates

## Complete Scenario Configuration

### Server Provisioning Recovery Example

```python
from datetime import datetime

# Column schema - 1-based indexing for openpyxl
COLUMN_MAP = {
    'date': 2,           # B
    'web_planned': 3,    # C
    'web_po': 4,         # D
    'web_cumul': 5,      # E (formula)
    'db_planned': 6,     # F
    'db_po': 7,          # G
    'db_cumul': 8,       # H (formula)
    'network_actual': 9, # I
    'total_prod': 10,    # J (formula)
    'notes': 11,         # K
}

# PO due dates: date -> (web_po, db_po)
PO_SCHEDULE = {
    datetime(2018, 1, 22): (1065, 855),
    datetime(2018, 2, 1): (855, 555),
    datetime(2018, 2, 15): (900, 900),
    datetime(2018, 3, 1): (900, 575),
    datetime(2018, 4, 2): (900, 575),
    datetime(2018, 5, 1): (900, 575),
}

SCENARIOS = {
    'Current Capacity and Racks': {
        'date_range': (datetime(2018, 1, 22), datetime(2018, 5, 1)),
        'db_start': datetime(2018, 3, 1),
        'network_target': 1200,
        'network_constraint': None,  # No special timing constraint
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 135,
        'ten_hour_shifts': False,
    },
    'Relocated Network Equipment': {
        'date_range': (datetime(2018, 1, 22), datetime(2018, 5, 1)),
        'db_start': datetime(2018, 2, 20),
        'network_target': 100,
        'network_constraint': {
            'before_feb1': 100,  # Must produce 100 before Feb 1
            'after_feb1': 0,     # Zero production after Feb 1
        },
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 135,
        'ten_hour_shifts': False,
    },
    '10 hr Shift Relocate Network Eq': {
        'date_range': (datetime(2018, 1, 22), datetime(2018, 5, 1)),
        'db_start': datetime(2018, 2, 20),
        'network_target': 0,
        'network_constraint': None,
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 135,
        'ten_hour_shifts': True,  # 170 units/day on/after Feb 1
        'ten_hour_start': datetime(2018, 2, 1),
        'ten_hour_capacity': 170,
    }
}
```

## Header Row Structure

```python
def write_headers(ws, column_map):
    """Write the 3-row header structure."""
    # Row 1: Product category labels
    ws.cell(row=1, column=column_map['web_planned'], value='Rack-Mount Web Servers')
    ws.cell(row=1, column=column_map['db_planned'], value='Blade Database Servers')
    ws.cell(row=1, column=column_map['network_actual'], value='Network Appliances')

    # Row 2: spacer (merge cells visually if needed)

    # Row 3: Column labels
    ws.cell(row=3, column=column_map['web_planned'], value='Planned Production')
    ws.cell(row=3, column=column_map['web_po'], value='Purchase Orders Due')
    ws.cell(row=3, column=column_map['web_cumul'], value='Cumulative Open Purchase Orders (EOD)')
    # ... etc for all columns
```

## Formula Construction

### Cumulative with Initial Condition

```python
def write_cumulative_formulas(ws, start_row, end_row, cumul_col, prev_prod_col, po_col):
    """
    Write cumulative formulas where:
    - First row: =C4-D4 (production - PO)
    - Subsequent: =E{prev}+C{current}-D{current}
    """
    # First data row
    first_formula = f'={col_letter(prev_prod_col)}{start_row}-{col_letter(po_col)}{start_row}'
    ws.cell(row=start_row, column=cumul_col, value=first_formula)

    # Remaining rows
    for row in range(start_row + 1, end_row + 1):
        formula = f'={col_letter(cumul_col)}{row-1}+{col_letter(prev_prod_col)}{row}-{col_letter(po_col)}{row}'
        ws.cell(row=row, column=cumul_col, value=formula)

def col_letter(col_idx):
    """Convert 1-based column index to letter."""
    from openpyxl.utils import get_column_letter
    return get_column_letter(col_idx)
```

## Calendar Logic

```python
import calendar
from datetime import datetime, timedelta

def generate_date_range(start: datetime, end: datetime):
    """Generate inclusive date range."""
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)

def is_working_day(dt: datetime, holidays=None):
    """Check if date is a working day (Mon-Fri, not holiday)."""
    if dt.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    if holidays and dt in holidays:
        return False
    return True

# US Federal Holidays 2018 (example)
HOLIDAYS_2018 = {
    datetime(2018, 1, 1),   # New Year's
    datetime(2018, 1, 15),  # MLK Day
    datetime(2018, 2, 19),  # Presidents Day
    # ... etc
}
```

## Validation Script

```python
#!/usr/bin/env python3
"""Validate production planning workbook structure."""
from openpyxl import load_workbook
from datetime import datetime
import sys

def validate(filepath, scenarios_config):
    wb = load_workbook(filepath, data_only=False)

    errors = []

    for sheet_name, config in scenarios_config.items():
        if sheet_name not in wb.sheetnames:
            errors.append(f"Missing sheet: {sheet_name}")
            continue

        ws = wb[sheet_name]
        start_date, end_date = config['date_range']
        expected_days = (end_date - start_date).days + 1
        expected_rows = 3 + expected_days  # 3 header rows + data

        if ws.max_row != expected_rows:
            errors.append(f"{sheet_name}: row count {ws.max_row}, expected {expected_rows}")

        # Check date sequence
        for i, expected_date in enumerate(generate_date_range(start_date, end_date)):
            row = 4 + i
            actual = ws.cell(row=row, column=2).value
            if actual != expected_date:
                errors.append(f"{sheet_name} B{row}: {actual}, expected {expected_date}")

    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print(f"  - {e}")
        return False
    print("All validations passed")
    return True

if __name__ == '__main__':
    validate(sys.argv[1], SCENARIOS)
```