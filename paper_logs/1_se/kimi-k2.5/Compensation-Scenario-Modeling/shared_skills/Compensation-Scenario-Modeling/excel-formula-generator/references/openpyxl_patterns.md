# openpyxl Patterns and Pitfalls

## Reading Binary Excel Files

Excel files (.xlsx) are ZIP archives of XML files - they cannot be read with text tools.

```python
import openpyxl

# Correct way to inspect structure
wb = openpyxl.load_workbook('file.xlsx')
print("Sheets:", wb.sheetnames)

# Read all values from a sheet
for row in ws.iter_rows(values_only=True):
    print(row)
```

## Formula Storage with Escape Handling

Formulas are stored as strings starting with `=`. openpyxl does not evaluate them.

```python
# WRONG - escape sequence warning
formula = f"=SUM(Assumptions!\$C\$21:\$C\$30)"

# CORRECT - raw f-string
formula = rf"=SUM(Assumptions!$C$21:$C$30)"

# Set a formula
cell.value = "=SUM(A1:A10)"

# Read a formula (returns string, not result)
print(cell.value)  # "=SUM(A1:A10)"
```

## Named Ranges

```python
from openpyxl.workbook.defined_name import DefinedName

# Create named range
wb.defined_names.add(DefinedName('MWS', attr_text='Assumptions!\$B\$5'))

# Reference in formula
cell.value = "=MWS*0.2"
```

## Worksheet Order Control

```python
# Sheet order matters for cross-sheet references
# Move sheet to specific position
wb.move_sheet('Summary', offset=-999)  # Move to first
wb.move_sheet('Assumptions', offset=-999)

# Verify order
print([s.title for s in wb._sheets])
```

## Layout Planning for Totals

```python
# Calculate positions dynamically
HEADER_ROWS = 3
DATA_COUNT = 103
TOTAL_ROW = HEADER_ROWS + DATA_COUNT + 1  # 107

# Place totals formula
ws.cell(row=TOTAL_ROW, column=5, value=f"=SUM(E{HEADER_ROWS+1}:E{TOTAL_ROW-1})")

# Update summary links when positions change
summary_cell.value = f"='EE Calcs Current'!E{TOTAL_ROW}"
```

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `BadZipFile` | File is .xls (Excel 97-2003) or corrupted | Use `xlrd` for .xls files |
| `KeyError: 'Sheet'` | Sheet name doesn't exist | Check `wb.sheetnames` first |
| Formula shows as text | Cell formatted as text | Set `cell.data_type = 'f'` or ensure value starts with `=` |
| `#REF!` in Excel | Named range or sheet reference broken | Verify named ranges created before formulas |
| `SyntaxWarning: invalid escape sequence '\$'` | Backslash in cell reference | Use raw f-strings: `rf"..."` |

## Performance Tips

- Use `ws.iter_rows()` instead of `ws.rows` for large sheets
- Set `read_only=True` when only reading: `load_workbook(path, read_only=True)`
- Use `write_only=True` for very large output files
- Batch cell operations rather than individual writes