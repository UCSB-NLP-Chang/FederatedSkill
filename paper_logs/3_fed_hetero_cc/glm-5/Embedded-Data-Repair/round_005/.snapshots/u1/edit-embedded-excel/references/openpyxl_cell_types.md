# openpyxl Cell Data Types Reference

## Cell.data_type Values

| Type | Meaning | Example |
|------|---------|----------|
| `'n'` | Numeric | `1.131`, `42` |
| `'f'` | Formula | `=ROUND(1/C4, 4)` |
| `'s'` | String | `"USD"` |
| `'b'` | Boolean | `True`, `False` |
| `'d'` | Date/DateTime | `datetime object` |
| `'e'` | Error | `#DIV/0!` |

## Checking Cell Type

```python
cell = ws['C4']

# Method 1: Check data_type attribute
if cell.data_type == 'f':
    print("This is a formula - don't overwrite!")

# Method 2: Check if value is string starting with =
if isinstance(cell.value, str) and cell.value.startswith('='):
    print("Formula detected")
```

## Formula Preservation Pattern

When updating value cells that formulas reference:

```python
# C4 is a value cell (data_type='n')
# D3 contains formula =ROUND(1/C4, 4)

# Correct: Update C4, D3 recalculates automatically
ws['C4'].value = 1.1590

# Wrong: Overwriting D3 breaks the calculation chain
ws['D3'].value = 0.8628  # Don't do this!
```

## Common Formula Patterns in Financial Grids

| Pattern | Purpose |
|---------|----------|
| `=ROUND(1/A1, 4)` | Reciprocal rate with precision |
| `=A1*B1` | Cross-rate calculation |
| `=IF(A1=0, 0, 1/A1)` | Safe reciprocal with zero check |

## Precision in Financial Spreadsheets

When calculating inverse values for ROUND formulas:

```python
# If formula is =ROUND(1/D5, 4) and target is 0.8645
# Calculate the inverse and round to match matrix precision

target_rate = 0.8645
matrix_precision = 4  # Match existing values like 1.1498

source_value = round(1 / target_rate, matrix_precision)  # 1.1567
ws['D5'].value = source_value
```

This ensures the formula calculates correctly and the value displays consistently with other rates.