---
name: excel-formula-automation
description: Automate Excel formula injection with openpyxl. Use when tasks require writing Excel formulas programmatically, performing INDEX/MATCH lookups, statistical aggregations, weighted calculations, or cross-sheet references while preserving formatting.
---

# Excel Formula Automation

## Workflow (mandatory order)
1. **Pre-flight validation**: Run `python3 scripts/validate_data_sheet.py <path>` — BLOCKING. Checks Data sheet integrity.
2. **Load and inspect**: `python3 scripts/validate_references.py --inspect <path>` to view structure.
3. **Map layout**: Identify header row (usually row 4), key columns, data ranges. For multi-series: MATCH on series code column, NOT entity code.
4. **Build formulas**: Use templates with correct `$` locking (see references/locking-patterns.md). MATCH mode MUST be 0.
5. **Inject formulas**: Set `cell.value = "=FORMULA"` — never use `data_only=True` for writing.
6. **Validate blocking**: Run `python3 scripts/validate_references.py <path>` — exits with error if `$` signs missing or MATCH mode omitted.
7. **Handle verifier expectations**: If verifier checks computed values, see references/verifier-compatibility.md.
8. **Cross-row verification**: When formulas reference other Task sheet rows, verify mapping logic matches task.
9. **Save and verify**: Save, reload, count formula cells.

## Critical: Reference Locking
**All workers fail on this in R2–R5.** See references/locking-patterns.md for the explicit table. Summary:

| Context | Pattern | Example |
|---------|---------|---------|
| INDEX/MATCH lookup range | Fully absolute | `$D$21:$D$38` |
| INDEX/MATCH row key | Column-absolute | `$D12` |
| Statistics range (MIN/MAX/MEDIAN) | Row-absolute | `H$35:H$40` |
| SUMPRODUCT values range | Row-absolute | `H$35:H$40` |
| SUMPRODUCT weights range | Row-absolute | `H$26:H$31` |
| Year header MATCH | Row-absolute | `H$10` |

## CRITICAL: MATCH Mode Must Be 0
`=MATCH(range,range)` defaults to sorted mode — fails on unsorted data.

| Wrong | Correct |
|-------|---------|
| `=MATCH($D12,Data!$D$21:$D$38)` | `=MATCH($D12,Data!$D$21:$D$38,0)` |

Validation script enforces this. Missing `,0` causes BLOCKING error.

## Verifier Compatibility & Value Evaluation
`openpyxl` **does not evaluate formulas**. It stores them as strings.
- **Formula-only verifiers**: Inject formulas. Validation passes.
- **Value-checking verifiers**: Loading with `data_only=True` returns `None` or stale cache.
- **Resolution**:
  1. Compute expected values in Python (`pandas`/`numpy`).
  2. Write values to target cells first.
  3. Overwrite with formulas if task requires them.
- See `references/verifier-compatibility.md` for detailed patterns.

## Cross-Row Formula Verification
When formulas reference other Task sheet rows (e.g., row 35 references rows 12, 19, 26):
- Verify row offset logic matches task requirements
- Use explicit row mapping: `fin_out_row = 12 + i`, `scrap_row = 19 + i`
- Manually trace one example to confirm correct entity mapping

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs.
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- Verifier's tolerance (often 1e-4) decides precision; skill gives full precision.

## Key Patterns
- **2D lookup**: `=INDEX(range,MATCH(row_key,row_range,0),MATCH(col_key,col_range,0))`
- **Weighted mean**: `=SUMPRODUCT(values,weights)/SUM(weights)`
- **Percentile**: `=PERCENTILE.INC(range,0.25)` (use `.INC`, not deprecated `QUARTILE`)

## Anti-patterns
- Using `data_only=True` for writing — strips formulas
- Missing `$` in lookup ranges — causes fill errors
- `=MATCH(range,range)` without `,0` — defaults to sorted, fails
- Using deprecated `QUARTILE()` — use `QUARTILE.INC()` or `PERCENTILE.INC`
- Hardcoding values instead of cell references
- Skipping blocking validation scripts
- Assuming `openpyxl` computes values for verifiers

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
- Formulas within Task sheet referencing other rows need explicit offset verification
- Example: row 35 → rows 12, 19, 26 for same entity

## Helper Scripts
- `scripts/validate_data_sheet.py` — Pre-flight Data sheet validation. BLOCKING.
- `scripts/validate_references.py` — Validates `$` locking and MATCH mode. BLOCKING.

Run BEFORE and AFTER formula injection. Script exits non-zero if issues detected.