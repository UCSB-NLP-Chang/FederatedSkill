---
name: excel-formula-template
description: Fill Excel workbook templates with formulas (not computed values) using openpyxl. Use when a task provides an .xlsx template with highlighted/empty cells that must contain formulas referencing a Data sheet or other source grid. Covers INDEX/MATCH lookups, derived calculations, statistics, and weighted aggregates.
---

# Excel Formula Template Fill

Fill Excel workbook templates with formula chains using openpyxl.

## Workflow

1. **Inspect the workbook**
   - Load with `openpyxl.load_workbook(path)` (no `data_only`)
   - Print sheet names, dimensions, and all cells with highlights or placeholders

2. **Map the Data sheet**
   - Identify source grid: header rows for column matching, key columns for row matching, data range bounds
   - Print actual row numbers of headers and first/last data rows to avoid off-by-one

3. **Identify target cells**
   - Cells with highlight fill (e.g., `00FFF2CC` yellow) and `value=None` are fill targets
   - Group by block: lookup, derived, stats, aggregate

4. **Write formulas programmatically**
   - Set `cell.value = "=FORMULA()"` as string (not computed)
   - Use f-strings to inject dynamic ranges
   - Preserve formatting: set `cell.value` directly, do NOT use `ws.cell(row=r, column=c, value=...)`

5. **Validate before saving**
   - Reload saved file and verify formula strings exist (not computed values)
   - Run `scripts/validate_formulas.py` to check presence and formatting
   - **Manual spot-check**: compute expected values from Data sheet and compare

## Formula Layers

### Layer 1: 2D Lookup (INDEX/MATCH)
```python
f"=INDEX(Data!$H$21:$L$38,MATCH($D{row},Data!$D$21:$D$38,0),MATCH(H$10,Data!$H$4:$L$4,0))"
```
- Row key: column-absolute `$D{row}` (same column, varying row)
- Column key: row-absolute `H$10` (same row, varying column)
- Data range and lookup vectors: fully absolute `$`

### Layer 2: Derived Calculations
```python
f"=(H{success_row}-H{fail_row})/H{cap_row}*100"
```

### Layer 3: Statistics
```python
f"=MIN(H$35:H$40)"
f"=PERCENTILE.INC(H$35:H$40,0.25)"
```

### Layer 4: Weighted Aggregates
```python
f"=SUMPRODUCT(H$35:H$40,H$26:H$31)/SUM(H$26:H$31)"
```

## Critical Pitfalls

1. **Wrong operand order** — If task says "net reliability gap", determine: (Successful−Failed) or (Failed−Successful)?
   - Re-read task wording carefully
   - If ambiguous, compute both and check which matches sample data sign
   - Task-memory note: R0 verifier failures were sign-flip errors from wrong operand order

2. **Off-by-one in Data sheet ranges** — Print actual row numbers:
   - Header row location (e.g., row 4 for years)
   - First data row (e.g., row 21)
   - Last data row (e.g., row 38)
   - Off-by-one shifts every lookup result

3. **Missing $ in references** — Without `$`, copying formulas shifts references incorrectly:
   - Lock lookup range: `$H$21:$L$38`
   - Lock key vectors: `$D$21:$D$38`, `$H$4:$L$4`

4. **Overwriting formatting** — Use `cell.value = formula`, not `ws.cell(row=r, column=c, value=...)`

5. **Not validating** — Agent's self-check is unreliable. Manually compute expected values.

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision

## Known Invariants (by sub-task)

### weighted-cloud-reliability-calc (R0)
- Data sheet structure: year headers in row 4, entity codes in column D, data rows 21-38
- Task sheet highlight color: `FFF2CC` (yellow)
- Derived calculation: verify operand order from task wording ("gap" typically A−B, not B−A)

## Verification Commands

Check formula strings (not data_only values):
```python
wb = openpyxl.load_workbook(path, data_only=False)
cell = wb["Task"]["H12"]
print(cell.value)  # Should print "=INDEX(...)" string
```

Run validation script:
```bash
python3 scripts/validate_formulas.py input.xlsx output.xlsx
```

## Anti-Patterns

- **Do not** use `data_only=True` when verifying (returns cached values or None)
- **Do not** mix reference styles: `$D12` (column fixed) vs `D$12` (row fixed) vs `$D$12` (both)
- **Do not** use `pandas` for this task — it strips formatting
- **Do not** write computed numbers into formula cells

## Troubleshooting

| Issue | Check |
|-------|-------|
| Formulas show as text | Ensure value starts with `=` and is a string |
| #REF! errors | Verify lookup ranges exist; check `$` locking |
| Wrong calculations | Verify MATCH position; check year headers align |
| Sign-flip errors | Re-examine operand order in derived calculations |
