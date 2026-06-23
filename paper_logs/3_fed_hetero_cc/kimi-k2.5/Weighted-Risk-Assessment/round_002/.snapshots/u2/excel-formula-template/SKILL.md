---
name: excel-formula-template
description: Fill Excel workbook templates with formulas (not computed values) using openpyxl. Use when a task provides an .xlsx template with highlighted/empty cells that must contain formulas referencing a Data sheet or other source grid. Covers INDEX/MATCH lookups, derived calculations, statistics, and weighted aggregates.
---

# Excel Formula Template Fill

Fill Excel workbook templates with formula chains using openpyxl.

## Workflow

### 1. Inspect the workbook
- Load with `openpyxl.load_workbook(path)` (no `data_only`)
- Print sheet names, dimensions, and all cells with highlights or placeholders

### 2. Map the Data sheet
- Identify source grid: header rows for column matching, key columns for row matching, data range bounds
- Print actual row numbers of headers and first/last data rows to avoid off-by-one
- **Print a few sample values** to confirm coordinates

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
- Count highlighted empty cells per block in the Task sheet
- **Decision rule**: If `len(entities) != block_row_count`, re-scan Data sheet bounds. Do not proceed until counts match.
- Common mismatch causes: extra header/total rows in Task sheet, missing entities in Data sheet, or incorrect range assumptions.

### 3. Identify target cells
- Cells with highlight fill (e.g., `00FFF2CC` yellow) and `value=None` are fill targets
- Group by block: lookup, derived, stats, aggregate

### 4. Write formulas programmatically
- Set `cell.value = "=FORMULA()"` as string (not computed)
- Use f-strings to inject dynamic ranges
- **Lock ranges appropriately**: Use `$` for rows that must not shift (e.g., `$35:$40`) even if filling by script
- Preserve formatting: set `cell.value` directly, do NOT use `ws.cell(row=r, column=c, value=...)`

### 5. Validate before saving
- **MANDATORY**: Run `python3 scripts/validate_formulas.py input.xlsx output.xlsx`
- Reload saved file and verify formula strings exist (not computed values)
- Manually spot-check: compute expected values from Data sheet and compare

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
f"=(H{admit_row}-H{discharge_row})/H{bed_row}*100"
```
- Use relative column (H→I→J when filling across)
- Verify operand order against task wording (see Critical Pitfalls)

### Layer 3: Statistics
```python
f"=MIN(H$35:H$40)"
f"=PERCENTILE.INC(H$35:H$40,0.25)"
```
- Use row-absolute (`$35:$40`) to lock the data block rows
- **Verify range bounds match entity count exactly** — if 5 entities, range should be `H35:H39`, not `H35:H40`

### Layer 4: Weighted Aggregates
```python
f"=SUMPRODUCT(H$35:H$40,H$26:H$31)/SUM(H$26:H$31)"
```
- **CRITICAL**: Use row-absolute references (`$35:$40`, `$26:$31`) for both ranges
- Column remains relative (H→I) to copy across years
- Weight range must align exactly with value range dimensions
- **Verify weight column**: weights must come from the correct lookup block (e.g., bed capacity, not admissions)

## Pre-save checklist
- [ ] Entity count in Data sheet matches Task block row counts
- [ ] All lookup ranges use fully absolute references (`$A$1:$Z$99`)
- [ ] Derived formula operand order matches task wording (verify sign)
- [ ] Statistics range spans exactly the derived block rows (no extra/missing)
- [ ] Weighted mean uses correct weight column (capacity/population, not values)
- [ ] SUMPRODUCT ranges use row-absolute `$`
- [ ] At least one cell per block manually verified against Data sheet values
- [ ] `validate_formulas.py` executed without errors

## Critical Pitfalls

1. **Wrong operand order** — If task says "net reliability gap" or "net patient flow", determine direction:
   - "Net flow" usually implies (Inflow − Outflow) or (Admissions − Discharges), but verify expected sign from context
   - If ambiguous, compute both orderings and check which matches expected sample sign
   - Task-memory: R0 failures were sign-flip errors; hospital-bedflow specifically uses (Admissions−Discharges)/Capacity

2. **Off-by-one in Data sheet ranges** — Print actual row numbers:
   - Header row location (e.g., row 4 for years)
   - First data row (e.g., row 21)
   - Last data row (e.g., row 38)
   - Off-by-one shifts every lookup result

3. **Missing $ in references** — Without `$`, copying formulas shifts references incorrectly:
   - Lock lookup range: `$H$21:$L$38`
   - Lock key vectors: `$D$21:$D$38`, `$H$4:$L$4`
   - Lock weighted aggregate data blocks: `H$35:H$40` (row-absolute, column-relative)

4. **Overwriting formatting** — Use `cell.value = formula`, not `ws.cell(row=r, column=c, value=...)`

5. **Not validating** — Agent's self-check is unreliable. Manually compute expected values.

6. **Unlocked weighted ranges** — SUMPRODUCT ranges must be row-absolute (`$`) to prevent accidental shift if the formula cell is copied vertically within the sheet.

7. **Hardcoded block sizes** — Never assume 5 or 6 rows. Count entities dynamically (Step 2.5) and verify against Task sheet highlights before writing formulas.

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

### weighted-hospital-bedflow-calc
- Data sheet structure: year headers in row 4, series codes in column D, data rows 21-38
- Task sheet blocks:
  - Admissions: rows 12-17
  - Discharges: rows 19-24
  - Bed Capacity: rows 26-31
  - Net Patient Flow: rows 35-40 (formula: `=(Admissions−Discharges)/Bed Capacity*100`)
  - Statistics: rows 42-47 (MIN, MAX, MEDIAN, AVERAGE, PERCENTILE.INC 25%, PERCENTILE.INC 75%)
  - Weighted Mean: row 50 (weighted by Bed Capacity rows 26-31)
- **Reference locking**: Net flow formulas use relative columns/rows (filled per-cell), but statistics and weighted means MUST use row-absolute ranges (`H$35:H$40`, `H$26:H$31`)
- **Entity count must match**: `len(unique_entities_in_data) == rows_in_lookup_block == rows_in_derived_block == rows_in_stats_range`

### weighted-{domain}-{metric}-calc (general pattern)
- Derived calculations: verify whether "gap" means (X−Y)/Capacity or (Y−X)/Capacity — re-read task wording
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

Manual calculation check:
```python
# Load Data sheet values manually and verify derived calculations
# Example: (612.5 - 580.1) / 720 * 100 == 4.5
```

## Anti-Patterns

- **Do not** use `data_only=True` when verifying (returns cached values or None)
- **Do not** mix reference styles: `$D12` (column fixed) vs `D$12` (row fixed) vs `$D$12` (both)
- **Do not** use `pandas` for this task — it strips formatting
- **Do not** write computed numbers into formula cells
- **Do not** skip running `validate_formulas.py` even if output looks correct
- **Do not** proceed to formula writing if entity count mismatch is detected — re-scan Data sheet bounds first

## Troubleshooting

| Issue | Check |
|-------|-------|
| Formulas show as text | Ensure value starts with `=` and is a string |
| #REF! errors | Verify lookup ranges exist; check `$` locking |
| Wrong calculations | Verify MATCH position; check year headers align |
| Sign-flip errors | Re-examine operand order in derived calculations |
| Weighted mean incorrect | Verify ranges are row-absolute (`$`); verify weight/value alignment |
| Verifier rejects file | Run validation script; check for placeholder values instead of formulas |
| Entity count mismatch | Re-scan Data sheet bounds; check for header/total rows in Task sheet |
