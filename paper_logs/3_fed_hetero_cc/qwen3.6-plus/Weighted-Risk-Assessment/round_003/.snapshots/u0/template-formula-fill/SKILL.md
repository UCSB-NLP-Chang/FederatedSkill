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

### 1.5 Verify Data sheet structure explicitly
**CRITICAL**: Before building formulas, print the Data sheet structure to confirm header locations. Do not assume row 4 or row 20.
```python
ws_data = wb['Data']
print(f"Row 4: {[c.value for c in ws_data[4]]}")  # Usually year headers
print(f"Row 20: {[c.value for c in ws_data[20]]}")  # Check if data or headers
print(f"Row 21 (first data): {[c.value for c in ws_data[21]]}")
```
**Decision rule**: If row 4 contains years (2021, 2022, etc.), use row 4 for MATCH. If row 4 is empty, scan rows 1-10. Never assume row 20 contains headers unless verified. (Run `python3 scripts/diagnose_data_sheet.py input.xlsx` for automated check.)

### 2. Map the Data sheet & Detect Structure
- Identify: header rows (year columns), key columns (entity codes, series codes), data range bounds.
- **CRITICAL**: Determine if Data has one row per entity or multiple series per entity (e.g., `CED_REN_GEN`, `CED_GRID_USE`).
- Print actual row numbers of headers and first/last data rows.
- **Print sample values** to confirm coordinates — off-by-one shifts every lookup.

### 2.5 Verify entity count and block alignment (MANDATORY GATE)
**DO NOT PROCEED** until this check passes. Mismatched entity counts cause silent formula errors across all blocks.
```python
import openpyxl
wb = openpyxl.load_workbook('input.xlsx')
ws_data = wb['Data']
entities = set()
series_codes = []
for row in ws_data.iter_rows(min_row=21, max_row=38, min_col=2, max_col=4):
    if row[0].value: entities.add(row[0].value)
    if row[2].value: series_codes.append(row[2].value)
print(f"Unique entities: {len(entities)} | Total rows: {len(series_codes)}")
if len(series_codes) > len(entities):
    print(f"MULTI-SERIES DETECTED: {len(series_codes)//len(entities)} series/entity. Match on series code, NOT entity code.")
```
- Count highlighted empty cells per block in the Task sheet.
- **Decision rule**: If `len(entities) != block_row_count` (for single-series) or `total_data_rows != total_task_rows`, re-scan Data sheet bounds. Do not proceed until counts match.

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
- Row key: **column-absolute** (`$D{row}` — same column, varying row).
- Column key: **row-absolute** (`H$10` — same row, varying column).
- **Multi-series rule**: If Task column D contains series codes, match directly. If Data has multiple rows per entity, MATCH on entity code returns the first match — you MUST match on series code.

**Layer 2 — Derived calculations**
```python
cell.value = f"=(H{r1}-H{r2})/H{r3}*100"
```
- **Verify operand order against the task description.** If task says "gap between X and Y", determine X−Y vs Y−X from context. If ambiguous, compute both and check sign against sample data.
- **Verify the denominator** — is it a specific column or a total?

**Layer 3 — Statistics**
```python
cell.value = f"=MIN(H$35:H$40)"
cell.value = f"=MAX(H$35:H$40)"
cell.value = f"=MEDIAN(H$35:H$40)"
cell.value = f"=AVERAGE(H$35:H$40)"
```
**Percentile/Quartile variants** — check task instructions for exact function name:
```python
# Standard (preferred):
cell.value = f"=PERCENTILE.INC(H$35:H$40,0.25)"
cell.value = f"=PERCENTILE.INC(H$35:H$40,0.75)"
# Alternative (valid Excel equivalent):
cell.value = f"=QUARTILE.INC(H$35:H$40,1)"  # 25th percentile
cell.value = f"=QUARTILE.INC(H$35:H$40,3)"  # 75th percentile
```
- **CRITICAL**: Use row-absolute references (`H$35:H$40`) for all statistics ranges to prevent shift when copying.
- **Verify range bounds match entity count exactly.**
- **Decision rule**: Use `PERCENTILE.INC` by default; switch to `QUARTILE.INC` only if task explicitly names it. Verifiers may check exact function names.

**Layer 4 — Weighted mean**
```python
cell.value = f"=SUMPRODUCT(H$35:H$40,H$26:H$31)/SUM(H$26:H$31)"
```
- ValueRange and WeightRange must have same dimensions.
- **CRITICAL**: Use row-absolute references (`H$35:H$40`) for both ranges.
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
- **MANDATORY MANUAL SPOT-CHECK**: Compute expected values from the Data sheet for at least one cell per formula block and verify the formula would produce them.

**Spot-check workflow**:
1. Pick one entity/series (e.g., row 12) and one year column (e.g., H).
2. Manually look up the Data sheet values.
3. Compute the derived formula result by hand.
4. Verify the formula string references the correct cells and would produce that result.
5. Repeat for at least one stats cell and the weighted mean cell.
**Self-verification by re-reading the saved file is NOT sufficient** — it only confirms the formula was written, not that it computes correctly.

### 7. Save
```python
wb.save('output.xlsx')
```

## Pre-save checklist
- [ ] Data sheet header row verified (row 4 vs 20)
- [ ] Entity count & multi-series structure identified
- [ ] Lookup key column verified (series code vs entity code)
- [ ] Entity count in Data matches Task block row counts (MANDATORY GATE)
- [ ] All lookup ranges use fully absolute references (`$A$1:$Z$99`)
- [ ] Derived formula operand order matches task wording (verify sign)
- [ ] Statistics & SUMPRODUCT ranges use row-absolute references (`H$35:H$40`)
- [ ] Weighted mean uses correct weight column
- [ ] Function names match task instructions (PERCENTILE.INC vs QUARTILE.INC)
- [ ] At least one cell per block manually verified against Data sheet values

## Critical Pitfalls

1. **Wrong header row assumption** — Year headers are usually in row 4, but always verify. If row 4 is empty, scan rows 1-10. Never assume row 20 contains headers.
2. **Multi-series data mismatch** — If Data has multiple rows per entity, MATCH on entity code returns the first matching row only. You MUST match on series code.
3. **Wrong operand order** — #1 source of sign errors. Compute both interpretations if unsure.
4. **Missing `$` in statistics/SUMPRODUCT ranges** — Without row-absolute (`$`), formulas shift incorrectly. Always use `H$35:H$40` format.
5. **Off-by-one in Data sheet ranges** — Print actual row numbers. A single off-by-one shifts every lookup result.
6. **Missing `$` in lookup references** — Lock lookup ranges and key vectors with `$`.
7. **Overwriting formatting** — `ws['A1'].value = v` preserves styles; `ws.cell(row=r, column=c, value=v)` may not.
8. **Writing computed values instead of formulas** — Cells must contain formula strings starting with `=`.
9. **Skipping entity count verification** — This is a mandatory gate. Proceeding with mismatched counts guarantees formula errors.
10. **Wrong percentile/quartile function** — Use `PERCENTILE.INC` by default; switch to `QUARTILE.INC` only if explicitly required. Verifiers may check exact names.

## Anti-patterns

- **Do not** use `data_only=True` when loading for formula writing.
- **Do not** use `pandas` — it strips formatting.
- **Do not** mix up `$D12` (column fixed) vs `D$12` (row fixed) vs `$D$12` (both fixed).
- **Do not** use `PERCENTILE.EXC` — use `PERCENTILE.INC`.
- **Do not** proceed if row mapping alignment or entity count mismatch is detected.
- **Do not** rely solely on `validate_formulas.py` — it checks structure, not computed correctness.
- **Do not** use relative ranges (`H35:H40`) in statistics or SUMPRODUCT — use row-absolute.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs. Pass raw float values directly.
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision.

## Known invariants (by sub-task)

### weighted-cloud-reliability-calc
- Single row per entity, entity codes in column D, year headers in row 4.
- Derived calculation: verify operand order ("gap" typically A−B).

### weighted-hospital-bedflow-calc
- Task blocks: Admissions (12-17), Discharges (19-24), Bed Capacity (26-31), Net Flow (35-40), Stats (42-47), Weighted Mean (50).
- Net flow formula: `(Admissions−Discharges)/Bed Capacity*100`.
- Statistics & weighted mean MUST use row-absolute ranges. Weighted by Bed Capacity.

### weighted-campus-energy-balance-calc
- Multi-series per entity: 3 series × 6 entities = 18 data rows. Series codes in column D.
- Year headers in **row 4** (NOT row 20).
- Blocks: Renewable Gen (12-17), Grid Cons (19-24), Baseline Demand (26-31), Net Balance (35-40), Stats (42-47), Weighted Mean (50).
- Net balance: `(Renewable−Grid)/Baseline*100`.
- Weighted mean uses Baseline Energy Demand as weights. MUST use row-absolute ranges.

### weighted-{domain}-{metric}-calc (general pattern)
- Derived calculations: verify whether "gap" means (X−Y)/Capacity or (Y−X)/Capacity.
- Data sheet range bounds: print actual header/data row numbers before building formulas.
- Highlighted cells with `value=None` are fill targets.
- Weighted mean denominator must be the weight column, not the value column.