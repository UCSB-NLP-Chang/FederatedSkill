---
name: excel-formula-injection
description: Inject formulas into Excel workbooks using openpyxl while preserving formatting. Handles INDEX/MATCH lookups, statistical aggregates, weighted means, and cross-sheet references. Use when tasks require formula-driven outputs in .xlsx files.
---

# Excel Formula Injection

Write formulas programmatically. **Core limitation: openpyxl stores formulas but never calculates them.**

## MANDATORY: Run Pre-Flight Check First

**Step 0 — Execute this command before writing any formulas:**

```bash
python3 scripts/check_test_data_only.py /path/to/tests/
```

**Handle the result:**

| Exit Code | Meaning | Your Action |
|-----------|---------|-------------|
| 0 | No `data_only=True` | Proceed with openpyxl formula injection |
| 2 | `data_only=True` found | **STOP**. Use external engine (LibreOffice/xlwings) or calculate manually. See `references/verifier-interaction.md`. |

**Do not proceed to Step 1 until you have handled the pre-flight check result.**

## Workflow

1. **Pre-flight check**: Run `python3 scripts/check_test_data_only.py <tests_dir>`. Handle exit code before continuing.
2. **Inspect structure**: `python3 -c "import openpyxl; wb = openpyxl.load_workbook('file.xlsx'); print(wb.sheetnames)"` — Print sheet names, dimensions, merged cells.
3. **Map ranges**: Identify source data ranges and target formula cells. Write them down before coding.
4. **Write formulas**: Assign formula strings to `cell.value` only. Do not modify `.fill`, `.number_format`, or `.alignment`.
5. **Verify syntax**: Reload saved file and print formula strings to confirm they persisted.
6. **Calculate manually**: Run `python3 scripts/calculate_stats.py` to compute expected values for verification.
7. **Run test suite**: Execute `pytest -v` immediately. Do not wait.
8. **Run verification script**: `python3 scripts/verify_before_submit.py output.xlsx tests/` — **This must pass before claiming done.**

## Critical Limitations

- **No calculation engine**: openpyxl writes formulas but cannot evaluate them.
- **data_only=True trap**: Returns cached values from last Excel save; returns `None` for newly written formulas.
- **Verifier mismatches**: Tests opening files with `data_only=True` see empty cells.

## Anti-Patterns

- **Do not** skip Step 0 — determines if verifier needs calculated values
- **Do not** rely on `data_only=True` to verify newly written formulas (returns None)
- **Do not** claim success until `verify_before_submit.py` exits with code 0
- **Do not** overwrite styles: only modify `.value`, not `.fill` or `.number_format`
- **Do not** use locale-specific semicolons `;` as argument separators
- **Do not** round numbers: pass raw floats to cells

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs:

- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision

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

## Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|----------|
| Verifier shows empty/None values | Formulas never calculated + `data_only=True` | Use external engine OR calculate manually |
| Test fails but formulas look correct | Formula string mismatch (spaces, `$`, commas) | Dump actual vs expected formula strings |
| #REF! errors | Invalid sheet names or ranges | Check sheet names match exactly |
| #N/A in MATCH | Lookup value not found | Confirm exact match flag (`0`) and value exists |
| Formatting lost | Style reassignment | Only modify `.value` |
| Agent claimed success but tests failed | Test suite never executed | Run `verify_before_submit.py` before claiming done |

## Known Invariants (by sub-task)

### B1: Excel Formula Population with openpyxl
- Output Excel must contain formula strings in target cells, not static values
- Formatting (fills, borders, number formats, merged cells) must be preserved
- Formulas must use correct absolute/relative references for copyability
- Verifier may check formula strings OR calculated values — determine which before proceeding

## Scripts

- `scripts/check_test_data_only.py`: **RUN THIS FIRST.** Detects `data_only=True` in test files.
- `scripts/verify_before_submit.py`: **RUN THIS BEFORE CLAIMING DONE.** Runs tests and checks output.
- `scripts/formula_injector.py`: Batch inject formulas into rectangular ranges.
- `scripts/calculate_stats.py`: Calculate statistics using standard library for verification.

## References

- `references/formula-patterns.md`: INDEX/MATCH variations, reference types, Excel function syntax.
- `references/verifier-interaction.md`: Handling verifiers that require calculated values, external engine setup.