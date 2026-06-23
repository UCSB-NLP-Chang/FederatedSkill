---
name: excel-formula-automation
description: Automate Excel workbook modifications using openpyxl to add formulas, lookup tables, and calculations. Use when tasks require writing Excel formulas programmatically, performing cross-sheet lookups, or implementing spreadsheet calculations while preserving formatting.
---

# Excel Formula Automation with openpyxl

## Workflow

1. **Inspect workbook structure** - Load with `openpyxl.load_workbook(path, data_only=False)`. Identify sheets, header rows (usually row 4), and data ranges.
2. **Map Data sheet** - Find header row for year MATCH, key column for row MATCH. For multi-series: series code column (e.g., `*_REN_GEN`), NOT entity code.
3. **Build formulas** - Use INDEX/MATCH for lookups, statistical functions, weighted means. See Reference Locking Table.
4. **Inject formulas** - Assign to `cell.value`. Save and reload to verify strings preserved.
5. **Verify** - Check formula text matches requirements exactly. Visual inspection is insufficient.

## Reference Locking Table

STOP: Verify each formula follows this locking pattern BEFORE saving.

| Component | Locking Pattern | Example |
|-----------|-----------------|---------|
| Lookup data range | Fully absolute: `$` on row AND col | `Data!$H$21:$L$38` |
| Row key range | Fully absolute | `Data!$D$21:$D$38` |
| Col header range | Fully absolute | `Data!$H$21:$L$21` |
| Row key cell | Column-absolute only | `$D12` |
| Col header cell | Row-absolute only | `H$10` |
| Statistics ranges | Row-absolute only | `H$35:H$40` |
| SUMPRODUCT ranges | Row-absolute only | `H$26:H$31` |

## Formula Patterns

### INDEX/MATCH Two-Dimensional Lookup
```python
formula = f"=INDEX(Data!$H$21:$L$38,MATCH($D{row},Data!$D$21:$D$38,0),MATCH({col}$10,Data!$H$21:$L$21,0))"
```

### Statistics Row
```python
stats = [
    f"=MIN(H$35:H$40)",
    f"=MAX(H$35:H$40)",
    f"=MEDIAN(H$35:H$40)",
    f"=AVERAGE(H$35:H$40)",
    f"=PERCENTILE.INC(H$35:H$40,0.25)",  # Q1
    f"=PERCENTILE.INC(H$35:H$40,0.75)",  # Q3
]
```

### Weighted Mean
```python
weighted_mean = f"=SUMPRODUCT(H$35:H$40,H$26:H$31)/SUM(H$26:H$31)"
```

## STOP — Mandatory Checks

1. **Deprecated functions**: Use `PERCENTILE.INC` not `PERCENTILE`. Use `QUARTILE.INC` not `QUARTILE`.
2. **Reference locking**: Verify each formula has `$` in correct positions per table above.
3. **Multi-series detection**: If Data has series codes (column D), MATCH on series code, not entity.
4. **Header row**: Usually row 4, NOT row 20. Inspect actual structure.

## Known Invariants (by sub-task)

### Multi-series data (R2-R5)
- Series codes in column D (e.g., `ALP_LOAD_IN`, `ALP_LOAD_OUT`)
- MATCH on series code, returns correct row per series
- Each entity has N rows (one per series)

### Statistical formulas
- MIN/MAX/MEDIAN/AVERAGE/PERCENTILE.INC range must be row-locked
- PERCENTILE.INC quartile mapping: 0.25=Q1, 0.5=median, 0.75=Q3

## Anti-Patterns

- **Don't** assume formula correctness from text inspection - a formula that looks correct may reference wrong rows
- **Don't** skip `$` verification - missing absolute references cause wrong values on fill
- **Don't** use `data_only=True` for writing - it strips formulas
- **Don't** use deprecated `QUARTILE()` - use `QUARTILE.INC()` or `PERCENTILE.INC()`
- **Don't** round output values - pass raw floats to cells

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs. Pass raw float values directly:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`
- DO: `ws.cell(row=r, column=c, value=x)` with x as raw float

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| #N/A | MATCH key not found | Verify key values exist in range |
| #REF! | Invalid reference | Check range bounds |
| Wrong values | Missing `$` locking | Check Reference Locking Table |
| Verifier fails | Formula logic mismatch | Re-read task spec character by character |
