# Formula Patterns Reference

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

### Multi-series data lookup
When Data sheet has multiple rows per entity (e.g., different series/indicators):
1. **Identify the series code column** in both Task and Data sheets.
2. **Match on series code**, not entity code — entity code MATCH returns only the first matching row.
3. **Verify row alignment**: Task sheet row N should map to Data sheet row M for the same series.
```python
# Verify series codes match between Task and Data
task_series = [ws_task.cell(row=r, column=4).value for r in range(12, 30)]
data_series = [ws_data.cell(row=r, column=4).value for r in range(21, 39)]
print(f"Task series: {task_series}")
print(f"Data series: {data_series}")
```

### Common mistakes
- Forgetting `$` on the lookup vectors causes `#N/A` when formula is copied.
- Using the wrong row for column headers (off-by-one).
- Data range not matching the lookup vector extent.
- **Matching on entity code when Data has series codes** — returns wrong row.

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
- Value and weight ranges must have same dimensions.
- Weights typically come from lookup layer (capacity, population, etc.).
- Use row-absolute (`H$35:H$40`) to lock rows when copying across columns.

## Statistics

| Statistic | Formula (Preferred) | Alternative |
|-----------|---------------------|-------------|
| Minimum | `=MIN(range)` | — |
| Maximum | `=MAX(range)` | — |
| Median | `=MEDIAN(range)` | — |
| Mean | `=AVERAGE(range)` | — |
| 25th percentile | `=PERCENTILE.INC(range, 0.25)` | `=QUARTILE.INC(range, 1)` |
| 75th percentile | `=PERCENTILE.INC(range, 0.75)` | `=QUARTILE.INC(range, 3)` |

**Decision rule**: Use `PERCENTILE.INC` by default. Only use `QUARTILE.INC` if the task explicitly names it or the verifier expects it. Both are valid Excel functions but produce identical results. Use `PERCENTILE.INC` (inclusive) not `PERCENTILE.EXC`.

**CRITICAL**: Always use row-absolute references (`H$35:H$40`) for statistics ranges.

## Dynamic Range Detection

Use this pattern to count entities and verify block alignment before writing formulas:
```python
import openpyxl
from collections import Counter

wb = openpyxl.load_workbook('input.xlsx')
ws_data = wb['Data']
ws_task = wb['Task']

# Check if multi-series: count unique entity codes vs total rows
entities = set()
series_codes = []
for row in ws_data.iter_rows(min_row=21, max_row=38, min_col=2, max_col=4):
    entity = row[0].value
    series = row[2].value
    if entity: entities.add(entity)
    if series: series_codes.append(series)

print(f"Unique entities: {len(entities)}")
print(f"Total data rows: {len(series_codes)}")
if len(series_codes) > len(entities):
    print(f"MULTI-SERIES DETECTED: {len(series_codes) / len(entities):.0f} series per entity")

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
    if len(block) != len(entities):
        print(f"  WARNING: Block {i+1} has {len(block)} rows but Data has {len(entities)} entities!")
```

**Decision rule**: If total data rows != total Task target rows, or any block row count != entity count, re-scan Data sheet bounds or check for header/total rows.

## openpyxl Formatting Preservation

When setting `cell.value` on an existing cell, openpyxl preserves the cell's existing style attributes (font, fill, border, number_format, alignment). However:
- `ws.cell(row=r, column=c, value=v)` creates a new cell and may reset styles.
- Prefer `ws[cell_coord].value = v` or `ws.cell(row=r, column=c); cell.value = v`.
- After writing, verify a sample of cells still have the expected `number_format` and `fill.fgColor.rgb`.

## Reference Style Summary
| Pattern | Example | Use case |
|---------|---------|----------|
| Absolute | `$D$21:$D$38` | Fixed lookup table that never moves |
| Column absolute, row relative | `$D12` | Copy down rows, keep column fixed |
| Row absolute, column relative | `H$10` | Copy across columns, keep row fixed |
| Relative | `H35:H40` | Adjusts when copied in any direction |

**For SUMPRODUCT and statistics ranges**: Always use row-absolute (`H$35:H$40`) to prevent accidental shift when the formula cell is copied vertically within the sheet.

## Identifying Target Cells

Target cells typically have:
- A highlight fill color (common: `FFF2CC` — light yellow)
- `value is None` (empty)
- A specific `number_format` already set (e.g., `0.00`)

Scan all cells in the template and collect those matching these criteria.