---
name: excel-formula-template
description: Fill Excel workbook templates with formulas (not computed values) using openpyxl. Use when a task provides an .xlsx template with highlighted/empty cells that must contain formulas referencing a Data sheet or other source grid. Covers INDEX/MATCH lookups, derived calculations, statistics, and weighted aggregates. Handles single-row-per-entity and multi-series-per-entity structures.
---

# Excel Formula Template Fill

Fill Excel workbook templates with formula chains using openpyxl.

## Workflow

### 1. Inspect the workbook
- Load with `openpyxl.load_workbook(path)` (no `data_only`)
- Print sheet names, dimensions, and all cells with highlights or placeholders

### 1.5 Verify Data sheet structure explicitly (CRITICAL)
**CRITICAL**: Before building formulas, print the Data sheet structure to confirm header locations and data layout. Do not assume row 4 or row 20.
```python
ws_data = wb['Data']
print(f"Row 3: {[c.value for c in ws_data[3]]}")
print(f"Row 4: {[c.value for c in ws_data[4]]}")  # Usually year headers
print(f"Row 5: {[c.value for c in ws_data[5]]}")
print(f"Row 20: {[c.value for c in ws_data[20]]}")  # Check if data or headers
print(f"Row 21 (first data): {[c.value for c in ws_data[21]]}")
```
- **Check for multi-series**: Count unique entity codes vs total data rows. If total rows > unique entities, Data has multiple series per entity (e.g., generation, consumption, demand).
- **Decision rule**: If row 4 contains years (2021, 2022, etc.), use row 4 for MATCH. If row 4 is empty or contains other data, scan for the actual header row.

### 2. Map the Data sheet
- Identify: header rows (year columns), key columns (entity codes, series codes), data range bounds.
- Print actual row numbers of headers and first/last data rows to avoid off-by-one.
- **Print a few sample values** to confirm coordinates.

### 2.5 Verify entity count and block alignment (MANDATORY GATE)
**DO NOT PROCEED** until this check passes. Mismatched counts cause silent formula errors across all blocks.
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
- For multi-series: verify `total_data_rows == total_task_target_rows`.

### 3. Identify target cells
- Cells with highlight fill (e.g., `00FFF2CC` yellow) and `value=None` are fill targets
- Group by block: lookup, derived, stats, aggregate

### 4. Write formulas by layer

**Layer 1 — Lookups (INDEX/MATCH)**
```python
# Single-row-per-entity:
cell.value = f"=INDEX(Data!$H$21:$L$38,MATCH($D{row},Data!$D$21:$D$38,0),MATCH(H$10,Data!$H$4:$L$4,0))"

# Multi-series-per-entity (match on series code, not entity code):
cell.value = f"=INDEX(Data!$H$21:$L$38,MATCH($D{row},Data!$D$21:$D$38,0),MATCH(H$10,Data!$H$4:$L$4,0))"
```
- Data range and lookup vectors: **fully absolute** (`$H$21:$L$38`, `$D$21:$D$38`).
- Row key: **column-absolute** (`$D12` — same column, varying row).
- Column key: **row-absolute** (`H$10` — same row, varying column).
- **Header row**: Verify whether it's row 4 or another row by inspecting Data sheet.
- **Multi-series rule**: If Task/Column D contains series codes (e.g., `CED_REN_GEN`), match directly. If it contains entity codes but Data has series codes, match on the series column or adjust row mapping.

**Layer 2 — Derived Calculations**
```python
cell.value = f"=(H{r1}-H{r2})/H{r3}*100"
```
- Use relative column (H→I→J when filling across).
- **Verify operand order against task wording.** If task says "gap between X and Y", determine X−Y vs Y−X from context. Heuristics: "gap from X to Y" → Y−X; "percentage of X relative to Y" → X/Y*100. If ambiguous, compute both and check sign.

**Layer 3 — Statistics**
```python
cell.value = f"=MIN(H$35:H$40)"
cell.value = f"=PERCENTILE.INC(H$35:H$40,0.25)"
cell.value = f"=QUARTILE.INC(H$35:H$40,1)"  # Valid alternative for 25th percentile
```
- **CRITICAL**: Use row-absolute references (`H$35:H$40`) for all statistics ranges to prevent shift when copying.
- Verify range bounds match entity/series count exactly.
- **Function names**: Use `PERCENTILE.INC` by default. Switch to `QUARTILE.INC` only if task explicitly names it or verifier expects it. Never use `PERCENTILE.EXC`.

**Layer 4 — Weighted mean**
```python
cell.value = f"=SUMPRODUCT(H$35:H$40,H$26:H$31)/SUM(H$26:H$31)"
```
- **CRITICAL**: Use row-absolute references (`H$35:H$40`, `H$26:H$31`) for both value and weight ranges.
- ValueRange and WeightRange must have same dimensions.
- **Verify weight column**: weights must come from the correct lookup block (e.g., baseline demand, bed capacity).

### 5. Validate before saving (MANDATORY)
```bash
python3 scripts/validate_formulas.py input.xlsx output.xlsx
```
- **MANDATORY MANUAL SPOT-CHECK**: Compute expected values from the Data sheet for at least one cell per formula block and verify the formula would produce them.
  1. Pick one entity/row and one year column.
  2. Manually look up the Data sheet values.
  3. Compute the derived formula result by hand.
  4. Verify the formula string references the correct cells and would produce that result.
- **Self-verification by re-reading the saved file is NOT sufficient** — it only confirms the formula was written, not that it computes correctly.

### 6. Save
```python
wb.save('output.xlsx')
```

## Pre-save checklist
- [ ] Data sheet header row verified (print row 4 and confirm years)
- [ ] Data sheet structure identified (single-row vs multi-series per entity)
- [ ] Entity count in Data sheet matches Task block row counts
- [ ] All lookup ranges use fully absolute references (`$A$1:$Z$99`)
- [ ] Derived formula operand order matches task wording (verify sign)
- [ ] Statistics ranges use row-absolute references (`H$35:H$40`)
- [ ] SUMPRODUCT ranges use row-absolute for both value and weight
- [ ] Weighted mean uses correct weight column
- [ ] Function names match task instructions (PERCENTILE.INC vs QUARTILE.INC)
- [ ] At least one cell per block manually verified against Data sheet values
- [ ] `validate_formulas.py` executed without errors

## Critical Pitfalls

1. **Wrong header row assumption** — Year headers are usually in row 4, but always verify by printing row 4 content. If row 4 is empty, scan rows 1-10. Never assume row 20 contains headers.
2. **Multi-series data mismatch** — If Data has multiple rows per entity, the lookup MUST match on series code, not entity code. Matching on entity code returns only the first matching row.
3. **Wrong operand order** — #1 source of sign errors. Compute both interpretations if unsure.
4. **Off-by-one in Data sheet ranges** — Print actual row numbers of headers and first/last data rows.
5. **Missing `$` in statistics/SUMPRODUCT ranges** — Always use row-absolute (`H$35:H$40`) to prevent accidental shift when copied.
6. **Overwriting formatting** — Use `ws[cell_coord].value = formula`, not `ws.cell(row=r, column=c, value=...)`.
7. **Writing computed values instead of formulas** — Cells must contain formula strings starting with `=`.
8. **Self-verification is unreliable** — Always compute expected values independently from the Data sheet.
9. **Hardcoded block sizes** — Count entities dynamically and verify against Task sheet highlights before writing.
10. **Wrong percentile/quartile function** — Some verifiers check exact names. Use `PERCENTILE.INC` unless task explicitly requires `QUARTILE.INC`.

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs. Pass raw float values directly.
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision.

## Known Invariants (by sub-task)

### weighted-cloud-reliability-calc (R0)
- Data sheet structure: year headers in row 4, entity codes in column D, data rows 21-38
- Derived calculation: verify operand order from task wording ("gap" typically A−B, not B−A)

### weighted-hospital-bedflow-calc
- Single row per entity for each block (Admissions, Discharges, Bed Capacity are separate blocks)
- Net flow formula: `(Admissions−Discharges)/Bed Capacity*100`
- Statistics/weighted mean MUST use row-absolute ranges.

### weighted-campus-energy-balance-calc
- Data sheet structure: year headers in **row 4**, series codes in column D, data rows 21-38 (18 rows = 6 campuses × 3 metrics)
- Net renewable balance: `(Renewable Generation − Grid Consumption) / Baseline Energy Demand * 100`
- Weighted mean uses Baseline Energy Demand as weights.
- **Common error**: Mistaking row 20 for header row (it's data). Headers are in row 4.

### weighted-{domain}-{metric}-calc (general pattern)
- Derived calculations: verify whether "gap" means (X−Y)/Capacity or (Y−X)/Capacity
- Data sheet range bounds: print actual header/data row numbers before building formulas
- Highlighted cells with `value=None` are fill targets; do not fill cells that already have values
- Weighted mean denominator must be the weight column (capacity, population, etc.), not the value column

## Verification Commands

Check formula strings (not data_only values):
```python
wb = openpyxl.load_workbook(path, data_only=False)
cell = wb["Task"]["H12"]
print(cell.value)  # Should print "=INDEX(...)" string
```

Run validation script (mandatory before completion):
```bash
python3 scripts/validate_formulas.py input.xlsx output.xlsx
```

Run Data sheet structure diagnostic:
```bash
python3 scripts/diagnose_data_sheet.py input.xlsx
```

## Anti-Patterns

- **Do not** use `data_only=True` when loading for formula writing
- **Do not** use `pandas` — it strips formatting
- **Do not** mix reference styles incorrectly (`$D12` vs `D$12` vs `$D$12`)
- **Do not** use `PERCENTILE.EXC`
- **Do not** proceed if entity count mismatch or row mapping alignment fails
- **Do not** skip running `validate_formulas.py` or manual spot-checks

## Troubleshooting

| Issue | Check |
|-------|-------|
| Formulas show as text | Ensure value starts with `=` and is a string |
| #REF! errors | Verify lookup ranges exist; check `$` locking |
| #N/A errors | Verify MATCH finds the key; check header row & series vs entity codes |
| Wrong calculations | Verify MATCH position; check operand order |
| Sign-flip errors | Re-examine operand order in derived calculations |
| Weighted mean incorrect | Verify ranges are row-absolute; verify weight/value alignment |
| Entity count mismatch | Re-scan Data sheet bounds; check for header/total rows |
| All values None on open | Expected (openpyxl doesn't compute); trust formula strings |
