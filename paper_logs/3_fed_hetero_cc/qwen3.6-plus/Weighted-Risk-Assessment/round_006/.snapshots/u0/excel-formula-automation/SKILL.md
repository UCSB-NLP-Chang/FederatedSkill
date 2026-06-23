---
name: excel-formula-automation
description: Automate Excel formula injection with openpyxl. Use when tasks require writing Excel formulas programmatically, performing INDEX/MATCH lookups, statistical aggregations, weighted calculations, or cross-sheet references while preserving formatting.
---

# Excel Formula Automation

## Workflow
1. **Load and inspect**: `python3 scripts/validate_references.py --inspect <path>` to view structure.
2. **Map layout**: Identify header row (usually row 4), key columns, and data ranges.
3. **Build formulas**: Use templates with correct `$` locking (see references/locking-patterns.md).
4. **Inject formulas**: Set `cell.value = "=FORMULA"` — never use `data_only=True` for writing.
5. **Validate blocking**: Run `python3 scripts/validate_references.py <path>` — exits with error if `$` signs missing.
6. **Save and verify**: Save, reload, count formula cells.

## Critical: Reference Locking
**All workers fail on this in R2–R5.** See references/locking-patterns.md for the explicit table. Summary:

| Context | Pattern | Example |
|---------|---------|---------|
| INDEX/MATCH lookup range | Fully absolute | `$D$21:$D$38` |
| INDEX/MATCH row key | Column-absolute | `$D12` |
| Statistics range (MIN/MAX/MEDIAN) | Row-absolute | `H$35:H$40` |
| SUMPRODUCT values range | Row-absolute | `H$35:H$40` |
| SUMPRODUCT weights range | Row-absolute | `H$26:H$31` |
| Year header MATCH | Row-absolute | `H$10` |

## Output precision
Never round, truncate, or fixed-format numeric values. Pass raw float values directly.

## Key Patterns
- **2D lookup**: `=INDEX(range,MATCH(row_key,row_range,0),MATCH(col_key,col_range,0))`
- **Weighted mean**: `=SUMPRODUCT(values,weights)/SUM(weights)`
- **Percentile**: `=PERCENTILE.INC(range,0.25)` (use `.INC`, not deprecated `QUARTILE`)

## Anti-patterns
- Using `data_only=True` for writing — strips formulas
- Missing `$` in lookup ranges — causes fill errors
- Using deprecated `QUARTILE()` — use `QUARTILE.INC()` or `PERCENTILE.INC()`
- Hardcoding values instead of cell references
- Skipping blocking validation

## Known invariants (by sub-task)

### multi-series-per-entity
- Series codes in column D (e.g., `*_REN_GEN`, `*_LOAD_IN`)
- MATCH on series code, not entity code
- Each entity has N series rows; formulas target specific series

### single-row-per-entity
- MATCH on entity code in key column
- One formula row per entity

### header-row-verification
- Header row is typically row 4, NOT row 20
- Always verify before constructing MATCH formulas

## Helper Script
Run `python3 scripts/validate_references.py <workbook_path>` to validate formula references. Script exits with non-zero status if required `$` locking is missing.
