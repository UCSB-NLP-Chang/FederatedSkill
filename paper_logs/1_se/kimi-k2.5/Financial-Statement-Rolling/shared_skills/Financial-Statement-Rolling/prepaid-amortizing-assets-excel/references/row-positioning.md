# Row Positioning for Prepaid/Amortizing Assets

## Dynamic Row Calculation

Always calculate control rows based on actual data count:

```python
def calculate_control_rows(data_rows, first_data_row=6):
    """
    Calculate control row positions for prepaid amortization sheets.
    
    Args:
        data_rows: List of data dictionaries
        first_data_row: Row where data starts (typically 6)
    
    Returns:
        dict with row numbers for each control section
    """
    data_count = len(data_rows)
    last_data_row = first_data_row + data_count - 1
    
    return {
        'first_data': first_data_row,
        'last_data': last_data_row,
        'month_totals': last_data_row + 1,
        'ending_balance': last_data_row + 2,
        'variance': last_data_row + 3,
        'gl_balance': last_data_row + 4
    }
```

## Examples

| Data Count | First Data | Last Data | Month Totals | Ending Balance | Variance | GL Balance |
|------------|------------|-----------|--------------|----------------|----------|------------|
| 3 rows | 6 | 8 | 9 | 10 | 11 | 12 |
| 22 rows | 6 | 27 | 28 | 29 | 30 | 31 |
| 41 rows | 6 | 46 | 47 | 48 | 49 | 50 |
| 100 rows | 6 | 105 | 106 | 107 | 108 | 109 |

## Verification Pattern

```python
def verify_row_positions(sheet, expected_rows):
    """Verify control rows have correct labels."""
    checks = [
        (expected_rows['month_totals'], 'Month Totals'),
        (expected_rows['ending_balance'], 'Ending Balance'),
        (expected_rows['variance'], 'Variance'),
        (expected_rows['gl_balance'], 'GL Balance'),
    ]
    
    for row, expected_label in checks:
        actual = sheet.cell(row, 1).value
        assert actual == expected_label, \
            f"Row {row}: expected '{expected_label}', got '{actual}'"
```

## Common Mistake: Hardcoding

**Wrong:**
```python
# Assuming 41 rows means controls at 47-50
totals_row = 47  # Breaks if data count changes!
```

**Right:**
```python
rows = calculate_control_rows(data)
totals_row = rows['month_totals']  # Adapts to data count
```

## Summary Sheet Reference Pattern

When building summary formulas, use calculated row numbers:

```python
expense_rows = calculate_control_rows(expense_data)
insurance_rows = calculate_control_rows(insurance_data)

summary['B7'] = f"='PPD Exp #1250'!O{expense_rows['month_totals']}"
summary['B8'] = f"='PPD Exp #1250'!O{expense_rows['ending_balance']}"
summary['B9'] = f"='PPD Exp #1250'!O{expense_rows['gl_balance']}"

summary['B12'] = f"='PPD Ins #1251'!O{insurance_rows['month_totals']}"
summary['B13'] = f"='PPD Ins #1251'!O{insurance_rows['ending_balance']}"
summary['B14'] = f"='PPD Ins #1251'!O{insurance_rows['gl_balance']}"
```
