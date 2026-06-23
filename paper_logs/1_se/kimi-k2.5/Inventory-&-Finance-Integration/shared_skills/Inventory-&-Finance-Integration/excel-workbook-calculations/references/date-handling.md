# Date Handling in Excel Workbooks

## Extracting Dates from Irregular Headers

Excel files often store dates in header rows with descriptive text.

### Pattern: Descriptive Cell with Embedded Date
```
Cell A1: "Today's Date"
Cell B1: 2025-07-04 00:00:00 (datetime object)
Cell C1: "Month End"
Cell D1: 2025-07-31 00:00:00 (datetime object)
```

### Extraction Strategy
```python
def extract_date_from_header(df_header, row_idx, col_idx, is_text_cell=False):
    """
    Extract date from header DataFrame.
    
    df_header: DataFrame read with nrows=2 (just header section)
    row_idx: row containing the date (usually 0)
    col_idx: column containing the date value
    is_text_cell: if True, parse with regex; if False, use datetime directly
    """
    import re
    from datetime import datetime
    
    cell_value = df_header.iloc[row_idx, col_idx]
    
    if pd.isna(cell_value):
        return None
    
    if isinstance(cell_value, str):
        # Text like "Today's Date 2025-07-04 00:00:00"
        match = re.search(r'(\d{4}-\d{2}-\d{2})', cell_value)
        if match:
            return datetime.strptime(match.group(1), '%Y-%m-%d').date()
    elif hasattr(cell_value, 'date'):
        # pandas Timestamp or datetime object
        return cell_value.date()
    else:
        # Already a date
        return cell_value
```

## Writing Dates Back to Excel

### As ISO Strings (Recommended for Cross-Platform)
```python
ws['B2'] = date_obj.isoformat()  # "2025-07-04"
```

### As Native Excel Dates
```python
from openpyxl.utils.datetime import datetime_to_excel_serial
# openpyxl handles datetime objects automatically when assigned
ws['B2'] = datetime(2025, 7, 4)  # Stored as Excel serial date
```

## Common Date Calculations

### Days Remaining in Period
```python
from datetime import date
remaining = (planning_horizon_end - asof_date).days
```

### Projected Out-of-Stock Date
```python
import numpy as np
projected_oos = asof_date + timedelta(days=np.floor(current_stock / daily_rate))
```

### Required Delivery Date (Business Days Logic)
```python
# Simple calendar days; adjust for business days if needed
required_delivery = projected_oos + timedelta(days=lead_time_days)
```