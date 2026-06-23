# Excel Formula Patterns Reference

## INDEX/MATCH Two-Dimensional Lookup

Lookup by row key and column header:
```excel
=INDEX(Data!$H$21:$L$38,MATCH($D12,Data!$D$21:$D$38,0),MATCH(H$10,Data!$H$4:$L$4,0))
```

### Reference locking rules

| Part | Example | Locking | Why |
|------|---------|---------|-----|
| Data range | `$H$21:$L$38` | Fully absolute | Same source for every cell |
| Row lookup vector | `$D$21:$D$38` | Fully absolute | Same column for every cell |
| Col lookup vector | `$H$4:$L$4` | Fully absolute | Same row for every cell |
| Row key column | `$D12` | Column absolute | Same column, varying row |
| Col key row | `H$10` | Row absolute | Same row, varying column |

### Python generation

```python
import openpyxl
from openpyxl.utils import get_column_letter

def index_match_formula(row_num, col_num, data_range, row_key_col, col_header_row):
    """Generate INDEX/MATCH formula for 2D lookup."""
    col_letter = get_column_letter(col_num)
    return f"=INDEX(Data!{data_range},MATCH(${row_key_col}{row_num},Data!${row_key_col}$21:${row_key_col}$38,0),MATCH({col_letter}${col_header_row},Data!${get_column_letter(8)}$4:${get_column_letter(12)}$4,0))"
```

### Common mistakes

- Forgetting `$` on lookup vectors causes `#N/A` when formula is copied
- Using wrong row for column headers (off-by-one)
- Data range extent not matching lookup vector extent

## Derived Calculations

### Percentage / Gap formulas

```excel
=(H12-H19)/H26*100
```

**Critical**: Verify operand order against task description. Key heuristics:

| Task wording | Likely formula |
|--------------|----------------|
| "gap from X to Y" | `Y - X` |
| "difference between X and Y" | Check sign context |
| "percentage of X relative to Y" | `X / Y * 100` |
| "success rate" | `success / total` |

When uncertain, compute both interpretations and check which matches sample data or expected sign.

### Weighted mean

```excel
=SUMPRODUCT(H$35:H$40,H$26:H$31)/SUM(H$26:H$31)
```

**CRITICAL**: Use row-absolute (`$`) for ranges in SUMPRODUCT.
- Value and weight ranges must have same dimensions
- Weights typically come from lookup layer (capacity, population, etc.)
- Use row-absolute (`H$35:H$40`) to lock rows when copying across columns

## Statistics

| Statistic | Formula |
|-----------|---------|
| Minimum | `=MIN(range)` |
| Maximum | `=MAX(range)` |
| Median | `=MEDIAN(range)` |
| Mean | `=AVERAGE(range)` |
| 25th percentile | `=PERCENTILE.INC(range, 0.25)` |
| 75th percentile | `=PERCENTILE.INC(range, 0.75)` |

Note: Use `PERCENTILE.INC` (inclusive) for standard statistical summaries.

## Dynamic Range Detection

Use this pattern to count entities and verify block alignment before writing formulas:

```python
import openpyxl
from collections import Counter

wb = openpyxl.load_workbook('input.xlsx')
ws_data = wb['Data']
ws_task = wb['Task']

# Count unique entities in Data sheet (adjust column/rows as needed)
entities = []
for row in ws_data.iter_rows(min_row=21, max_row=38, min_col=2, max_col=2):
    val = row[0].value
    if val:
        entities.append(val)
entity_count = len(set(entities))
print(f"Data sheet entities: {entity_count} unique")

# Count highlighted empty cells per block in Task sheet
highlight_counts = Counter()
for row in ws_task.iter_rows(min_row=1, max_row=ws_task.max_row, max_col=ws_task.max_column):
    for c in row:
        if c.fill and c.fill.fgColor and 'FFF2CC' in str(c.fill.fgColor.rgb) and c.value is None:
            highlight_counts[c.row] += 1

# Group consecutive rows into blocks
blocks = []
current_block = []
for r in sorted(highlight_counts.keys()):
    if not current_block or r == current_block[-1] + 1:
        current_block.append(r)
    else:
        blocks.append(current_block)
        current_block = [r]
if current_block:
    blocks.append(current_block)

print(f"Task sheet blocks: {len(blocks)}")
for i, block in enumerate(blocks):
    print(f"  Block {i+1}: rows {block[0]}-{block[-1]} ({len(block)} rows)")
    if len(block) != entity_count:
        print(f"  WARNING: Block {i+1} has {len(block)} rows but Data has {entity_count} entities!")
```

**Decision rule**: If any block row count != entity count, re-scan Data sheet bounds or check for header/total rows in Task sheet before proceeding.

## openpyxl Formatting Preservation

When setting `cell.value` on an existing cell, openpyxl preserves the cell's existing style attributes (font, fill, border, number_format, alignment). However:
- `ws.cell(row=r, column=c, value=v)` creates a new cell and may reset styles
- Prefer `ws[cell_coord].value = v` or get the cell first, then set `.value`
- After writing, verify a sample of cells still have the expected `number_format` and `fill.fgColor.rgb`

## Reference Style Summary

| Pattern | Example | Use case |
|---------|---------|----------|
| Absolute | `$D$21:$D$38` | Fixed lookup table that never moves |
| Column absolute, row relative | `$D12` | Copy down rows, keep column fixed |
| Row absolute, column relative | `H$10` | Copy across columns, keep row fixed |
| Relative | `H35:H40` | Adjusts when copied in any direction |

**For SUMPRODUCT and statistics ranges**: Always use row-absolute (`H$35:H$40`) to prevent accidental shift when the formula cell is copied vertically within the sheet.
