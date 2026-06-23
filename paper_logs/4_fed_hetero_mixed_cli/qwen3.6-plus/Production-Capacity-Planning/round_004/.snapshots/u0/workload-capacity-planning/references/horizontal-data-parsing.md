# Parsing Horizontal/Transposed Excel Data

Use this pattern when Excel weeks are arranged as columns (left-to-right) rather than rows.

## Identifying Horizontal Layout

Signs in raw cell inspection:
```
Row 4: ['(1):Week', '(2):4', '(3):5', '(4):6', ...]
Row 5: ['(1):MIG weld Demand', '(2):49.85', '(3):14.44', '(4):15.98', ...]
```

Key indicators:
- Week numbers (4, 5, 6...) appear in column headers, not row values
- Data labels are in column 1 (e.g., "MIG weld Demand")
- Values extend horizontally across columns

## Parsing Pattern

```python
import openpyxl

wb = openpyxl.load_workbook('/path/to/file.xlsx')
ws = wb['SheetName']

# Find the header row (contains week numbers)
week_cols = {}
demand_row = None

for row in ws.iter_rows(min_row=1, max_row=10):
    for cell in row:
        if isinstance(cell.value, (int, float)) and 1 <= cell.value <= 52:
            week_cols[int(cell.value)] = cell.column
        elif isinstance(cell.value, str) and 'demand' in cell.value.lower():
            demand_row = cell.row

# Extract demand by week
week_demand = {}
if demand_row and week_cols:
    for week, col in week_cols.items():
        val = ws.cell(row=demand_row, column=col).value
        if val is not None:
            week_demand[week] = float(val)

print(f"Found {len(week_demand)} weeks of demand data")
print(f"Week range: {min(week_demand.keys())} to {max(week_demand.keys())}")
```

## Common Horizontal Layout Patterns

### Pattern 1: Multiple Header Rows
When weeks are split across multiple header rows (e.g., Row 4: weeks 4-18, Row 5: weeks 19-33...):

```python
# Collect all week mappings across multiple rows
week_cols = {}
for row_idx in range(4, 7):  # Check rows 4-6
    row = ws[row_idx]
    for cell in row:
        if isinstance(cell.value, (int, float)) and 1 <= cell.value <= 52:
            week_cols[int(cell.value)] = cell.column
```

### Pattern 2: Demand in Multiple Category Rows
When demand is split across rows (e.g., MIG weld, TIG weld) that need summation:

```python
demand_rows = []
for row in ws.iter_rows(min_row=1, max_row=10):
    for cell in row:
        if isinstance(cell.value, str) and 'demand' in cell.value.lower():
            demand_rows.append(cell.row)
            break

# Sum demands across categories
week_demand = {}
for week, col in week_cols.items():
    total = 0
    for row_idx in demand_rows:
        val = ws.cell(row=row_idx, column=col).value
        if val is not None:
            total += float(val)
    week_demand[week] = total
```

## Verification

After parsing, always verify:
- Week sequence has no gaps (`weeks == list(range(min(weeks), max(weeks)+1))`)
- Demand values are plausible (positive, reasonable magnitude)
- Total demand matches expected sum from task description

## Anti-Patterns

- **Don't** use `pd.read_excel()` without checking orientation—it assumes vertical layout
- **Don't** assume week 1 is in column B; find week numbers programmatically
- **Don't** ignore the 'Total' column often found at the end (column 51 or similar)
