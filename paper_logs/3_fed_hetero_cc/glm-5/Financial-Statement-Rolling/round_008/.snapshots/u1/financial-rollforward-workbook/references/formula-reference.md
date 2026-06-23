# Formula Reference for Rollforward Workbooks

## Complete Control Row Templates

Assuming:
- Data rows: 6 to `last_data_row`
- Period Totals row: `pt_row` = `last_data_row + 1`
- Ending Balance row: `eb_row` = `pt_row + 1`
- Variance row: `var_row` = `eb_row + 1`
- GL Balance row: `gl_row` = `var_row + 1`

### Period Totals Row

```python
def write_period_totals(ws, first_row, last_row, pt_row):
    """Write SUM formulas for each column."""
    columns = ['B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N']
    for col in columns:
        ws[f'{col}{pt_row}'] = f'=SUM({col}{first_row}:{col}{last_row})'

    # Reserve column: sum of period accruals (C, F, I, L)
    ws[f'O{pt_row}'] = f'=C{pt_row}+F{pt_row}+I{pt_row}+L{pt_row}'

    # Label
    ws[f'A{pt_row}'] = 'Period Totals'
```

### Ending Balance Row (CRITICAL)

```python
def write_ending_balance(ws, pt_row, eb_row):
    """Write Ending Balance formulas - MUST reference Period Totals for beginning."""

    # First period: references Period Totals for Beginning Balance (B)
    # RIGHT: =B{pt_row}+C{pt_row}-D{pt_row}
    ws[f'E{eb_row}'] = f'=B{pt_row}+C{pt_row}-D{pt_row}'

    # Subsequent periods: reference prior period's Ending Balance
    ws[f'H{eb_row}'] = f'=E{eb_row}+F{pt_row}-G{pt_row}'
    ws[f'K{eb_row}'] = f'=H{eb_row}+I{pt_row}-J{pt_row}'
    ws[f'N{eb_row}'] = f'=K{eb_row}+L{pt_row}-M{pt_row}'

    # Reserve: sum of period endings
    ws[f'O{eb_row}'] = f'=E{eb_row}+H{eb_row}+K{eb_row}+N{eb_row}'

    # Label
    ws[f'A{eb_row}'] = 'Ending Balance'

    # WRONG PATTERN (do not use):
    # ws[f'E{eb_row}'] = f'=B{eb_row}+C{eb_row}-D{eb_row}'  # WRONG! Self-referencing
```

### Variance Row (CRITICAL - Most Common Bug)

```python
def write_variance(ws, eb_row, var_row, gl_row):
    """Write Variance formula - MUST use column N for BOTH values.

    CORRECT: Variance = N(GL_row) - N(Ending_Balance_row)
    WRONG:   Variance = O(GL_row) - N(Ending_Balance_row)  <- Common mistake!
    """

    # RIGHT: column N for both GL and Ending Balance
    ws[f'N{var_row}'] = f'=N{gl_row}-N{eb_row}'

    # Also for Reserve column
    ws[f'O{var_row}'] = f'=O{gl_row}-O{eb_row}'

    # Label
    ws[f'A{var_row}'] = 'Variance'

    # WRONG PATTERNS (do not use):
    # ws[f'N{var_row}'] = f'=O{gl_row}-N{eb_row}'  # WRONG! GL is in N, not O
    # ws[f'N{var_row}'] = f'=O{gl_row}-O{eb_row}'  # WRONG! Both wrong column
```

### GL Balance Row

```python
def write_gl_balance(ws, gl_row, gl_data):
    """Write GL Balance values from JSON source."""

    # Static values (not formulas)
    ws['E12'] = gl_data['jul']
    ws['H12'] = gl_data['aug']
    ws['K12'] = gl_data['sep']
    ws['N12'] = gl_data['oct']

    # Reserve: Period Totals - Ending Balance
    pt_row = gl_row - 3
    eb_row = gl_row - 1
    ws[f'O{gl_row}'] = f'=O{pt_row}-O{eb_row}'

    # Label
    ws[f'A{gl_row}'] = 'GL Balance'
```

### Data Row Formulas

```python
def write_data_row(ws, row):
    """Write cascading balance formulas for a single data row."""

    # Period 1 Ending: Beg + Accruals - Utilization
    ws[f'E{row}'] = f'=B{row}+C{row}-D{row}'

    # Period 2 Ending: Period 1 End + Accruals - Utilization
    ws[f'H{row}'] = f'=E{row}+F{row}-G{row}'

    # Period 3 Ending: Period 2 End + Accruals - Utilization
    ws[f'K{row}'] = f'=H{row}+I{row}-J{row}'

    # Period 4 Ending: Period 3 End + Accruals - Utilization
    ws[f'N{row}'] = f'=K{row}+L{row}-M{row}'

    # Reserve: sum of period accruals
    ws[f'O{row}'] = f'=C{row}+F{row}+I{row}+L{row}'
```

## Cross-Sheet Summary Links

```python
def write_summary_links(summary, detail_sheets, gl_row=12, eb_row=10):
    """Link summary cells to detail sheet control rows."""

    for sheet_name, cells in detail_sheets.items():
        # Use single quotes for sheet names with spaces/special chars
        safe_name = f"'{sheet_name}'"

        # Period Additions (O column, Period Totals row)
        summary[f'B{cells["additions"]}'] = f"={safe_name}!O{gl_row-3}"

        # Ending Balance (O column, Ending Balance row)
        summary[f'B{cells["ending"]}'] = f"={safe_name}!O{eb_row}"

        # GL Balance (O column, GL Balance row)
        summary[f'B{cells["gl"]}'] = f"={safe_name}!O{gl_row}"

        # Variance (N column, Variance row)
        summary[f'B{cells["variance"]}'] = f"={safe_name}!N{gl_row-1}"
```

## Common Formula Errors and Fixes

| Error Pattern | Description | Correct Pattern |
|---------------|-------------|-----------------|
| `=O12-N10` | GL from column O instead of N | `=N12-N10` |
| `=B10+C10-D10` | Ending Balance self-reference | `=B9+C9-D9` |
| `=SUM(B6:8)` | Missing column in range | `=SUM(B6:B8)` |
| `=Sheet!A1` | Unquoted sheet name | `='Sheet Name'!A1` |
| `=B6+B7+B8` | Manual sum instead of SUM() | `=SUM(B6:B8)` |
