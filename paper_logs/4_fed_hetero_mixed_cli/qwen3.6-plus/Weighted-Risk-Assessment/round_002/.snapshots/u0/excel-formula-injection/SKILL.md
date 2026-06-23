---
name: excel-formula-injection
description: Inject formulas into Excel workbooks using openpyxl while preserving formatting. Handles INDEX/MATCH lookups, statistical aggregates, weighted means, and cross-sheet references. Use when tasks require formula-driven outputs in .xlsx files.
---

# Excel Formula Injection

Write formulas into Excel workbooks programmatically. Core limitation: openpyxl stores formulas but **never calculates them**.

## Pre-Flight Check (Run Before Writing Formulas)

**Step 0**: Detect if verifier expects calculated values:

```bash
python3 scripts/check_test_data_only.py /path/to/tests/
```

OR manually:
```bash
grep -r "data_only" tests/ | grep -i "true"
```

| Result | Meaning | Action |
|--------|---------|--------|
| `data_only=True` found | Verifier expects calculated values | Use external engine (LibreOffice/xlwings) OR calculate expected values manually |
| No `data_only=True` | Verifier checks formula strings | Proceed with openpyxl |

## Workflow

1. **Run pre-flight check**: Execute `python3 scripts/check_test_data_only.py <tests_dir>` BEFORE writing any formulas. If `data_only=True` detected, see `references/verifier-interaction.md` for external engine options.
2. **Inspect structure**: Load workbook with `openpyxl.load_workbook(path)`. Print sheet names, dimensions, merged cells, and sample rows.
3. **Map ranges**: Identify source data ranges and target formula cells before writing.
4. **Write formulas**: Assign formula strings to `cell.value` (e.g., `cell.value = "=A1+B1"`). Do not modify `.fill`, `.number_format`, or `.alignment`. Use `scripts/formula_injector.py` for bulk injection.
5. **Verify syntax**: Reload saved file and print formula strings to confirm they persisted with correct references.
6. **Calculate manually**: Extract source data and compute expected results in Python using `scripts/calculate_stats.py`.
7. **Run test suite early**: Execute verifier immediately after writing first batch. Do not wait until all formulas complete.
8. **Run full test suite**: Execute verifier on complete output. **Do not claim success until tests pass.**

## Critical Limitations

- **No calculation engine**: openpyxl writes formulas but cannot evaluate them.
- **data_only=True trap**: Returns cached values from last Excel save; returns `None` for newly written formulas.
- **Verifier mismatches**: Tests opening files with `data_only=True` see empty cells if formulas were never calculated by Excel.

## Decision Tree: Formula vs Calculation Failures

When tests fail after formula injection:

```
Did you run check_test_data_only.py before writing?
├── YES: Was data_only=True detected?
│   ├── YES: Did you use external engine?
│   │   ├── YES: Check LibreOffice/xlwings errors
│   │   └── NO: Run external engine OR calculate manually and compare
│   └── NO: Compare formula strings character-by-character
│           (spaces, $, commas, sheet name quotes)
└── NO: Run it now to determine failure mode
```

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

- **Do not** skip pre-flight check—determines if verifier needs calculated values
- **Do not** rely on `data_only=True` to verify newly written formulas (returns None)
- **Do not** assume self-verification is sufficient—run the actual test suite
- **Do not** overwrite styles: `cell.value = "=FORMULA()"` preserves styles; reassigning `.fill` or `.number_format` overwrites them
- **Do not** use locale-specific semicolons `;` as argument separators unless required
- **Do not** write long inline Python scripts for bulk injection—use `scripts/formula_injector.py`
- **Do not** claim success until test suite passes

## Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|----------|
| Verifier shows empty/None values | Formulas never calculated + `data_only=True` | Use external engine OR calculate manually |
| Test fails but calculations look correct | Formula string mismatch (spaces, `$`, commas) | Dump actual vs expected formula strings; use `scripts/formula_injector.py` |
| #REF! errors | Invalid sheet names or ranges | Check sheet names match exactly; verify ranges exist |
| #N/A in MATCH | Lookup value not found | Confirm exact match flag (`0`) and lookup value exists |
| Formatting lost | Style reassignment | Load existing template; only modify `.value` |
| Agent claimed success but tests failed | Test suite never executed | Run `pytest -v` or test command before claiming done |

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
- `scripts/check_test_data_only.py`: Scan test files for `data_only=True` usage. Run BEFORE writing formulas to determine verifier expectations.

## References

- `references/formula-patterns.md`: Detailed INDEX/MATCH variations, reference types, and Excel function syntax.
- `references/verifier-interaction.md`: Handling verifiers that require calculated values, external engine setup (LibreOffice/xlwings), and fallback strategies.
