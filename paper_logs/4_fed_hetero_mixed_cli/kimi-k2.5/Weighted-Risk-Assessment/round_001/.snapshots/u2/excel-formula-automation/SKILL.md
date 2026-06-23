---
name: excel-formula-automation
description: Write and verify Excel formulas programmatically using openpyxl while handling its key limitation (no calculation engine). Use when tasks require formula-driven outputs with cross-sheet lookups (INDEX/MATCH, VLOOKUP), statistical calculations, weighted metrics, or batch formula injection into pre-formatted templates.
---

# Excel Formula Automation

Write formulas programmatically while handling openpyxl's critical limitation: it stores formulas but never calculates them.

## When to use

- Filling specific cell ranges in existing `.xlsx` templates with Excel formulas
- Templates with pre-applied formatting (fills, borders, number formats, merged cells) that must be preserved
- Cross-sheet lookups (`INDEX/MATCH`, `VLOOKUP`), derived calculations, or aggregations (`SUMPRODUCT`, `PERCENTILE`)
- Weighted mean calculations or statistical formulas across data ranges

## Workflow

1. **Inspect structure**: Load workbook with `openpyxl.load_workbook()`. Print sheet names, dimensions, merged cells, and target cell ranges. Identify source data locations and header mappings.
2. **Map ranges**: Define target ranges (e.g., `H12:L17`) and corresponding row/column identifiers. Note absolute vs relative reference requirements.
3. **Inject formulas**: Assign formula strings to `cell.value` without modifying `cell.fill`, `cell.number_format`, or `cell.alignment`. Use absolute references (`$`) appropriately for cross-sheet lookups.
4. **Preserve layout**: Do not delete or recreate sheets. Only modify `.value` in target cells. Verify merged cells remain intact.
5. **Verify syntax**: Reload saved file and sample-check formula strings contain expected references.
6. **Validate logic**: Calculate expected results manually using Python (see `scripts/calculate_stats.py`) or run the test suite early.

## Critical Limitations

- **No calculation engine**: openpyxl writes formulas but cannot evaluate them
- **data_only=True trap**: Returns cached values from last Excel save; returns `None` for newly written formulas
- **Verifier failures**: Test suites opening files with `data_only=True` will see empty cells if formulas were never calculated by Excel

## Common Formula Patterns

### INDEX/MATCH 2D Lookup
```excel
=INDEX(Data!$H$21:$L$38,MATCH(D12,Data!$D$21:$D$38,0),MATCH(H$10,Data!$H$4:$L$4,0))
```
- Use absolute refs (`$`) for table arrays and headers
- Match row key in column D, column key in row 10
- `MATCH(...,0)` for exact match (required for text codes)

### Cross-Sheet References
- Syntax: `SheetName!$A$1` or `'Sheet Name With Spaces'!$A$1` (quotes if spaces)
- openpyxl preserves sheet names exactly as written

### Statistical Aggregates
- Percentiles: `PERCENTILE.INC(range,0.25)` for Q1, `0.75` for Q3
- Weighted mean: `SUMPRODUCT(values,weights)/SUM(weights)`

## Critical Rules

- **Never overwrite styles**: `cell.value = "=FORMULA()"` preserves existing styles
- **Absolute vs Relative**: Use `$` for fixed ranges (e.g., `Data!$H$21:$L$38`) and mixed references for row/column lookups
- **Merged Cells**: Writing to top-left coordinate is safe; other cells in merged range may error
- **Formula Syntax**: Excel uses commas `,` as argument separators; avoid locale-specific semicolons unless required
- **Run tests early**: Execute test suite immediately after changes—do not rely solely on manual verification

## Anti-Patterns

- **Don't** rely on `data_only=True` to verify newly written formulas—returns `None`
- **Don't** assume pandas/numpy are available for verification calculations
- **Don't** mix relative and absolute references without explicit intent
- **Don't** assume self-verification is sufficient—test suite may check exact cell addresses or reference styles
- **Don't** use `data_only=True` when you need to preserve formulas—converts formulas to values on save

## Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|----------|
| Verifier shows empty/None values | Formulas never calculated | Verify using manual Python calculation; ensure formulas reference correct cells; if verifier needs cached values, use external engine (xlwings/LibreOffice) |
| #REF! errors | Invalid sheet/range reference | Verify sheet names match exactly; check ranges exist |
| #N/A in MATCH | Lookup value not found | Use exact match flag (0); verify lookup value exists in range |
| #VALUE! | Wrong argument type | Ensure ranges same size for SUMPRODUCT |
| Wrong lookup results | MATCH approximate mode | Use `MATCH(...,0)` for exact match |
| Formatting lost | Style overwrite in code | Never reassign `.fill` or `.number_format`; load existing template |

## Verification Strategies

When verifiers expect calculated values:

1. **Manual calculation**: Extract source data, replicate logic in Python using `statistics` module (no numpy/pandas dependency)
2. **Formula inspection**: Verify formula strings contain correct cell references and function names
3. **External engine** (if available): Use xlwings or LibreOffice to open/save file to cache calculated values
4. **Run test suite**: Capture failure output; compare expected vs actual cell values or formula structures

## Scripts

- `scripts/calculate_stats.py`: Calculate MIN, MAX, MEDIAN, MEAN, PERCENTILE, WEIGHTED MEAN using standard library for verification
- `scripts/formula_injector.py`: Batch inject repetitive formulas into rectangular ranges while preserving formatting

## References

- `references/formula-patterns.md`: Detailed INDEX/MATCH variations, reference types, and Excel function syntax

## Known invariants (by sub-task)

(Empty—will be populated as verifier failures reveal task-specific rules)