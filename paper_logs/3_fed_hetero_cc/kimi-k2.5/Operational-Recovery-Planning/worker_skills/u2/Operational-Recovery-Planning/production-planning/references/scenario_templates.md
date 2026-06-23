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

SCENARIOS = {
    'Current Capacity and Racks': {
        'date_range': (datetime(2018, 1, 22), datetime(2018, 5, 1)),
        'db_start': datetime(2018, 3, 1),
        'network_target': 1200,
        'network_constraint': None,
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 135,
    },
    'Relocated Network Equipment': {
        'date_range': (datetime(2018, 1, 22), datetime(2018, 5, 1)),
        'db_start': datetime(2018, 2, 20),
        'network_target': 100,
        'network_constraint': {'before_feb1': 100, 'after_feb1': 0},
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 135,
    }
}
```

### Fulfillment Recovery Example (Multi-Product)

```python
from datetime import datetime

COLUMN_MAP = {
    'date': 2,              # B
    'express_planned': 3,   # C
    'express_po': 4,        # D
    'express_cumul': 5,     # E (formula)
    'standard_planned': 6,  # F
    'standard_po': 7,       # G
    'standard_cumul': 8,    # H (formula)
    'bulk_actual': 9,       # I
    'total_prod': 10,       # J (formula)
    'notes': 11,            # K
}

MANITOBA_HOLIDAYS = {
    datetime(2018, 2, 19),  # Louis Riel Day
    datetime(2018, 3, 30),  # Good Friday
}

def is_working_day_manitoba(dt):
    return dt.weekday() < 5 and dt not in MANITOBA_HOLIDAYS

SCENARIOS = {
    'Current Capacity and Zones': {
        'standard_start': datetime(2018, 3, 1),
        'bulk_min_total': 1200,
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 135,
    },
    'Relocated Bulk Storage': {
        'standard_start': datetime(2018, 2, 20),
        'bulk_timing': {'before_feb1_min': 100, 'after_feb1': 0},
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 135,
    },
    '10 hr Shift Relocate Bulk Stor': {
        'standard_start': datetime(2018, 2, 20),
        'ten_hour_shifts': True,
        'ten_hour_start': datetime(2018, 2, 1),
        'ten_hour_capacity': 170,
    }
}
```

## Header Row Structure

```python
def write_merged_headers(ws, column_map):
    """Write headers with merged cells for product categories."""
    ws.merge_cells('C2:E2')
    ws.merge_cells('F2:H2')
    ws.cell(row=2, column=3, value='Priority Express Orders')
    ws.cell(row=2, column=6, value='Standard Freight Orders')
    
    # Row 3: Column labels
    ws.cell(row=3, column=3, value='Planned Production')
    ws.cell(row=3, column=4, value='Purchase Orders Due')
    ws.cell(row=3, column=5, value='Cumulative Open Purchase Orders (EOD)')
```

## Formula Construction

### Cumulative with Initial Condition
```python
def write_cumulative_formulas(ws, start_row, end_row, cumul_col, prod_col, po_col, initial_value=None):
    from openpyxl.utils import get_column_letter
    c, p, po = get_column_letter(cumul_col), get_column_letter(prod_col), get_column_letter(po_col)
    
    first = f'={initial_value}+{p}{start_row}-{po}{start_row}' if initial_value else f'={p}{start_row}-{po}{start_row}'
    ws.cell(row=start_row, column=cumul_col, value=first)
    
    for row in range(start_row + 1, end_row + 1):
        ws.cell(row=row, column=cumul_col, value=f'={c}{row-1}+{p}{row}-{po}{row}')

def write_total_formulas(ws, start_row, end_row, total_col, prod_cols):
    from openpyxl.utils import get_column_letter
    t = get_column_letter(total_col)
    letters = [get_column_letter(c) for c in prod_cols]
    for row in range(start_row, end_row + 1):
        ws.cell(row=row, column=total_col, value=f'={'+'.join(f'{l}{row}' for l in letters)}')
```

## Calendar Logic

```python
from datetime import datetime, timedelta

def generate_date_range(start: datetime, end: datetime):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)

def is_working_day(dt: datetime, holidays=None):
    if dt.weekday() >= 5:
        return False
    if holidays and dt in holidays:
        return False
    return True
```

## Validation Script

```python
#!/usr/bin/env python3
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
        start, end = config['date_range']
        expected_rows = 3 + (end - start).days + 1
        if ws.max_row != expected_rows:
            errors.append(f"{sheet_name}: row count {ws.max_row}, expected {expected_rows}")
    if errors:
        print("VALIDATION FAILED:\n" + "\n".join(f"  - {e}" for e in errors))
        return False
    print("✓ All validations passed")
    return True
```

## On-Time Status Calculation

```python
def calculate_on_time_status(final_cumulative):
    """Negative or zero = over-produced (orders fulfilled). Positive = backlog."""
    return "Yes" if final_cumulative <= 0 else "No"

def get_multi_product_status(product_cumul_map):
    """Check all product lines."""
    statuses = ["Yes" if v <= 0 else "No" for v in product_cumul_map.values()]
    if all(s == "Yes" for s in statuses):
        return "Yes"
    elif all(s == "No" for s in statuses):
        return "No"
    else:
        return ", ".join(f"{k}: {v}" for k, v in zip(product_cumul_map.keys(), statuses))
```