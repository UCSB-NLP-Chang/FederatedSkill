# Formula Patterns Reference

## INDEX/MATCH Two-Dimensional Lookup

Lookup by row key and column header:
```excel
=INDEX(DataRange, MATCH(RowKey, KeyColumn, 0), MATCH(ColHeader, HeaderRow, 0))
```

### Reference locking rules
| Part | Locking | Why |
|------|---------|-----|
| data_range | Fully absolute `$H$21:$L$38` | Same source for every cell |
| row_lookup_vector | Fully absolute `$D$21:$D$38` | Same column for every cell |
| col_lookup_vector | Fully absolute `$H$4:$L$4` | Same row for every cell |
| row_key column | Column-absolute `$D12` | Same column, varying row |
| col_key row | Row-absolute `H$10` | Same row, varying column |

### Python generation
```python
def index_match_formula(row_key_cell, col_header_cell, data_range, key_col, header_row):
    return f"=INDEX({data_range},MATCH({row_key_cell},{key_col},0),MATCH({col_header_cell},{header_row},0))"
```

### Common mistakes
- Forgetting `$` on the lookup vectors causes #N/A when formula is copied
- Using the wrong row for column headers (off-by-one)
- Data range not matching the lookup vector extent

## Derived Calculations

### Percentage / Gap formulas
```excel
=(numerator_cell - denominator_cell) / divisor_cell * 100
```

**Critical**: Verify operand order against task description. If the task says "gap between X and Y", determine whether it means X−Y or Y−X. Look for contextual clues like expected sign or sample values.

### Weighted mean
```excel
=SUMPRODUCT(values_range, weights_range) / SUM(weights_range)
```
- ValueRange and WeightRange must have same dimensions
- Weights typically come from lookup layer (capacity, population, etc.)

## Statistics

| Statistic | Formula |
|-----------|---------|
| Minimum | `=MIN(range)` |
| Maximum | `=MAX(range)` |
| Median | `=MEDIAN(range)` |
| Mean | `=AVERAGE(range)` |
| 25th percentile | `=PERCENTILE.INC(range, 0.25)` |
| 75th percentile | `=PERCENTILE.INC(range, 0.75)` |

Use `PERCENTILE.INC` (inclusive) not `PERCENTILE.EXC`.

## openpyxl Formatting Preservation

When setting `cell.value` on an existing cell, openpyxl preserves the cell's existing style attributes (font, fill, border, number_format, alignment). However:
- `ws.cell(row=r, column=c, value=v)` creates a new cell and may reset styles
- Prefer `ws[cell_coord].value = v` or `ws.cell(row=r, column=c); cell.value = v`
- After writing, verify a sample of cells still have the expected `number_format` and `fill.fgColor.rgb`

## Identifying Target Cells

Target cells typically have:
- A highlight fill color (common: `FFF2CC` — light yellow)
- `value is None` (empty)
- A specific `number_format` already set (e.g., `0.00`)

Scan all cells in the template and collect those matching these criteria.
