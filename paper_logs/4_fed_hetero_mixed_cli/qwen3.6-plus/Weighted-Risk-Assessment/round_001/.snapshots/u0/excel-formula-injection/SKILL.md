---
name: excel-formula-injection
description: Inject formulas into Excel workbooks using openpyxl while preserving formatting. Handles INDEX/MATCH lookups, statistical aggregates, weighted means, and cross-sheet references. Use when tasks require formula-driven outputs in .xlsx files.
---

# Excel Formula Injection

Write formulas into Excel workbooks programmatically. Core limitation: openpyxl stores formulas but **never calculates them**.

## Workflow

1. **Inspect structure**: Load workbook with `openpyxl.load_workbook(path)`. Print sheet names, dimensions, merged cells, and sample rows to understand layout.
2. **Map ranges**: Identify source data ranges and target formula cells before writing.
3. **Write formulas**: Assign formula strings to `cell.value` (e.g., `cell.value = "=A1+B1"`). Do not modify `.fill`, `.number_format`, or `.alignment`.
4. **Verify syntax**: Reload saved file and print formula strings to confirm they persisted with correct references.
5. **Calculate manually**: Extract source data and compute expected results in Python to verify logic (see `scripts/calculate_stats.py`).
6. **Run test suite early**: Execute verifier immediately after changes. Do not rely on self-verification alone.

## Critical Limitations

- **No calculation engine**: openpyxl writes formulas but cannot evaluate them.
- **data_only=True trap**: Returns cached values from last Excel save; returns `None` for newly written formulas.
- **Verifier mismatches**: Tests opening files with `data_only=True` see empty cells if formulas were never calculated by Excel.

## Common Formula Patterns

### INDEX/MATCH 2D Lookup
```excel
=INDEX(Data!$H$21:$L$38,MATCH(D12,Data!$D$21:$D$38,0),MATCH(H$10,Data!$H$4:$L$4,0))
```
- Use absolute refs (`$`) for table arrays and headers
- `MATCH(...,0)` for exact match (required for text codes)

### Cross-Sheet References
```excel
=SheetName!A1
='Sheet Name With Spaces'!A1
```

### Statistical Aggregates
```excel
=AVERAGE(H35:H40)
=MEDIAN(H35:H40)
=PERCENTILE.INC(H35:H40,0.25)
=SUMPRODUCT(H35:H40,H26:H31)/SUM(H26:H31)
```

## Anti-Patterns

- **Do not** rely on `data_only=True` to verify newly written formulas (returns None)
- **Do not** assume self-verification is sufficient—run the actual test suite
- **Do not** overwrite styles: `cell.value = "=FORMULA()"` preserves styles; reassigning `.fill` or `.number_format` overwrites them
- **Do not** use locale-specific semicolons `;` as argument separators unless the target environment requires it

## Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|----------|
| Verifier shows empty/None values | Formulas never calculated | Verify using manual Python calculation; ensure formulas reference correct cells |
| Test fails but calculations look correct | Cell location or string mismatch | Run test with verbose output; compare expected vs actual formula strings |
| #REF! errors | Invalid sheet names or ranges | Check sheet names match exactly; verify ranges exist |
| #N/A in MATCH | Lookup value not found | Confirm exact match flag (`0`) and lookup value exists in search range |
| Formatting lost | Style reassignment | Load existing template; only modify `.value`, not style properties |

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Known Invariants (by sub-task)

### B1: Excel Formula Population with openpyxl
- Output Excel must contain formula strings in target cells, not static values
- Formatting (fills, borders, number formats, merged cells) must be preserved
- Formulas must use correct absolute/relative references for copyability
- Verifier may check formula strings OR calculated values—determine which before proceeding

## Scripts

- `scripts/formula_injector.py`: Populate a rectangular range with parameterized formulas while preserving formatting. Use for repetitive injection across large grids.
- `scripts/calculate_stats.py`: Calculate MIN, MAX, MEDIAN, MEAN, PERCENTILE, WEIGHTED MEAN using standard library for manual verification.

## References

- `references/formula-patterns.md`: Detailed INDEX/MATCH variations, reference types, and Excel function syntax.
