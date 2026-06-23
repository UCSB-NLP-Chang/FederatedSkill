# Control Row Formula Templates

## Row Positions (calculated dynamically)
```
last_data_row = first_data_row + len(line_items) - 1
totals_row = last_data_row + 1
ending_row = last_data_row + 2
variance_row = last_data_row + 3
gl_row = last_data_row + 4
```

## Period Totals Row Formulas

| Column | Formula |
|---------|---------|
| B (Beg) | `=SUM(B{first}:B{last})` |
| C-D | `=SUM(C{first}:C{last})` |
| E-N | Similar SUM formulas |
| O (Reserve) | `=C{totals}+F{totals}+I{totals}+L{totals}` |

## Ending Balance Row Formulas

| Column | Formula | Notes |
|---------|---------|-------|
| E (Jul End) | `=B{totals}+C{totals}-D{totals}` | Beg from Period Totals |
| H (Aug End) | `=E{ending}+F{totals}-G{totals}` | Prior Ending + activity |
| K (Sep End) | `=H{ending}+I{totals}-J{totals}` | Prior Ending + activity |
| N (Oct End) | `=K{ending}+L{totals}-M{totals}` | Prior Ending + activity |
| O (Reserve) | `=D{ending}+G{ending}+J{ending}+M{ending}` | Sum of utilizations |

**CRITICAL**: Ending Balance E column must reference `B{totals_row}` (Period Totals), NOT `B{ending_row}` (self).

## Variance Row Formula (MOST CRITICAL)

```
O{variance} = =N{gl_row}-N{ending_row}
```

**CORRECT**: Both operands use column N (Oct Ending column).
**WRONG**: `=O{gl_row}-N{ending_row}` - GL Balance values are in columns E/H/K/N, NOT column O.

## GL Balance Row

Static values from JSON:
- E{gl_row} = Jul GL value
- H{gl_row} = Aug GL value
- K{gl_row} = Sep GL value
- N{gl_row} = Oct GL value
- O{gl_row} = `=O{totals}-O{ending}`

## Python Implementation

```python
from openpyxl import Workbook

wb = Workbook()
ws = wb.active

# Data rows
first_row = 6
for i, item in enumerate(items):
    row = first_row + i
    ws[f'E{row}'] = f'=B{row}+C{row}-D{row}'
    ws[f'H{row}'] = f'=E{row}+F{row}-G{row}'
    ws[f'K{row}'] = f'=H{row}+I{row}-J{row}'
    ws[f'N{row}'] = f'=K{row}+L{row}-M{row}'

last_row = first_row + len(items) - 1
totals = last_row + 1
ending = last_row + 2
variance = last_row + 3
gl = last_row + 4

# Period Totals
for col in 'BCDEFGHIJKLMN':
    ws[f'{col}{totals}'] = f'=SUM({col}{first_row}:{col}{last_row})'
ws[f'O{totals}'] = f'=C{totals}+F{totals}+I{totals}+L{totals}'

# Ending Balance
ws[f'E{ending}'] = f'=B{totals}+C{totals}-D{totals}'
ws[f'H{ending}'] = f'=E{ending}+F{totals}-G{totals}'
ws[f'K{ending}'] = f'=H{ending}+I{totals}-J{totals}'
ws[f'N{ending}'] = f'=K{ending}+L{totals}-M{totals}'
ws[f'O{ending}'] = f'=D{ending}+G{ending}+J{ending}+M{ending}'

# Variance - CRITICAL: use column N for GL
ws[f'O{variance}'] = f'=N{gl}-N{ending}'

# GL Balance
ws[f'E{gl}'] = gl_json.get('jul', 0)
ws[f'H{gl}'] = gl_json.get('aug', 0)
ws[f'K{gl}'] = gl_json.get('sep', 0)
ws[f'N{gl}'] = gl_json.get('oct', 0)
ws[f'O{gl}'] = f'=O{totals}-O{ending}'
```
