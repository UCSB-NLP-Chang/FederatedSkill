# Production Planning Scenario Templates

## Complete Scenario Configuration

### Server Provisioning Recovery Example

```python
from datetime import datetime

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
        'network_constraint': None,
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 135,
        'ten_hour_shifts': False,
    },
    'Relocated Network Equipment': {
        'date_range': (datetime(2018, 1, 22), datetime(2018, 5, 1)),
        'db_start': datetime(2018, 2, 20),
        'network_target': 100,
        'network_constraint': {'before_feb1': 100, 'after_feb1': 0},
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
        'ten_hour_shifts': True,
        'ten_hour_start': datetime(2018, 2, 1),
        'ten_hour_capacity': 170,
    }
}
```

### Fulfillment Recovery Example (Multi-Product)

```python
from datetime import datetime

COLUMN_MAP = {
    'date': 2,              # B
    'express_prod': 3,      # C
    'express_po': 4,        # D
    'express_cumul': 5,     # E (formula)
    'std_prod': 6,          # F
    'std_po': 7,            # G
    'std_cumul': 8,         # H (formula)
    'bulk_prod': 9,         # I
    'total_prod': 10,       # J (formula)
    'notes': 11,            # K
}

PO_SCHEDULE = {
    datetime(2018, 1, 22): (1065, 855),
    datetime(2018, 2, 1): (855, 555),
    datetime(2018, 2, 15): (900, 900),
    datetime(2018, 3, 1): (900, 575),
    datetime(2018, 4, 2): (900, 575),
    datetime(2018, 5, 1): (900, 575),
}

# Manitoba holidays 2018
HOLIDAYS = {
    datetime(2018, 2, 19),  # Louis Riel Day
    datetime(2018, 3, 30),  # Good Friday
}

SCENARIOS = {
    'Current Capacity and Zones': {
        'date_range': (datetime(2018, 1, 22), datetime(2018, 5, 1)),
        'std_start': datetime(2018, 3, 1),
        'bulk_total_target': 1200,
        'bulk_strategy': 'even_distribution',
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 135,
        'ten_hour_shifts': False,
    },
    'Relocated Bulk Storage': {
        'date_range': (datetime(2018, 1, 22), datetime(2018, 5, 1)),
        'std_start': datetime(2018, 2, 20),
        'bulk_total_target': 100,
        'bulk_strategy': 'front_load_before_feb1',
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 135,
        'ten_hour_shifts': False,
    },
    '10 hr Shift Relocate Bulk Stor': {
        'date_range': (datetime(2018, 1, 22), datetime(2018, 5, 1)),
        'std_start': datetime(2018, 2, 20),
        'bulk_total_target': 0,
        'bulk_strategy': 'zero_entire_horizon',
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 170,
        'ten_hour_shifts': True,
        'ten_hour_start': datetime(2018, 2, 1),
    }
}
```

## Header Row Structure

### Simple 3-Row Header
```python
def write_headers(ws, column_map):
    """Write the 3-row header structure."""
    ws.cell(row=1, column=column_map['web_planned'], value='Rack-Mount Web Servers')
    ws.cell(row=1, column=column_map['db_planned'], value='Blade Database Servers')
    ws.cell(row=1, column=column_map['network_actual'], value='Network Appliances')
    
    ws.cell(row=3, column=column_map['web_planned'], value='Planned Production')
    ws.cell(row=3, column=column_map['web_po'], value='Purchase Orders Due')
    ws.cell(row=3, column=column_map['web_cumul'], value='Cumulative Open Purchase Orders (EOD)')
```

### Merged Cell Headers (Fulfillment Pattern)
```python
def write_merged_headers(ws, column_map):
    """Write headers with merged cells for product categories."""
    ws.merge_cells('C2:E2')
    ws.merge_cells('F2:H2')
    ws.merge_cells('I2:K2')
    
    ws.cell(row=2, column=3, value='Priority Express Orders')
    ws.cell(row=2, column=6, value='Standard Freight Orders')
    ws.cell(row=2, column=9, value='Bulk Pallet Loads')
    
    ws.cell(row=3, column=2, value='Date')
    ws.cell(row=3, column=3, value='Planned Production')
    ws.cell(row=3, column=4, value='Purchase Orders Due')
    ws.cell(row=3, column=5, value='Cumulative Open Purchase Orders (EOD)')
    # ... repeat for each product group
    ws.cell(row=3, column=9, value='Actual Var to PO')
    ws.cell(row=3, column=10, value='Total Prod')
    ws.cell(row=3, column=11, value='Notes')
```

## Formula Construction

### Cumulative with Initial Condition
```python
def write_cumulative_formulas(ws, start_row, end_row, cumul_col, prod_col, po_col, initial_value=None):
    """Write cumulative formulas: =PREV_CUMUL + PO - Production."""
    from openpyxl.utils import get_column_letter
    
    cumul_letter = get_column_letter(cumul_col)
    prod_letter = get_column_letter(prod_col)
    po_letter = get_column_letter(po_col)
    
    # First data row
    if initial_value is not None:
        first_formula = f'={initial_value}+{po_letter}{start_row}-{prod_letter}{start_row}'
    else:
        first_formula = f'={po_letter}{start_row}-{prod_letter}{start_row}'
    ws.cell(row=start_row, column=cumul_col, value=first_formula)

    # Remaining rows
    for row in range(start_row + 1, end_row + 1):
        formula = f'={cumul_letter}{row-1}+{po_letter}{row}-{prod_letter}{row}'
        ws.cell(row=row, column=cumul_col, value=formula)
```

### Total Production Formula
```python
def write_total_formulas(ws, start_row, end_row, total_col, prod_cols):
    """Write sum formulas across multiple product columns."""
    from openpyxl.utils import get_column_letter
    
    prod_letters = [get_column_letter(c) for c in prod_cols]
    
    for row in range(start_row, end_row + 1):
        parts = '+'.join(f'{l}{row}' for l in prod_letters)
        formula = f'={parts}'
        ws.cell(row=row, column=total_col, value=formula)
```

## Calendar Logic

```python
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

# Regional Holiday References
HOLIDAYS_US_2018 = {datetime(2018, 1, 1), datetime(2018, 1, 15), datetime(2018, 2, 19)}
HOLIDAYS_MANITOBA_2018 = {datetime(2018, 2, 19), datetime(2018, 3, 30)}
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
        expected_rows = 3 + expected_days

        if ws.max_row != expected_rows:
            errors.append(f"{sheet_name}: row count {ws.max_row}, expected {expected_rows}")

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
    print("✓ All validations passed")
    return True

if __name__ == '__main__':
    validate(sys.argv[1], SCENARIOS)
```

## On-Time Status Calculation

```python
def calculate_on_time_status(final_cumulative):
    """Negative/Zero cumulative = orders fulfilled. Positive = backlog."""
    return "Yes" if final_cumulative <= 0 else "No"
```