---
name: excel-formula-injection
description: Inject formulas into Excel workbooks using openpyxl while preserving formatting. Handles INDEX/MATCH lookups, statistical aggregates, weighted means, and cross-sheet references. Use when tasks require formula-driven outputs in .xlsx files. CRITICAL - Must run check_test_data_only.py BEFORE writing formulas.
---
# Excel Formula Injection

Write formulas programmatically. Core limitation: openpyxl stores formulas but **never calculates them**.

## MANDATORY PRE-FLIGHT (Run This Command First)

```bash
python3 scripts/check_test_data_only.py /path/to/tests/
```

| Exit Code | Meaning | Action |
|-----------|---------|--------|
| 0 | No data_only=True found | Proceed with openpyxl |
| 2 | data_only=True detected | Use external engine OR calculate manually |
| No tests dir | Cannot determine | Assume data_only=True, use external engine |

**If exit code 2**: Stop. Openpyxl alone will fail. See `references/verifier-interaction.md`.

## Workflow

1. **Run pre-flight check**: Execute `python3 scripts/check_test_data_only.py <tests_dir>` before any other work.
2. **Inspect workbook**: `openpyxl.load_workbook()`. Print sheet names, dimensions, merged cells.
3. **Map ranges**: Identify source data and target cells.
4. **Inject formulas**: `cell.value = "=FORMULA()"`. Do not modify `.fill` or `.number_format`.
5. **Verify syntax**: Reload saved file, print formula strings to confirm correct references.
6. **Run test suite**: Execute `pytest -v` or test command immediately. Do not claim success until tests pass.

## MANDATORY PRE-COMPLETION (Run This Before Submitting)

```bash
python3 scripts/verify_before_submit.py output.xlsx tests/
```

Exit code 0 = all checks passed. Any other exit code = do not submit.

## Critical Limitations

- openpyxl writes formulas but cannot calculate them
- `data_only=True` returns `None` for newly written formulas
- Tests using `data_only=True` will see empty cells

## Formula Patterns

### INDEX/MATCH 2D Lookup
```excel
=INDEX(Data!$H$21:$L$38,MATCH(D12,Data!$D$21:$D$38,0),MATCH(H$10,Data!$H$4:$L$4,0))
```
- Absolute refs (`$`) for table arrays
- `MATCH(...,0)` for exact match

### Statistical Aggregates
```excel
=PERCENTILE.INC(H35:H40,0.25)
=SUMPRODUCT(values,weights)/SUM(weights)
```

### Cross-Sheet References
```excel
=SheetName!A1
='Sheet Name With Spaces'!A1
```

## Anti-Patterns

- Do not skip pre-flight check—determines if verifier needs calculated values
- Do not claim success until tests pass
- Do not overwrite styles—only modify `.value`
- Do not rely on self-verification—run actual test suite
- Do not use `data_only=True` to verify newly written formulas (returns None)

## Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|----------|
| Verifier shows None values | data_only=True on uncalculated formulas | Run pre-flight check; use external engine |
| Tests fail but formulas look correct | Formula string mismatch | Dump actual vs expected formula strings |
| Agent claimed success but tests failed | Test suite never executed | Run verify_before_submit.py before submitting |
| #REF! errors | Invalid sheet/range | Check sheet names match exactly |

## Output Precision

Never round numeric values in outputs. Pass raw floats directly.
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`
- DO: `ws.cell(row=r, column=c, value=x)` with x as raw float

## Scripts

- `scripts/check_test_data_only.py`: **Run FIRST.** Detects data_only=True in tests.
- `scripts/verify_before_submit.py`: **Run BEFORE SUBMITTING.** Runs all checks including tests.
- `scripts/formula_injector.py`: Bulk inject repetitive formulas.
- `scripts/calculate_stats.py`: Manual verification using standard library.

## References

- `references/formula-patterns.md`: INDEX/MATCH variations, reference types.
- `references/verifier-interaction.md`: External engine setup, fallback strategies.

## Known Invariants (by sub-task)

### B1: Excel Formula Population
- Output must contain formula strings in target cells, not static values
- Formatting must be preserved
- Formulas must use correct absolute/relative references
- Determine if verifier checks formula strings OR calculated values before proceeding
