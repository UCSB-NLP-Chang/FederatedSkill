---
name: excel-formula-fill
description: Fill Excel workbook templates with formulas (not computed values) using openpyxl. Use when a task provides an .xlsx template with highlighted/empty cells that must contain formulas referencing a Data sheet. Covers INDEX/MATCH lookups, derived calculations, statistics, and weighted aggregates. Handles both single-row-per-entity and multi-series-per-entity data structures.
---

# Excel Formula Fill

Fill Excel template cells with formula chains (not computed values) using openpyxl.

## When to use

- Task provides an `.xlsx` workbook with a "Data" sheet and a "Task" sheet
- Task sheet has highlighted/empty cells that must contain Excel formulas
- Formulas reference the Data sheet via lookups, arithmetic, stats, or weighted means

## Workflow

### 1. Inspect workbook structure

Load with `openpyxl.load_workbook(path)` (no `data_only`). Print sheet names, dimensions, and sample cell values/fills.

```python
import openpyxl
wb = openpyxl.load_workbook('input.xlsx')
for name in wb.sheetnames:
    ws = wb[name]
    print(f'{name}: dims={ws.dimensions}')
```

### 1.5 Verify Data sheet header row location (MANDATORY)

**CRITICAL**: Before building formulas, print the Data sheet structure to confirm header locations. Do NOT assume row 4 or row 20.

```python
ws_data = wb['Data']
print(f"Row 3: {[c.value for c in ws_data[3]]}")
print(f"Row 4: {[c.value for c in ws_data[4]]}")  # Usually year headers
print(f"Row 5: {[c.value for c in ws_data[5]]}")
print(f"Row 20: {[c.value for c in ws_data[20]]}")  # Check if data or headers
print(f"Row 21 (first data): {[c.value for c in ws_data[21]]}")
print(f"Col D sample: {[c.value for c in ws_data['D'][20:25]]}")  # Entity/series codes
```

**Decision rule**: If row 4 contains years (2021, 2022, etc.), use row 4 for MATCH. If row 4 is empty or contains other data, scan rows 1-10 for the actual header row.

Alternatively, run the diagnostic script:
```bash
python3 scripts/diagnose_data_sheet.py input.xlsx
```

### 2. Map the Data sheet

- Identify: header rows (year columns), key columns (entity codes, series codes), data range bounds.
- **CRITICAL**: Determine if Data has one row per entity or multiple series per entity.
- Print the actual row numbers of headers and first/last data rows.
- Print sample values to confirm coordinates — off-by-one in range bounds shifts every lookup.

```python
# Check for multi-series structure
ws_data = wb['Data']
series_codes = []
for row in ws_data.iter_rows(min_row=21, max_row=38, min_col=4, max_col=4):
    if row[0].value:
        series_codes.append(row[0].value)
unique_entities = set(c.split('_')[0] if '_' in c else c for c in series_codes)
if len(series_codes) > len(unique_entities):
    print(f"MULTI-SERIES DETECTED: {len(series_codes)} rows for {len(unique_entities)} entities")
    print("MATCH KEY MUST BE SERIES CODE, NOT ENTITY CODE")
else:
    print(f"Single-row-per-entity: {len(series_codes)} entities")
```

### 2.5 Verify row mapping alignment (MANDATORY — DO NOT SKIP)

Before writing any formulas, verify the Task sheet rows map correctly to Data sheet rows:

```python
# For multi-series data: check that series codes match
ws_task = wb['Task']
task_codes = []
for r in range(12, 30):  # sample Task sheet rows
    code = ws_task.cell(row=r, column=4).value  # column D
    if code:
        task_codes.append(code)
print(f"Task sheet codes: {task_codes}")
```

**Decision rules**:
- If Data has multiple series per entity (e.g., `CED_REN_GEN`, `CED_GRID_USE`), the lookup key MUST match on series code, not entity code
- If Task sheet series codes are in a different column than entity codes, use the series code column for MATCH
- Count total data rows and verify they match total Task sheet target rows

**STOP**: Do NOT proceed to step 3 if any of these checks fail. Re-scan Data sheet bounds first.

### 3. Identify target cells

Cells with highlight fill (e.g., `FFF2CC` yellow) and `value=None` are fill targets. Group by block type: lookup, derived, statistics, weighted-aggregate.

```python
ws_task = wb['Task']
targets = []
for row in ws_task.iter_rows(min_row=1, max_row=ws.max_row, max_col=ws.max_column):
    for c in row:
        if c.fill and c.fill.fgColor and 'FFF2CC' in str(c.fill.fgColor.rgb) and c.value is None:
            targets.append(c.coordinate)
print(f"Targets: {len(targets)}")
```

### 4. Write formulas by layer

Build formulas in dependency order. Set `cell.value = "=FORMULA()"` (string starting with `=`). Use `ws[cell_coord].value = formula` to preserve formatting.

**Layer 1 — Lookups (INDEX/MATCH)**

For single-row-per-entity:
```python
cell.value = f"=INDEX(Data!$H$21:$L$26,MATCH($D{row},Data!$D$21:$D$26,0),MATCH(H$10,Data!$H$4:$L$4,0))"
```

For multi-series-per-entity (series codes in column D of Task sheet):
```python
cell.value = f"=INDEX(Data!$H$21:$L$38,MATCH($D{row},Data!$D$21:$D$38,0),MATCH(H$10,Data!$H$4:$L$4,0))"
```

**Multi-series lookup rules**:
- If Task sheet column D contains series codes (e.g., `CED_REN_GEN`), match directly on column D
- If Task sheet column D contains entity codes but Data has series codes, you may need a different lookup column or row position mapping
- **Verify the MATCH key exists in the Data sheet lookup column before writing formulas**

Reference locking:
- Data range and lookup vectors: **fully absolute** (`$H$21:$L$38`, `$D$21:$D$38`)
- Row key: **column-absolute** (`$D12` — same column, varying row)
- Column key: **row-absolute** (`H$10` — same row, varying column)

**Layer 2 — Derived calculations**
```python
cell.value = f"=(H{r1}-H{r2})/H{r3}*100"
```
- **Verify operand order against the task description.** If task says "gap between X and Y", determine X−Y vs Y−X from context.
- **Verify the denominator** — is it a specific column or a total?

**Layer 3 — Statistics**
```python
cell.value = f"=MIN(H$35:H$40)"
cell.value = f"=MAX(H$35:H$40)"
cell.value = f"=MEDIAN(H$35:H$40)"
cell.value = f"=AVERAGE(H$35:H$40)"
cell.value = f"=PERCENTILE.INC(H$35:H$40,0.25)"
cell.value = f"=PERCENTILE.INC(H$35:H$40,0.75)"
```
- **CRITICAL**: Use row-absolute references (`H$35:H$40`) for all statistics ranges to prevent shift when copying.
- Verify range bounds match entity/series count exactly.

**Layer 4 — Weighted mean**
```python
cell.value = f"=SUMPRODUCT(H$35:H$40,H$26:H$31)/SUM(H$26:H$31)"
```
- **CRITICAL**: Use row-absolute references (`H$35:H$40`, `H$26:H$31`) for both value and weight ranges.
- ValueRange and WeightRange must have same dimensions.
- **Verify weight column**: weights must come from the correct block.

### 5. Validate before saving (MANDATORY)

```bash
python3 scripts/validate_formulas.py input.xlsx output.xlsx
```

Additionally: manually compute expected values from the Data sheet for at least one cell per formula block:

```python
# Manual verification example
import openpyxl
wb = openpyxl.load_workbook('input.xlsx', data_only=True)
ws_data = wb['Data']
# Look up a specific value and compute expected result
ren_gen = float(ws_data.cell(row=21, column=8).value)  # H21
grid_use = float(ws_data.cell(row=22, column=8).value)  # H22
baseline = float(ws_data.cell(row=23, column=8).value)  # H23
expected = (ren_gen - grid_use) / baseline * 100
print(f"Expected net balance: {expected}")
```

### 6. Save

```python
wb.save('output.xlsx')
```

## Pre-save checklist

- [ ] Data sheet header row verified (print row 4 and confirm years)
- [ ] Data sheet structure identified (single-row vs multi-series per entity)
- [ ] Lookup key column verified (series code vs entity code for multi-series)
- [ ] All lookup ranges use fully absolute references (`$A$1:$Z$99`)
- [ ] Derived formula operand order matches task wording
- [ ] Statistics ranges use row-absolute references (`H$35:H$40`)
- [ ] SUMPRODUCT ranges use row-absolute for both value and weight
- [ ] Weighted mean uses correct weight column
- [ ] At least one cell per block manually verified against Data sheet values

## Critical pitfalls

1. **Multi-series data mismatch** — If Data has multiple rows per entity (e.g., generation, consumption, demand), the lookup MUST match on series code, not entity code. A MATCH on entity code will return only the first matching row.
2. **Wrong header row assumption** — Year headers are usually in row 4, but always verify by printing. Never assume row 20 contains headers unless verified.
3. **Wrong operand order** — #1 source of sign errors. Compute both interpretations if unsure.
4. **Missing `$` in statistics/SUMPRODUCT ranges** — Without row-absolute (`$`), formulas shift incorrectly. Always use `H$35:H$40` format.
5. **Off-by-one in Data sheet ranges** — Print actual row numbers of headers and first/last data rows.
6. **Overwriting formatting** — `ws['A1'].value = v` preserves styles; `ws.cell(row=1, column=1, value=v)` may not.
7. **Writing computed values instead of formulas** — Cells must contain formula strings starting with `=`.
8. **Self-verification is unreliable** — Always compute expected values independently from the Data sheet.

## Anti-patterns

- **Do NOT** use `data_only=True` when writing formulas — returns cached values or None
- **Do NOT** use pandas — it strips formatting, merges, and complex styles
- **Do NOT** match on entity code when Data has series codes per entity
- **Do NOT** use relative ranges (`H35:H40`) in statistics or SUMPRODUCT — use row-absolute (`H$35:H$40`)
- **Do NOT** use `PERCENTILE.EXC` — use `PERCENTILE.INC`
- **Do NOT** proceed if row mapping alignment cannot be verified
- **Do NOT** assume header row location without printing and verifying

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### weighted-cloud-reliability-calc (R0)
- Single row per entity, entity codes in column D
- Year headers in row 4
- Operand order for "reliability gap": check task wording carefully

### weighted-hospital-bedflow-calc (R1)
- Single row per entity for each block (Admissions, Discharges, Bed Capacity are separate blocks)
- Net flow formula: (Admissions−Discharges)/Bed Capacity*100
- Weighted mean weighted by Bed Capacity

### weighted-campus-energy-balance-calc (R2)
- Multi-series per entity: 3 series × 6 entities = 18 data rows
- Series codes: `*_REN_GEN`, `*_GRID_USE`, `*_BASE_DEMAND`
- Year headers in row 4 (NOT row 20 — common error)
- Net renewable balance: (Renewable Generation − Grid Consumption) / Baseline Energy Demand * 100
- Statistics and weighted mean MUST use row-absolute ranges
- Weighted mean uses Baseline Energy Demand as weights

## Verification

Run `scripts/validate_formulas.py <input.xlsx> <output.xlsx>` to check formula presence and reference locking.

Run `scripts/diagnose_data_sheet.py <input.xlsx>` to verify Data sheet structure before writing formulas.

Then manually compute 2-3 expected values (step 5 above) to verify logic.

## Formula patterns

See `references/formula-patterns.md` for detailed INDEX/MATCH syntax, reference locking rules, and dynamic range detection code.
