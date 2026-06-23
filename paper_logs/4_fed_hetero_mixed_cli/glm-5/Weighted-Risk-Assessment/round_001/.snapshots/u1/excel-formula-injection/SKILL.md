---
name: excel-formula-injection
description: Populate existing Excel workbooks with formulas using openpyxl while preserving formatting and layout. Use when tasks require injecting lookup formulas (INDEX/MATCH, VLOOKUP), statistical calculations, or weighted metrics into pre-formatted templates.
---

# Excel Formula Injection

Write formulas programmatically into existing Excel templates while preserving styles, merged cells, and sheet structure.

## When to use

- Tasks require filling specific cell ranges in an existing `.xlsx` template with Excel formulas
- Template contains pre-applied formatting (fills, borders, number formats, merged cells) that must be preserved
- Cross-sheet lookups (INDEX/MATCH, VLOOKUP), derived calculations, or aggregations needed
- Delivering `.xlsx` files with formula-driven outputs rather than static values

## Workflow

1. **Inspect structure first**: Load workbook with `openpyxl.load_workbook()` and print sheet names, dimensions, merged cells, and sample rows to understand layout.
2. **Map source data and target cells**: Locate source data ranges and identify target cells before writing formulas.
3. **Write formulas with correct references**: Assign formula strings to `cell.value`. Use absolute references (`$A$1`) for fixed ranges, mixed references for copyable formulas.
4. **Preserve styles**: `cell.value = "=FORMULA()"` preserves existing styles. Do not reassign `.fill`, `.number_format`, or `.alignment` unless explicitly required.
5. **Verify syntax**: Reload saved file and print formula strings to confirm they persisted correctly.
6. **Run tests immediately**: Execute the test suite right after making changes. Do not rely solely on manual calculation verification.

## Critical Limitations

- **openpyxl does not calculate formulas**: It only stores formula strings. Formulas will not have computed values until opened in Excel.
- **data_only=True trap**: Loading with `data_only=True` returns cached values from the last Excel save. For newly written formulas (never opened in Excel), it returns `None`.
- **Verifier failures**: Test suites opening files with `data_only=True` will see empty cells if formulas were never calculated by Excel.

## Common Formula Patterns

### INDEX/MATCH 2D Lookup
```python
# Two-way lookup by row key and column header
formula = f"=INDEX(Data!$H$21:$L$38, MATCH($D{row}, Data!$D$21:$D$38, 0), MATCH(H$10, Data!$H$4:$L$4, 0))"
```
- Use absolute refs (`$`) for table arrays and headers
- `0` in MATCH means exact match (required for text codes)

### Weighted Mean
```python
formula = "=SUMPRODUCT(values_range, weights_range) / SUM(weights_range)"
```

### Statistical Aggregates
```python
# Percentiles: PERCENTILE.INC for Q1 (0.25), Q3 (0.75)
formula = "=PERCENTILE.INC(H35:H40, 0.25)"
```

## Reference Rules

| Type | Syntax | Use Case |
|------|--------|----------|
| Absolute | `$A$1` | Table arrays, headers that don't shift |
| Mixed | `A$1`, `$A1` | Copy across rows or down columns |
| Relative | `A1` | Formula should adjust with position |
| Cross-sheet | `SheetName!A1` or `'Sheet Name'!A1` | Reference other sheets (quotes for spaces) |

## Anti-Patterns

- **Do not** assume self-verification is sufficient. A formula may calculate correctly but fail tests due to cell location, reference style, or formatting requirements.
- **Do not** use `data_only=True` when you need to preserve formulas — this converts formulas to values on save.
- **Do not** rely on `data_only=True` to verify newly written formulas — returns `None` until Excel recalculates.
- **Do not** overwrite styles by reassigning `cell.fill`, `cell.number_format`, or `cell.alignment` unless explicitly required.
- **Do not** delete or recreate sheets — only modify `.value` in target cells.

## Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|----------|
| Test fails but calculations look correct | Verifier checks exact location or string format | Run test with verbose output; compare expected vs actual cell addresses |
| Verifier shows empty/None values | Formulas never calculated | Verify using manual Python calculation (see scripts/calculate_stats.py) |
| Formula shows as text, not formula | Cell value doesn't start with `=` | Ensure formula string begins with `=` (no leading spaces/quotes) |
| #REF! error | Invalid sheet name or range | Check sheet names match exactly; verify ranges exist |
| #N/A in MATCH | Lookup value not found | Use `MATCH(...,0)` for exact match; check for type mismatches (text vs number) |
| Formatting lost | Called `ws.cell()` with style overrides | Always load existing template; only modify `.value` |

## Helper Scripts

- `scripts/formula_injector.py`: Populate a rectangular range with a parameterized formula while preserving all cell properties. Use for repetitive formula injection across large grids.
- `scripts/calculate_stats.py`: Calculate MIN, MAX, MEDIAN, MEAN, PERCENTILE, WEIGHTED MEAN using standard library for verification when numpy/pandas unavailable.

## References

- `references/formula-patterns.md`: Detailed INDEX/MATCH variations and Excel function syntax.
