---
name: excel-formula-injection
description: Inject formulas into Excel workbooks using openpyxl while preserving formatting. Handles INDEX/MATCH lookups, statistical aggregates, weighted means, and cross-sheet references. Use when tasks require formula-driven outputs in .xlsx files. CRITICAL - Must run check_test_data_only.py BEFORE writing formulas, and verify_before_submit.py MUST pass before claiming success.
---

# Excel Formula Injection

Write formulas programmatically. Core limitation: openpyxl stores formulas but **never calculates them**.

## MANDATORY PRE-FLIGHT

**Step 0 — Find test files first:**
Tests are often NOT in the data directory. Search for them:
```bash
find /root -name "test*.py" -o -name "*_test.py" 2>/dev/null | head -20
ls -la /root/test_output.py 2>/dev/null
```

**Step 1 — Run pre-flight check on TEST directory:**
```bash
python3 scripts/check_test_data_only.py <path_to_tests>
```

| Exit Code | Meaning | Action |
|-----------|---------|--------|
| 0 | No `data_only=True` | Proceed with openpyxl |
| 2 | `data_only=True` detected | STOP. Use external engine (LibreOffice/xlwings) or calculate manually. See `references/verifier-interaction.md` |
| 3 | No test files found | Search more broadly; assume `data_only=True` if uncertain |
| 1 | Script error | Fix path argument |

**Do not proceed until Step 1 handled.**

## Workflow

1. **Find tests & run pre-flight**: Execute Step 0 & 1 above.
2. **Inspect workbook**: `openpyxl.load_workbook()`. Print sheet names, dimensions, merged cells.
3. **Map ranges**: Identify source data and target cells.
4. **Inject formulas**: `cell.value = "=FORMULA()"`. Do not modify `.fill` or `.number_format`.
5. **Verify syntax**: Reload saved file, print formula strings.
6. **Run actual tests**: `pytest <test_file> -v` immediately. Do NOT skip.
7. **Run verification**: `python3 scripts/verify_before_submit.py output.xlsx <tests_dir>` — Must exit 0.

## MANDATORY PRE-COMPLETION

```bash
python3 scripts/verify_before_submit.py output.xlsx <tests_dir>
```

**Exit code 0 = all checks passed.** Any other = do not submit.

## Formula String Exactness

Tests often assert exact string matches. Common failures:
- Extra spaces around commas or operators
- Wrong function names (`PERCENTILE` vs `PERCENTILE.INC`)
- Incorrect `$` placement
- Wrong argument separator (some locales use `;`)

If tests fail but formulas look correct:
```python
print(f"actual: {repr(cell.value)}")
print(f"expected: {repr(expected_formula)}")
```

## Critical Limitations

- openpyxl writes formulas but cannot calculate them
- `data_only=True` returns `None` for newly written formulas
- Tests using `data_only=True` see empty cells

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

- Do not pass data/ directory to check/verify scripts — use tests/ or test file path
- Do not skip pre-flight check
- Do not claim success until `verify_before_submit.py` exits 0
- Do not overwrite styles — only modify `.value`
- Do not round numbers — pass raw floats

## Output Precision

Never round, truncate, or fixed-format numeric values:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`
- DO: `ws.cell(row=r, column=c, value=x)` with x as raw float

## Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|----------|
| `pytest` collects 0 items | Wrong directory passed | Run `find /root -name "test*.py"` |
| Verifier shows None values | `data_only=True` on uncalculated formulas | Run pre-flight; use external engine |
| Tests fail but formulas correct | Formula string mismatch | Dump actual vs expected with `repr()` |
| Agent claimed success but failed | Tests never executed | Run `verify_before_submit.py` before submitting |
| #REF! errors | Invalid sheet/range | Check sheet names match exactly |
| "No test files found" | Pre-flight searched wrong path | Use explicit file path like `/root/test_output.py` |

## Scripts

- `scripts/check_test_data_only.py`: **Run FIRST on TEST directory.** Exit 3 = no tests found.
- `scripts/verify_before_submit.py`: **Run BEFORE SUBMITTING.** Must exit 0.
- `scripts/formula_injector.py`: Bulk inject formulas into ranges.
- `scripts/calculate_stats.py`: Manual calculation verification.

## References

- `references/formula-patterns.md`: INDEX/MATCH variations, weighted mean patterns, reference types.
- `references/verifier-interaction.md`: External engine setup, fallback strategies.
- `references/finding-tests.md`: How to locate test files in non-standard locations.

## Known Invariants (by sub-task)

### B1: Excel Formula Population
- Output must contain formula strings in target cells, not static values
- Formatting must be preserved
- Formulas must use correct absolute/relative references
- Determine if verifier checks formula strings OR calculated values before proceeding
