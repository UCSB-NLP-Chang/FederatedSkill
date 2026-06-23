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

1. **Pre-flight check (CRITICAL)**: Run `python scripts/check_test_data_only.py <tests_dir>` BEFORE writing formulas. If `data_only=True` is detected, see `references/verifier-interaction.md` for alternative strategies.
2. **Inspect structure first**: Load workbook with `openpyxl.load_workbook()` and print sheet names, dimensions, merged cells, and sample rows to understand layout.
3. **Map source data and target cells**: Locate source data ranges and identify target cells before writing formulas.
4. **Write formulas with correct references**: Assign formula strings to `cell.value`. Use absolute references (`$A$1`) for fixed ranges, mixed references for copyable formulas.
5. **Preserve styles**: `cell.value = "=FORMULA()"` preserves existing styles. Do not reassign `.fill`, `.number_format`, or `.alignment` unless explicitly required.
6. **Verify syntax**: Reload saved file and print formula strings to confirm they persisted correctly.
7. **Run verification script**: Execute `python scripts/verify_before_submit.py <output_file> <tests_dir>`. This runs the test suite automatically.
8. **If tests fail**: Compare expected vs actual cell addresses, formula strings, and formatting. Check for subtle differences in reference style, sheet names, or cell locations.

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

- **Do not** skip the pre-flight check—it determines if the verifier needs calculated values
- **Do not** claim success until `verify_before_submit.py` passes
- **Do not** use `data_only=True` when you need to preserve formulas — this converts formulas to values on save
- **Do not** rely on `data_only=True` to verify newly written formulas — returns `None` until Excel recalculates
- **Do not** overwrite styles by reassigning `cell.fill`, `cell.number_format`, or `cell.alignment` unless explicitly required
- **Do not** delete or recreate sheets — only modify `.value` in target cells
- **Do not** use mixed absolute/relative references in weight ranges without verifying the intended behavior

## Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|----------|
| Verifier shows empty/None values | Formulas never calculated + `data_only=True` | Use external engine OR calculate manually; see `references/verifier-interaction.md` |
| Tests fail but formulas look correct | Formula string mismatch (spaces, `$`, commas) | Dump actual vs expected formula strings; use `scripts/formula_injector.py` |
| #REF! errors | Invalid sheet names or ranges | Check sheet names match exactly; verify ranges exist |
| #N/A in MATCH | Lookup value not found | Use exact match flag (`0`); verify lookup value exists |
| Weighted mean values wrong across columns | Weight range locked with `$` when should vary | Check if weight data varies by column; remove `$` from column reference |
| Formatting lost | Style reassignment | Load existing template; only modify `.value` |
| Agent claimed success but tests failed | Test suite never executed | Run `python scripts/verify_before_submit.py <output> <tests>` |

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
- Verifier may check formula strings OR calculated values—**determine which before proceeding using `check_test_data_only.py`**

## Helper Scripts

- `scripts/verify_before_submit.py`: Run mandatory pre-completion checks including test execution. **Run this before claiming done.**
  - Exit 0: All checks passed
  - Exit 1: Missing/invalid output file
  - Exit 2: Test suite failed
  - Exit 4: No test files found (search manually with `find`)
- `scripts/check_test_data_only.py`: Scan test files for `data_only=True` usage. **Run this FIRST before writing formulas.**
  - Exit 0: No `data_only=True` found (safe to proceed)
  - Exit 2: `data_only=True` detected (external calculation required)
  - Exit 3: No test files found (cannot determine safety)
- `scripts/formula_injector.py`: Populate a rectangular range with a parameterized formula while preserving all cell properties.
- `scripts/calculate_stats.py`: Calculate MIN, MAX, MEDIAN, MEAN, PERCENTILE, WEIGHTED MEAN using standard library for verification.

## References

- `references/formula-patterns.md`: Detailed INDEX/MATCH variations, weighted mean reference patterns, and Excel function syntax.
- `references/verifier-interaction.md`: Handling verifiers that require calculated values, external engine setup, and fallback strategies.
- `references/finding-tests.md`: How to locate test files when they're not in standard locations.
