---
name: template-formula-fill
description: Fill Excel workbook templates with formula chains (not computed values) using openpyxl. Use when a task provides an .xlsx template with highlighted/empty cells that must contain formulas referencing a Data sheet — covers INDEX/MATCH lookups, derived calculations, statistics, and weighted aggregates.
---

# Template Formula Fill

## When to use
- Task provides an `.xlsx` workbook with a "Data" sheet and a "Task" sheet.
- Task sheet has highlighted/empty cells that must contain Excel formulas.
- Formulas reference the Data sheet via lookups, arithmetic, stats, or weighted means.

## Workflow

### 1. Inspect workbook structure
```bash
python3 -c "
import openpyxl
wb = openpyxl.load_workbook('input.xlsx')
for name in wb.sheetnames:
    ws = wb[name]
    print(f'{name}: dims={ws.dimensions}')
"
```
- Load with `openpyxl.load_workbook(path)` — do NOT pass `data_only`.
- Print sheet names, dimensions, and sample cell values/fills/number_formats.

### 2. Map the Data sheet
- Identify: header rows (year columns), key columns (entity codes), data range bounds.
- Print the actual row numbers of headers and first/last data rows.
- **Print a few sample values** to confirm coordinates — off-by-one in range bounds shifts every lookup.

### 2.5 Verify entity count and block alignment
**CRITICAL STEP**: Before writing any formulas, count unique entities in the Data sheet and verify they match the Task sheet block sizes.
```python
import openpyxl
wb = openpyxl.load_workbook('input.xlsx')
ws_data = wb['Data']
entities = set()
for row in ws_data.iter_rows(min_row=21, max_row=38, min_col=2, max_col=2):
    if row[0].value:
        entities.add(row[0].value)
print(f"Unique entities in Data: {len(entities)} -> {sorted(entities)}")
```
- Count highlighted empty cells per block in the Task sheet.
- **Decision rule**: If `len(entities) != block_row_count`, re-scan Data sheet bounds. Do not proceed until counts match.
- Common mismatch causes: extra header/total rows in Task sheet, missing entities in Data sheet, or incorrect range assumptions.

### 3. Identify target cells
- Cells with highlight fill (e.g., `FFF2CC` yellow) and `value=None` are fill targets.
- Group them by block: lookup block, derived block, statistics block, weighted-aggregate block.
```python
targets = []
for row in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=ws.max_column):
    for c in row:
        if c.fill and c.fill.fgColor and 'FFF2CC' in str(c.fill.fgColor.rgb) and c.value is None:
            targets.append(c.coordinate)
```

### 4. Write formulas by layer

**Layer 1 — Lookups (INDEX/MATCH)**
```python
cell.value = f"=INDEX(Data!$H$21:$L$38,MATCH($D{row},Data!$D$21:$D$38,0),MATCH(H$10,Data!$H$4:$L$4,0))"
```
- Data range and lookup vectors: **fully absolute** (`$H$21:$L$38`, `$D$21:$D$38`).
- Row key: **column-absolute** (`$D12` — same column, varying row).
- Column key: **row-absolute** (`H$10` — same row, varying column).

**Layer 2 — Derived calculations**
```python
cell.value = f"=(H{r1}-H{r2})/H{r3}*100"
```
- **Verify operand order against the task description.** If task says "gap between X and Y", determine X−Y vs Y−X from context. If ambiguous, compute both and check sign against sample data.
- **Verify the denominator** — is it a specific column or a total?

**Layer 3 — Statistics**
```python
cell.value = f"=MIN(H{r1}:H{r2})"
cell.value = f"=MAX(H{r1}:H{r2})"
cell.value = f"=MEDIAN(H{r1}:H{r2})"
cell.value = f"=AVERAGE(H{r1}:H{r2})"
cell.value = f"=PERCENTILE.INC(H{r1}:H{r2},0.25)"
cell.value = f"=PERCENTILE.INC(H{r1}:H{r2},0.75)"
```
- **Verify range bounds match entity count exactly.** If 5 entities, range should be `H35:H39`, not `H35:H40`.

**Layer 4 — Weighted mean**
```python
cell.value = f"=SUMPRODUCT(H{v1}:H{v2},H{w1}:H{w2})/SUM(H{w1}:H{w2})"
```
- ValueRange and WeightRange must have same dimensions.
- **Verify weight column**: weights must come from the correct lookup block (e.g., bed capacity, not admissions).

### 5. Set formula values preserving formatting
- Use `ws[cell_coord].value = formula_string` — preserves existing style attributes.
- **Do NOT** use `ws.cell(row=r, column=c, value=v)` on cells with existing formatting — it may reset styles.
- If a cell needs a specific number format, set it explicitly: `cell.number_format = '0.00'`.

### 6. Validate before saving
```bash
python3 scripts/validate_formulas.py input.xlsx output.xlsx
```
- The script checks: all highlighted cells have formulas, formula types are present, number formats preserved.
- **Additionally**: manually compute expected values from the Data sheet for at least one cell per formula block and verify the formula would produce them. Self-verification by re-reading the saved file is unreliable.
- **Entity count check**: verify `len(unique_entities_in_data) == len(rows_in_derived_block) == len(rows_in_stats_range)`.

### 7. Save
```python
wb.save('output.xlsx')
```

## Pre-save checklist
- [ ] Entity count in Data sheet matches Task block row counts
- [ ] All lookup ranges use fully absolute references (`$A$1:$Z$99`)
- [ ] Derived formula operand order matches task wording (verify sign)
- [ ] Statistics range spans exactly the derived block rows (no extra/missing)
- [ ] Weighted mean uses correct weight column (capacity/population, not values)
- [ ] At least one cell per block manually verified against Data sheet values

## Critical Pitfalls

1. **Wrong operand order** — #1 source of sign errors. If task says "net reliability gap", verify whether (Successful−Failed) or (Failed−Successful). Compute both if unsure; check against sample data.
2. **Off-by-one in Data sheet ranges** — Print actual row numbers of headers and first/last data rows. A single off-by-one shifts every lookup result.
3. **Missing `$` in references** — Without `$`, copying formulas across columns/rows shifts references. Lock lookup ranges and key vectors with `$`.
4. **Overwriting formatting** — `ws['A1'].value = v` preserves styles; `ws.cell(row=1, column=1, value=v)` may not.
5. **Writing computed values instead of formulas** — Cells must contain formula strings starting with `=`, not Python-computed numbers.
6. **Self-verification is unreliable** — Always compute expected values independently from the Data sheet. The agent's own re-read of saved formulas does NOT confirm correctness.
7. **Hardcoded block sizes** — Never assume 5 or 6 rows. Count entities dynamically and verify against Task sheet highlights before writing formulas.

## Anti-patterns

- **Do not** use `data_only=True` when loading for formula writing (returns cached values or None, not formula strings).
- **Do not** use `pandas` for this task — it strips formatting, merges, and complex styles.
- **Do not** mix up `$D12` (column fixed) vs `D$12` (row fixed) vs `$D$12` (both fixed).
- **Do not** use `PERCENTILE.EXC` — use `PERCENTILE.INC` for standard statistical summaries.
- **Do not** proceed to formula writing if entity count mismatch is detected — re-scan Data sheet bounds first.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### weighted-{domain}-{metric}-calc (cloud-reliability, hospital-bedflow, etc.)
- Derived calculations: verify whether "gap" means (X−Y)/Capacity or (Y−X)/Capacity — re-read task wording. (R0: all workers got operand order wrong.)
- Data sheet range bounds: print actual header/data row numbers before building formulas. Off-by-one shifts every lookup. (R0: common failure across workers.)
- Highlighted cells with `value=None` are fill targets; do not fill cells that already have values.
- **Entity count must match**: `len(unique_entities_in_data) == rows_in_lookup_block == rows_in_derived_block == rows_in_stats_range`. Mismatch indicates wrong range bounds or extra header/total rows.
- Weighted mean denominator must be the weight column (capacity, population, etc.), not the value column.