# Excel Formula Patterns Reference

## INDEX/MATCH Two-Dimensional Lookup

The standard pattern for pulling data from a source grid by row key and column header:

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
=SUMPRODUCT(H35:H40,H26:H31)/SUM(H26:H31)
```

Requirements:
- Value and weight ranges must have same dimensions
- Weights typically come from lookup layer (capacity, population, etc.)
- Use row-absolute references for ranges that copy across columns: `H$35:H$40`

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

## openpyxl Formatting Preservation

When setting `cell.value` on an existing cell, openpyxl preserves the cell's existing style attributes:

```python
# Correct: preserves formatting
cell = ws['H12']
cell.value = "=SUM(H5:H10)"

# Avoid: may reset styles
ws.cell(row=12, column=8, value="=SUM(H5:H10)")
```

After writing, verify a sample of cells still have expected `number_format` and `fill.fgColor.rgb`.

## Reference Style Summary

| Pattern | Example | Use case |
|---------|---------|----------|
| Absolute | `$D$21:$D$38` | Fixed lookup table that never moves |
| Column absolute, row relative | `$D12` | Copy down rows, keep column fixed |
| Row absolute, column relative | `H$10` | Copy across columns, keep row fixed |
| Relative | `H35:H40` | Adjusts when copied in any direction |
