# Formula Templates for Rollforward Workbooks

## Complete Control Row Construction

```python
from openpyxl import Workbook
from openpyxl.utils import get_column_letter

def build_detail_sheet(wb, sheet_name, partners_data, gl_balances):
    """
    Build a detail sheet with correct control row formulas.
    
    partners_data: list of dicts with 'partner', 'beginning', monthly activity
    gl_balances: dict with keys 'jan', 'feb', 'mar', 'apr' for GL ending balances
    """
    ws = wb.create_sheet(sheet_name)
    
    # Headers (row 5)
    headers = ['Partner', 'Beginning Balance', 'Jan Adds', 'Jan Util', 'Jan Ending',
               'Feb Adds', 'Feb Util', 'Feb Ending',
               'Mar Adds', 'Mar Util', 'Mar Ending',
               'Apr Adds', 'Apr Util', 'Apr Ending', 'Reserve']
    for col, header in enumerate(headers, 1):
        ws.cell(row=5, column=col, value=header)
    
    # Data rows (rows 6+)
    data_start = 6
    for i, partner in enumerate(partners_data):
        row = data_start + i
        ws.cell(row=row, column=1, value=partner['name'])
        ws.cell(row=row, column=2, value=partner['beginning'])
        ws.cell(row=row, column=3, value=partner['jan_adds'])
        ws.cell(row=row, column=4, value=partner['jan_util'])
        # Month ending formulas (data rows)
        ws.cell(row=row, column=5, value=f'=B{row}+C{row}-D{row}')  # Jan End
        ws.cell(row=row, column=6, value=partner['feb_adds'])
        ws.cell(row=row, column=7, value=partner['feb_util'])
        ws.cell(row=row, column=8, value=f'=E{row}+F{row}-G{row}')  # Feb End
        ws.cell(row=row, column=9, value=partner['mar_adds'])
        ws.cell(row=row, column=10, value=partner['mar_util'])
        ws.cell(row=row, column=11, value=f'=H{row}+I{row}-J{row}')  # Mar End
        ws.cell(row=row, column=12, value=partner['apr_adds'])
        ws.cell(row=row, column=13, value=partner['apr_util'])
        ws.cell(row=row, column=14, value=f'=K{row}+L{row}-M{row}')  # Apr End
        ws.cell(row=row, column=15, value=f'=C{row}+F{row}+I{row}+L{row}')  # Reserve
    
    data_end = data_start + len(partners_data) - 1
    
    # Control rows
    pt_row = data_end + 1  # Period Totals
    eb_row = data_end + 2  # Ending Balance
    var_row = data_end + 3  # Variance
    gl_row = data_end + 4  # GL Balance
    
    # Period Totals
    ws.cell(row=pt_row, column=1, value='Period Totals')
    for col in range(2, 15):  # B through N
        col_letter = get_column_letter(col)
        ws.cell(row=pt_row, column=col, value=f'=SUM({col_letter}{data_start}:{col_letter}{data_end})')
    ws.cell(row=pt_row, column=15, value=f'=C{pt_row}+F{pt_row}+I{pt_row}+L{pt_row}')  # O: sum accruals
    
    # Ending Balance (reference Period Totals for activity)
    ws.cell(row=eb_row, column=1, value='Ending Balance')
    ws.cell(row=eb_row, column=5, value=f'=B{pt_row}+C{pt_row}-D{pt_row}')  # Jan: Beg + Acc - Util
    ws.cell(row=eb_row, column=8, value=f'=E{eb_row}+F{pt_row}-G{pt_row}')  # Feb: Jan End + Acc - Util
    ws.cell(row=eb_row, column=11, value=f'=H{eb_row}+I{pt_row}-J{pt_row}')  # Mar: Feb End + Acc - Util
    ws.cell(row=eb_row, column=14, value=f'=K{eb_row}+L{pt_row}-M{pt_row}')  # Apr: Mar End + Acc - Util
    ws.cell(row=eb_row, column=15, value=f'=E{eb_row}+H{eb_row}+K{eb_row}+N{eb_row}')  # Sum of endings
    
    # Variance - CRITICAL: Column N for both GL and EB
    ws.cell(row=var_row, column=1, value='Variance')
    ws.cell(row=var_row, column=15, value=f'=N{gl_row}-N{eb_row}')  # CORRECT: N - N
    
    # GL Balance - static values in E, H, K, N (monthly endings)
    ws.cell(row=gl_row, column=1, value='GL Balance')
    ws.cell(row=gl_row, column=5, value=gl_balances['jan'])  # E: Jan GL
    ws.cell(row=gl_row, column=8, value=gl_balances['feb'])  # H: Feb GL
    ws.cell(row=gl_row, column=11, value=gl_balances['mar'])  # K: Mar GL
    ws.cell(row=gl_row, column=14, value=gl_balances['apr'])  # N: Apr GL
    ws.cell(row=gl_row, column=15, value=f'=E{gl_row}+H{gl_row}+K{gl_row}+N{gl_row}')  # O: sum GL
    
    return ws, pt_row, eb_row, var_row, gl_row
```

## Cross-Sheet Summary Links (CRITICAL: COLUMN N FOR GL)

```python
def build_summary_sheet(wb, detail_sheets_info):
    """
    Build summary sheet linking to detail sheet control rows.
    
    detail_sheets_info: list of (sheet_name, pt_row, eb_row, var_row, gl_row)
    """
    ws = wb.create_sheet('Summary', 0)
    
    # Headers
    ws.cell(row=1, column=1, value='Account')
    ws.cell(row=1, column=2, value='Period Additions')
    ws.cell(row=1, column=3, value='Ending Balance')
    ws.cell(row=1, column=4, value='GL Balance')
    ws.cell(row=1, column=5, value='Variance')
    
    for i, (sheet_name, pt_row, eb_row, var_row, gl_row) in enumerate(detail_sheets_info, 2):
        ws.cell(row=i, column=1, value=sheet_name)
        # Wrap sheet name in single quotes for cross-sheet references
        ws.cell(row=i, column=2, value=f"='{sheet_name}'!O{pt_row}")   # Period Totals - column O
        ws.cell(row=i, column=3, value=f"='{sheet_name}'!O{eb_row}")   # Ending Balance - column O
        # CRITICAL: GL Balance is in column N in detail sheet, not O!
        ws.cell(row=i, column=4, value=f"='{sheet_name}'!N{gl_row}")   # GL Balance - column N
        ws.cell(row=i, column=5, value=f"='{sheet_name}'!O{var_row}")  # Variance - column O
```

## Common Column Reference Summary

| What | Detail Sheet Column | Summary Sheet Link |
|------|---------------------|-------------------|
| Period Totals Reserve | O | `='Sheet'!O{pt_row}` |
| Ending Balance Reserve | O | `='Sheet'!O{eb_row}` |
| **GL Balance** | **N** (E,H,K,N for months) | **`='Sheet'!N{gl_row}`** |
| Variance | O | `='Sheet'!O{var_row}` |

## Formula Verification Script

```python
def verify_variance_formula(workbook_path):
    """Verify that Variance formula uses column N for GL Balance."""
    from openpyxl import load_workbook
    wb = load_workbook(workbook_path, data_only=False)
    
    errors = []
    for sheet_name in wb.sheetnames:
        if 'Summary' in sheet_name:
            continue
        ws = wb[sheet_name]
        # Find Variance row
        for row in range(1, ws.max_row + 1):
            if ws.cell(row=row, column=1).value == 'Variance':
                formula = ws.cell(row=row, column=15).value  # Column O
                if formula and isinstance(formula, str):
                    # Check that it references column N for GL, not O
                    if 'O' in formula and '-N' in formula:
                        # Pattern like =O12-N12 is WRONG
                        errors.append(f"{sheet_name} row {row}: WRONG Variance formula '{formula}' - uses column O for GL")
                    elif 'N' in formula and formula.count('N') >= 2:
                        # Pattern like =N12-N10 is CORRECT
                        pass
                    else:
                        errors.append(f"{sheet_name} row {row}: Unexpected Variance formula '{formula}'")
    
    if errors:
        print("VARIANCE FORMULA ERRORS:")
        for e in errors:
            print(f"  {e}")
        return False
    print("OK: All Variance formulas use column N correctly")
    return True


def verify_summary_gl_links(workbook_path):
    """Verify Summary sheet GL Balance links use column N."""
    from openpyxl import load_workbook
    wb = load_workbook(workbook_path, data_only=False)
    
    if 'Summary' not in wb.sheetnames:
        print("No Summary sheet found")
        return False
    
    ws = wb['Summary']
    errors = []
    
    for row in range(1, ws.max_row + 1):
        label = ws.cell(row=row, column=1).value
        if label and isinstance(label, str) and 'GL' in label.upper() and 'Balance' in label:
            formula = ws.cell(row=row, column=2).value
            if formula and isinstance(formula, str):
                if '!O' in formula:
                    errors.append(f"Summary row {row}: WRONG - GL Balance uses column O '{formula}' (should be N)")
                elif '!N' not in formula:
                    errors.append(f"Summary row {row}: Missing column N in '{formula}'")
    
    if errors:
        print("SUMMARY GL LINK ERRORS:")
        for e in errors:
            print(f"  {e}")
        return False
    print("OK: All Summary GL Balance links use column N correctly")
    return True
```

## Common Mistakes

| Wrong | Right | Explanation |
|-------|-------|-------------|
| `=O12-N12` | `=N{gl_row}-N{eb_row}` | GL Balance is in column N, not O |
| `='Sheet'!O{gl_row}` | `='Sheet'!N{gl_row}` | Summary GL link must use column N |
| `=E10+E{pt_row}-D{pt_row}` | `=B{pt_row}+C{pt_row}-D{pt_row}` | EB Beginning must reference Period Totals, not self |
| `=Sheet!A1` | `='Sheet Name'!A1` | Sheet names with spaces need single quotes |
| `B6:8` | `B6:B8` | Range must include both column letters |
