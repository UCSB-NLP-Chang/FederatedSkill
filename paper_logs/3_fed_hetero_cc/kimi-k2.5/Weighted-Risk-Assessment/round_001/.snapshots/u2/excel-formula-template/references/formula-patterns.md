# Excel Formula Patterns Reference

## INDEX+MATCH Two-Dimensional Lookup

The most common pattern for pulling data from a source grid:

```
=INDEX(data_range, MATCH(row_key, row_lookup_vector, 0), MATCH(col_key, col_lookup_vector, 0))
```

### Reference locking rules

| Part | Locking | Why |
|------|---------|-----|
| data_range | Fully absolute `$H$21:$L$38` | Same source for every cell |
| row_lookup_vector | Fully absolute `$D$21:$D$38` | Same column for every cell |
| col_lookup_vector | Fully absolute `$H$4:$L$4` | Same row for every cell |
| row_key column | Column-absolute `$D12` | Same column, varying row |
| col_key row | Row-absolute `H$10` | Same row, varying column |

### Common mistakes

- Forgetting `$` on the lookup vectors causes #N/A when formula is copied
- Using the wrong row for column headers (off-by-one)
- Data range not matching the lookup vector extent

## Derived Calculations

### Percentage / Gap formulas

```
=(numerator_cell - denominator_cell) / divisor_cell * 100
```

**Critical**: Verify operand order against task description. If the task says
"gap between X and Y", determine whether it means X-Y or Y-X. Look for
contextual clues like expected sign or sample values. When ambiguous, compute
both orderings and check which matches sample data sign.

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

## Weighted Mean

```
=SUMPRODUCT(values_range, weights_range) / SUM(weights_range)
```

- ValueRange and WeightRange must have same dimensions
- Use absolute references for ranges: `H$35:H$40`

## openpyxl Formatting Preservation

When setting `cell.value` on an existing cell, openpyxl preserves style
attributes. However:

- `ws.cell(row=r, column=c, value=v)` creates a new cell and may reset styles
- Prefer `ws[cell_coord].value = v` or `ws.cell(row=r, column=c); cell.value = v`
- After writing, verify a sample of cells still have expected `number_format`

## Identifying Target Cells

Target cells typically have:
- A highlight fill color (common: `00FFF2CC` — light yellow)
- `value is None` (empty)
- A specific `number_format` already set (e.g., `0.00`)
