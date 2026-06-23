# Troubleshooting Table

Common issues when parsing supply-chain Excel exports with irregular layouts.

| Symptom | Cause | Fix |
|---------|-------|-----|
| "could not convert string to float" | Header text in data rows | Inspect raw structure first, use `skiprows` based on header row position |
| Dates show as integers (e.g., 45474) | Excel serial dates not parsed | Use `pd.to_datetime` explicitly or check `isinstance(value, datetime)` |
| Missing items in output | Merge/concat lost rows | Verify item list before and after joins |
| Earlier delivery all True/False | Date comparison timezone issues | Ensure all dates are naive or UTC |
| `TypeError: unsupported operand type(s) for -: 'NoneType' and 'NoneType'` | Assuming dates in fixed row without checking | Always assert `cell.value is not None` and `isinstance(cell.value, (date, datetime))` before subtraction |
| Division by zero error | `DailySales == 0` when calculating DOH | Guard against zero before division |
| Inbound filtering wrong | Including future inbounds outside planning horizon | Only count inbounds arriving `<= HorizonEnd` |

## Pre-flight inspection pattern

Before parsing with pandas, inspect raw structure:

```python
# Read without headers to see actual layout
df_raw = pd.read_excel(file, sheet_name='Stock Snapshot', header=None, nrows=10)
print(df_raw.head())

# Identify: metadata rows, blank rows, actual header row, data start row
# Common pattern: row 0 = metadata, row 1 = blank, row 2 = headers, row 3+ = data
```

Then use `skiprows` appropriately:

```python
# After inspection confirmed header at row 2 (index)
df = pd.read_excel(file, sheet_name='Stock Snapshot', skiprows=[0, 1])
```