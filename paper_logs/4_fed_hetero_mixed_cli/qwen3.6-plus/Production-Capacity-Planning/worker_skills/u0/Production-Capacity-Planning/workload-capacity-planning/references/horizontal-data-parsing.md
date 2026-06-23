# Parsing Horizontal/Transposed Data

Use this pattern when data weeks are arranged as columns (left-to-right) rather than rows. This applies to both Excel and CSV formats.

## Identifying Horizontal Layout

**Excel signs in raw cell inspection**:
```
Row 4: ['(1):Week', '(2):4', '(3):5', '(4):6', ...]
Row 5: ['(1):MIG weld Demand', '(2):49.85', '(3):14.44', '(4):15.98', ...]
```

**CSV signs in raw file content**:
```
Row 0: ['Week', '5', '6', '7', '8', '9', '10', ...]
Row 1: ['Demand', '164.51', '155.93', '154.0', '141.99', ...]
```

Key indicators:
- Week numbers (4, 5, 6...) appear in column headers, not row values
- Data labels are in column 1 (e.g., "Demand", "MIG weld Demand")
- Values extend horizontally across many columns

## Parsing Pattern: Excel

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

## Parsing Pattern: CSV

```python
import csv

with open('/path/to/file.csv', 'r') as f:
    reader = csv.reader(f)
    rows = list(reader)

# First row contains week numbers (skip first column which is label)
week_cols = {}
for col_idx, val in enumerate(rows[0][1:], start=1):  # Skip 'Week' label
    try:
        week_num = int(float(val))
        if 1 <= week_num <= 53:
            week_cols[week_num] = col_idx  # Store 0-based column index
    except (ValueError, TypeError):
        continue

# Find demand row (look for 'Demand' in first column)
demand_row_idx = None
for row_idx, row in enumerate(rows):
    if row and 'demand' in str(row[0]).lower():
        demand_row_idx = row_idx
        break

# Extract demand by week
week_demand = {}
if demand_row_idx is not None:
    for week, col_idx in week_cols.items():
        val = rows[demand_row_idx][col_idx]
        if val:
            week_demand[week] = float(val)

print(f"Found {len(week_demand)} weeks of demand data")
print(f"Week range: {min(week_demand.keys())} to {max(week_demand.keys())}")
```

## Common Horizontal Layout Patterns

### Pattern 1: Multiple Header Rows (Excel)
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

### Pattern 3: CSV with Metadata Headers
When CSV has title rows before the data:

```python
with open('input.csv', 'r') as f:
    rows = list(csv.reader(f))

# Skip until we find the row with 'Week' in first column
header_idx = next(i for i, row in enumerate(rows) if row and row[0].lower() == 'week')
headers = rows[header_idx]
values = rows[header_idx + 1]

# Parse as normal...
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
- **Don't** assume CSV uses the same parsing code as Excel; use csv module for CSV files
- **Don't** assume CSV is vertical; check column count first
