# Excel Formula Patterns

## INDEX/MATCH Cross-Sheet Lookup
Use when mapping a 2D grid (rows keyed by one column, columns keyed by a header row).
```excel
=INDEX(SourceSheet!$DataRange,MATCH(RowKeyCell,SourceSheet!$RowKeyRange,0),MATCH(ColKeyCell,SourceSheet!$ColKeyRange,0))
```
- Lock the data range and key ranges with `$`.
- Leave the key cells relative so they adjust when copied.
- **Note**: `openpyxl` strips spaces after commas. Write without spaces to match strict verifiers.

## Weighted Mean
```excel
=SUMPRODUCT(ValueRange,WeightRange)/SUM(WeightRange)
```
- Lock ranges with `$` if applying across multiple columns.

## Percentile & Statistics
- `PERCENTILE(range,0.25)` for Q1, `0.75` for Q3.
- `MEDIAN(range)`, `AVERAGE(range)`, `MIN(range)`, `MAX(range)`.

## openpyxl Implementation Tips
```python
import openpyxl
wb = openpyxl.load_workbook('input.xlsx')
ws = wb['Task']
ws['H12'] = '=INDEX(Data!$H$21:$L$38,MATCH(Task!D12,Data!$D$21:$D$38,0),MATCH(Task!H$10,Data!$H$20:$L$20,0))'
wb.save('output.xlsx')
```
- Always use `data_only=False` (default) when writing formulas.
- Verify with `data_only=True` only after Excel has calculated the file, or use manual value checks.
- `openpyxl` expects US locale syntax (commas for argument separators, periods for decimals).
- `openpyxl` normalizes formulas by removing spaces after commas. Do not rely on exact string matches if you include spaces.

## Python Value Verification Snippet
Since `openpyxl` does not evaluate formulas, use this pattern to verify logical correctness:
```python
import openpyxl

wb = openpyxl.load_workbook('input.xlsx', data_only=False)
data_ws = wb['Data']
task_ws = wb['Task']

# Example: Verify H12 lookup manually
row_key = task_ws['D12'].value
col_key = task_ws['H10'].value

# Find row index in Data sheet
row_idx = None
for r in range(21, 39):
    if data_ws.cell(row=r, column=4).value == row_key:
        row_idx = r
        break

# Find col index in Data sheet
col_idx = None
for c in range(8, 13):
    if data_ws.cell(row=4, column=c).value == col_key:
        col_idx = c
        break

expected = data_ws.cell(row=row_idx, column=col_idx).value
print(f"Expected: {expected}")
```