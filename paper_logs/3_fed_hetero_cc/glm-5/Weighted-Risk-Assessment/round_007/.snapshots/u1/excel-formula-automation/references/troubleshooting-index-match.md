# Troubleshooting INDEX/MATCH Formulas

## Common Failure Modes

### 1. MATCH Returns Wrong Position

**Symptom**: Formula evaluates but returns value from wrong row/column

**Causes**:
- MATCH mode omitted (defaults to 1 = sorted ascending). Use `0` for exact match.
- Data not sorted when using mode 1 or -1
- Duplicate lookup keys in range (MATCH returns first match only)

**Diagnosis**:
```python
# Manual verification - check what MATCH should return
search_value = "PLA_FIN_OUT"
search_range = ["PLA_FIN_OUT", "PLA_SCRAP", "PLA_RATED_CAP", ...]  # from Data!D21:D38
expected_position = search_range.index(search_value) + 1  # 1-indexed for Excel
```

### 2. Type Mismatches

**Symptom**: Exact match fails despite value appearing identical

**Causes**:
- Float vs string: `123.0` != `"123"`
- Numeric codes stored as text in one sheet, numbers in another
- Leading/trailing spaces or invisible characters

**Diagnosis**:
```python
# Check actual types and repr
for cell in data_range:
    print(f"Value: {repr(cell.value)}, Type: {type(cell.value)}")
```

### 3. Range Dimension Mismatches

**Symptom**: `#VALUE!` error

**Cause**: INDEX array dimensions don't match MATCH results

**Rule**: For 2D INDEX/MATCH/MATCH:
- First MATCH (row) must return index within row count of INDEX array
- Second MATCH (column) must return index within column count of INDEX array

```
Data!$H$21:$L$38 has 18 rows (21-38), 5 columns (H-L)
MATCH on rows must return 1-18
MATCH on columns must return 1-5
```

### 4. Header Row Confusion

**Symptom**: Column MATCH fails or returns wrong year

**Common mistake**: Assuming year headers are in row 21 (with data) when they're in row 4

**Fix**: Visually inspect Data sheet - year headers often in row 4, not row 21
```python
# WRONG if headers are in row 4
MATCH(H$10, Data!$H$21:$L$21, 0)

# CORRECT
MATCH(H$10, Data!$H$4:$L$4, 0)
```

### 5. Cross-Sheet Reference Errors

**Symptom**: `#REF!` when opening in Excel

**Cause**: Sheet name contains spaces but not quoted, or sheet doesn't exist

**Fix**: Quote sheet names with spaces: `'Data Sheet'!$A$1` or ensure sheet exists

## Debugging Workflow

1. **Isolate**: Pick ONE failing cell, extract its formula
2. **Deconstruct**: Split INDEX and MATCH calls, test each MATCH separately
3. **Verify data**: Load Data sheet with `data_only=True`, print actual values in referenced ranges
4. **Manual calc**: Compute expected result in Python, compare to formula structure
5. **Check types**: Ensure lookup values and range values have identical types

## Verification Snippet

```python
import openpyxl

wb = openpyxl.load_workbook(path, data_only=True)
ws = wb['Data']

# Check what's actually in the lookup range
print("Row keys (D21:D38):")
for r in range(21, 39):
    val = ws.cell(row=r, column=4).value
    print(f"  Row {r}: {repr(val)} (type: {type(val).__name__})")

print("\nColumn headers (H4:L4):")
for c in range(8, 13):  # H=8, L=12
    val = ws.cell(row=4, column=c).value
    print(f"  Col {chr(64+c)}: {repr(val)}")

print("\nData sample (H21:L21):")
for c in range(8, 13):
    val = ws.cell(row=21, column=c).value
    print(f"  {chr(64+c)}21: {repr(val)}")
```