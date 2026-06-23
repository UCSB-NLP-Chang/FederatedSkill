---
name: excel-formula-automation
description: Construct and inject Excel formulas programmatically using openpyxl. Use for tasks requiring INDEX/MATCH lookups, statistical aggregations, weighted calculations, or cross-sheet references. CRITICAL LIMITATION: openpyxl writes formulas as strings; it does NOT evaluate them. Trigger when you need formula injection with verification that formulas will evaluate correctly in actual Excel.
---

# Excel Formula Automation with openpyxl

Build complex Excel workbooks with formulas. **Critical constraint**: openpyxl writes formulas as unevaluated strings - Excel (or a calculation engine) must open the file to compute values.

## Pre-Flight Data Verification (BLOCKING)

Before building ANY formula, verify the data source exists and is parseable:

1. **Load Data sheet with `data_only=True` first** - confirm expected values are present, not formulas or #REF! errors
2. **Check for actual data rows** - verify lookup ranges (e.g., `Data!H21:L38`) contain expected values
3. **Validate key columns exist** - series codes in expected column (e.g., column D), years in expected header row
4. **Type-check match keys** - ensure series codes are strings (not floats like `123.0`) if matching against text

If Data sheet shows `#REF!`, `None`, or wrong types: **STOP** and escalate.

Run pre-flight validation:
```bash
python3 scripts/validate_data_sheet.py <workbook_path>
```

## Workflow (mandatory order)

1. **Explore structure** - Load workbook with `data_only=False`, identify sheets, header row (usually row 4), data ranges, key lookup keys
2. **Pre-validate data** - Run `validate_data_sheet.py` - BLOCKING if data is corrupted
3. **Determine data structure** - Single-row-per-entity vs multi-series. For multi-series, MATCH on series code column (e.g., column D), NOT entity code
4. **Build formulas with correct reference locking** - Use `$` signs per Reference Locking Table below
5. **Inject formulas** - Set `cell.value = formula_string` directly
6. **Handle verifier expectations** - If verifier checks computed VALUES (not formula strings), see `references/verifier-compatibility.md`. openpyxl does NOT evaluate formulas.
7. **Run validation script** - Execute `scripts/validate_formulas.py` (exits 1 on errors - BLOCKING)
8. **Critical: Verify cross-row mappings** - When formulas reference other Task sheet rows, trace one example manually to confirm correct row offset
9. **Save and verify** - Save, reload, count formulas to confirm injection count matches expected

## Reference Locking Table (MANDATORY)

| Context | Lock Pattern | Example | Why |
|---------|--------------|---------|-----|
| INDEX/MATCH lookup ranges | Fully absolute `$A$1:$B$10` | `Data!$H$21:$L$38` | Range must not shift when formula copies |
| Statistics ranges (MIN/MAX/MEDIAN/AVERAGE) | Row-absolute `A$1:A$10` | `H$35:H$40` | Column adjusts, rows fixed |
| SUMPRODUCT/SUM weight ranges | Row-absolute `A$1:A$10` | `H$26:H$31` | Same as statistics |
| MATCH row key reference | Column-absolute `$A10` | `$D12` | Column fixed (series code), row adjusts |
| MATCH column header reference | Row-absolute `A$10` | `H$10` | Row fixed (header), column adjusts |

## Critical Formula Patterns

### INDEX/MATCH Two-Dimensional Lookup
```python
# CRITICAL: MATCH mode must be 0 (exact match)
formula = f"=INDEX(Data!$H$21:$L$38,MATCH($D{row},Data!$D$21:$D$38,0),MATCH({col}$10,Data!$H$4:$L$4,0))"
```
- `$D{row}`: Column D locked, row dynamic
- `{col}$10`: Column dynamic, row 10 locked
- **MATCH mode must be 0** - omitting defaults to 1 (sorted), causing wrong matches

### Common Error: MATCH mode omitted or wrong
```python
# WRONG - defaults to sorted match, fails on unsorted data
"=MATCH($D12,Data!$D$21:$D$38)"

# CORRECT - exact match required
"=MATCH($D12,Data!$D$21:$D$38,0)"
```

### Statistical Aggregations
```python
f"=MIN(H$35:H$40)"           # Row-absolute for fill-across
f"=PERCENTILE.INC(H$35:H$40,0.25)"  # .INC suffix mandatory
```

### Weighted Mean
```python
f"=SUMPRODUCT(H$35:H$40,H$26:H$31)/SUM(H$26:H$31)"
```

### Cross-Row Formulas Within Task Sheet
When formulas reference other rows in the same sheet (e.g., row 35 references rows 12, 19, 26):
```python
# Verify row mapping: if row 35 corresponds to entity 1, it should reference
# rows 12, 19, 26 for that same entity
fin_out_row = 12 + entity_offset
scrap_row = 19 + entity_offset
cap_row = 26 + entity_offset
```

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`
- DO: `ws.cell(row=r, column=c, value=x)` with x as raw float

## Validation Checklist (before save)

- [ ] Data sheet pre-validated: expected values present, correct types, no #REF! errors
- [ ] Formula strings match intended syntax exactly
- [ ] MATCH functions use `0` as third argument (exact match)
- [ ] Absolute references (`$`) preserved per Reference Locking Table
- [ ] Statistics use `PERCENTILE.INC` / `QUARTILE.INC` only
- [ ] Multi-series uses series code column for MATCH, not entity code
- [ ] Header row verified (check actual workbook, don't assume row 20)
- [ ] Cross-row mappings verified: trace one formula's row references manually
- [ ] Sample formula manually verified: computed expected result from source data

## Anti-Patterns

| Anti-Pattern | Correct Approach |
|--------------|------------------|
| Skip Data sheet validation | Always run `validate_data_sheet.py` first |
| `=MATCH(range,range)` (no mode) | `=MATCH(range,range,0)` for exact match |
| `=PERCENTILE(range,0.25)` | `=PERCENTILE.INC(range,0.25)` |
| `=QUARTILE(range,1)` | `=PERCENTILE.INC(range,0.25)` or `=QUARTILE.INC(range,1)` |
| `data_only=True` when writing | Keep `data_only=False` (default) |
| Trust visual inspection alone | Manual sample calculation + validation script |
| Assume lookup ranges are correct | Verify actual row/column contents |
| Assume openpyxl evaluates formulas | See `references/verifier-compatibility.md` |

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

### cross-row-formulas
- Formulas referencing other Task sheet rows need explicit offset verification
- Trace row mapping: row 35 → rows 12, 19, 26 for same entity

## When to Escalate

**Use xlwings or calamine instead of openpyxl when:**
- You need to read computed formula values (openpyxl cannot calculate)
- Data sheet contains formulas that must be evaluated first
- Complex array formulas or dynamic ranges required
- Test assertions check cell values, not formulas

**Escalate immediately if:**
- Data sheet shows `#REF!` errors in source data
- Lookup keys are floats but matched as strings (or vice versa)
- MATCH on series codes returns wrong index despite exact match mode

## Helper Scripts

- `scripts/formula_builder.py` - INDEX/MATCH, weighted mean, percentile builders
- `scripts/validate_formulas.py` - **BLOCKING**: Validates $ locking, deprecated functions, exits 1 on error
- `scripts/validate_data_sheet.py` - **BLOCKING**: Pre-flight data validation
- `scripts/excel_formula_utils.py` - Workbook inspection, range operations

Run validation scripts BEFORE saving:
```bash
python3 scripts/validate_data_sheet.py <workbook_path>
python3 scripts/validate_formulas.py <workbook_path> [target_sheet]
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| #N/A | MATCH key not found | Verify key values exist in range, check case/trailing spaces |
| #REF! | Invalid reference | Check range bounds, sheet name |
| Wrong values | Missing `$` locking | Check Reference Locking Table |
| MATCH returns wrong position | MATCH mode omitted | Add `,0` for exact match |
| Verifier fails on values | openpyxl doesn't evaluate | See `references/verifier-compatibility.md` |
| Type mismatch | Float vs string in MATCH | Check `repr(cell.value)` for actual types |

## References

- `references/verifier-compatibility.md` - Handling value-checking verifiers with openpyxl
- `references/troubleshooting-index-match.md` - Detailed INDEX/MATCH debugging guide
