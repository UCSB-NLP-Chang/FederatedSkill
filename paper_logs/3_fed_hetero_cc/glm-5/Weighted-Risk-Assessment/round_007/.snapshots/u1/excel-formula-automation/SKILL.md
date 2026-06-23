---
name: excel-formula-automation
description: Automate Excel formula injection with openpyxl. Use for tasks requiring INDEX/MATCH lookups, statistical aggregations, weighted calculations, or cross-sheet references. CRITICAL: openpyxl writes formulas as strings only - does NOT evaluate them. If verifier checks computed values, must pre-compute in Python or escalate to xlwings/calamine.
---

# Excel Formula Automation

## Pre-Flight Data Verification (BLOCKING)

STOP: Run `python3 scripts/validate_data_sheet.py <workbook_path>` BEFORE building formulas.

| Check | What to Verify |
|-------|----------------|
| Data sheet exists | Sheet named "Data" present |
| No #REF! errors | First 50 rows, 20 cols scanned |
| Series codes valid | Column D rows 21-38 contain strings/ints |
| Year headers found | Rows 1, 4, or 21 in columns H-L |
| Data range populated | H21:L38 not mostly empty |

If validation fails: **DO NOT proceed**. Fix Data sheet corruption first.

## Workflow (mandatory order)

1. **Validate data** - Run pre-flight script (BLOCKING)
2. **Explore structure** - Load with `data_only=False`, find header row (usually row 4), key columns
3. **Determine structure** - Single-row vs multi-series. Multi-series: MATCH on series code (column D)
4. **Build formulas** - Use `$` locking per Reference Locking Table below
5. **Inject formulas** - `cell.value = "=FORMULA"` (never `data_only=True` for writing)
6. **Verify cross-row mappings** - If formulas reference other Task sheet rows, trace one example manually
7. **Save and count** - Reload, verify formula count matches expected

## Reference Locking Table (MANDATORY)

STOP: Each formula must follow this pattern BEFORE saving.

| Context | Lock Pattern | Example |
|---------|--------------|---------|
| INDEX/MATCH lookup range | Fully absolute | `Data!$H$21:$L$38` |
| Row key range | Fully absolute | `Data!$D$21:$D$38` |
| Col header range | Fully absolute | `Data!$H$21:$L$21` |
| Row key cell | Column-absolute | `$D12` |
| Col header cell | Row-absolute | `H$10` |
| Statistics range | Row-absolute | `H$35:H$40` |
| SUMPRODUCT range | Row-absolute | `H$26:H$31` |

## Formula Patterns

### INDEX/MATCH 2D Lookup
```python
# MATCH mode=0 is MANDATORY for exact match (default is sorted mode)
formula = f"=INDEX(Data!$H$21:$L$38,MATCH($D{row},Data!$D$21:$D$38,0),MATCH({col}$10,Data!$H$21:$L$21,0))"
```

### Statistics
```python
f"=MIN(H$35:H$40)"
f"=PERCENTILE.INC(H$35:H$40,0.25)"  # Use .INC suffix
```

### Weighted Mean
```python
f"=SUMPRODUCT(H$35:H$40,H$26:H$31)/SUM(H$26:H$31)"
```

## STOP — Mandatory Checks

1. **MATCH mode=0**: `=MATCH(range,range)` defaults to sorted - MUST use `=MATCH(range,range,0)`
2. **Deprecated functions**: Use `PERCENTILE.INC` not `PERCENTILE`
3. **Reference locking**: Verify `$` positions per table
4. **Multi-series**: MATCH on series code, not entity code
5. **Cross-row formulas**: If row 35 references rows 12/19/26, verify same entity mapping

## Known Invariants (by sub-task)

### multi-series-per-entity
- Series codes in column D (e.g., `*_REN_GEN`, `*_LOAD_IN`)
- MATCH on series code, not entity code
- Each entity has N series rows

### cross-row-formulas-within-task-sheet
- Verify row offset: if row 35 is entity 1, it should reference rows 12, 19, 26 for same entity
- Use explicit mapping: `fin_out_row = 12 + i`, `scrap_row = 19 + i`

### header-row
- Usually row 4, NOT row 20. Inspect actual workbook.

## Verifier Compatibility

**openpyxl does NOT evaluate formulas** - it stores strings only.
- If verifier checks values: pre-compute in Python/numpy, write values to cells
- Or escalate to xlwings/calamine for evaluation
- See `references/verifier-compatibility.md` for strategies

## Anti-Patterns

| Anti-Pattern | Fix |
|--------------|-----|
| `=MATCH(range,range)` no mode | `=MATCH(range,range,0)` exact match |
| `=PERCENTILE(range,0.25)` | `=PERCENTILE.INC(range,0.25)` |
| Missing `$` in lookup range | Check Reference Locking Table |
| MATCH on entity code (multi-series) | MATCH on series code column |
| `data_only=True` for writing | Strips formulas - use `False` |
| Skip pre-flight validation | BLOCKING - must run first |

## Output precision

Never round numeric values when writing. Pass raw floats:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`
- DO: `ws.cell(row=r, column=c, value=x)` with raw float

## Helper Scripts

- `scripts/validate_data_sheet.py` - Pre-flight data validation (BLOCKING)
- `scripts/validate_formulas.py` - Reference locking validation

Run BEFORE building formulas:
```bash
python3 scripts/validate_data_sheet.py <workbook_path>
```