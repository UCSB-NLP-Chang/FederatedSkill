---
name: excel-formula-fill
description: Fill Excel workbook templates with formulas (not computed values) using openpyxl. Use when a task provides an .xlsx template with highlighted/empty cells that must contain formulas referencing a Data sheet or other source grid. Covers INDEX/MATCH lookups, derived calculations, statistics, and weighted aggregates.
---

# Excel Formula Fill

Fill Excel template cells with formula chains (not computed values) using openpyxl.

## When to use

- Task provides an `.xlsx` template with highlighted/empty cells that need formulas
- Formulas must reference a Data sheet or other source grid
- Calculation involves lookups, derived values, statistics, or weighted aggregates
- Original formatting (fills, borders, number formats) must be preserved

## Workflow

### 1. Inspect workbook structure

Load with `openpyxl.load_workbook(path)` (no `data_only`). Print sheet names, dimensions, and identify source/target sheets.

```python
import openpyxl
wb = openpyxl.load_workbook('input.xlsx')
print(f"Sheets: {wb.sheetnames}")
for name in wb.sheetnames:
    ws = wb[name]
    print(f"  {name}: {ws.dimensions}")
```

### 2. Map the Data sheet (source grid)

Identify the structure: header rows for column matching, key columns for row matching, data range bounds. Print sample values to confirm coordinates.

```python
ws_data = wb['Data']
# Print header row to identify year columns
for col in range(1, ws_data.max_column + 1):
    print(f"Col {col}: {ws_data.cell(row=4, column=col).value}")
# Print key column to identify entity codes
for row in range(1, min(10, ws_data.max_row + 1)):
    print(f"Row {row}: {ws_data.cell(row=row, column=4).value}")
```

### 3. Identify target cells in Task sheet

Cells with highlight fill (e.g., `FFF2CC` yellow) and `value=None` are fill targets. Group by block type.

```python
ws_task = wb['Task']
targets = []
for row in ws_task.iter_rows():
    for cell in row:
        if cell.fill and cell.fill.fgColor and 'FFF2CC' in str(cell.fill.fgColor.rgb):
            if cell.value is None:
                targets.append((cell.row, cell.column, cell.coordinate))
print(f"Targets: {len(targets)}")
```

### 4. Write formula chains by layer

Build formulas in dependency order. Set `cell.value = "=FORMULA()"` (string starting with `=`).

**Layer 1 — Lookups (INDEX/MATCH)**
```python
# 2D lookup: row key in column D, col key in row 10
for row, col, coord in lookup_targets:
    formula = f"=INDEX(Data!$H$21:$L$38,MATCH($D{row},Data!$D$21:$D$38,0),MATCH({openpyxl.utils.get_column_letter(col)}$10,Data!$H$4:$L$4,0))"
    ws_task[coord].value = formula
```

**Layer 2 — Derived calculations**
```python
# Percentage/gap: verify operand order against task description
formula = f"=(H{success_row}-H{fail_row})/H{cap_row}*100"
```

**Layer 3 — Statistics**
```python
formula = f"=MIN(H$35:H$40)"  # MAX, MEDIAN, AVERAGE, PERCENTILE.INC
```

**Layer 4 — Weighted mean**
```python
formula = f"=SUMPRODUCT(H$35:H$40,H$26:H$31)/SUM(H$26:H$31)"
```

### 5. Verify computed correctness (CRITICAL)

Before saving, manually compute 2-3 expected values using Python to catch logic errors:

```python
# Load Data sheet with actual values
wb_data = openpyxl.load_workbook('input.xlsx', data_only=True)
ws = wb_data['Data']
# Build lookup dict
data = {}
for r in range(21, 39):  # Adjust to your range
    key = ws.cell(row=r, column=4).value  # Entity code
    for c in range(8, 13):  # Columns H-L
        year = ws.cell(row=4, column=c).value
        data[(key, year)] = ws.cell(row=r, column=c).value

# Verify a lookup formula
expected = data[('EntityA', 2023)]
print(f"Expected for EntityA/2023: {expected}")
# Compare against what your INDEX/MATCH formula should return
```

### 6. Save

```python
wb.save('output.xlsx')
```

## Formula patterns

See `references/formula-patterns.md` for detailed INDEX/MATCH syntax, reference locking rules, and statistical formulas.

## Critical pitfalls

1. **Wrong operand order** — The #1 cause of failures. If task says "gap between X and Y", carefully determine whether X-Y or Y-X. If ambiguous, compute both and check sign against sample data or task context.

2. **Off-by-one in Data sheet range** — Print actual row numbers of headers and first/last data rows. A one-row shift makes every lookup wrong.

3. **Missing `$` in references** — Without `$`, copying formulas shifts references. Lock lookup ranges and key vectors with `$`.

4. **Overwriting formatting** — Setting `cell.value` preserves formatting. Avoid `ws.cell(row=r, column=c, value=...)` which may reset styles.

5. **Writing computed values instead of formulas** — Never write a number into a cell that should contain a formula string starting with `=`.

6. **Self-verification is unreliable** — Always compute expected values independently from the Data sheet.

## Output precision

When formulas produce numeric results, do NOT round or truncate intermediate values. The formula itself determines output; let Excel compute and the verifier check precision.

## Known invariants (by sub-task)

### weighted-cloud-reliability-calc (R0)
- Task sheet has blocks: lookup (INDEX/MATCH), derived (percentages), statistics (MIN/MAX/MEDIAN/AVERAGE/PERCENTILE.INC), weighted mean (SUMPRODUCT)
- Highlight color: `FFF2CC` (light yellow)
- Data sheet: entity codes in column D, year headers in row 4, numeric values in intersection range
- Operand order for "reliability gap": check task wording carefully; if "gap from X to Y", typically Y-X

## Anti-patterns

- **Do NOT use pandas** — It strips formatting, merges, and complex styles
- **Do NOT use `data_only=True` when writing formulas** — It returns cached values or None, not formula strings
- **Do NOT assume formula syntax without verification** — Re-read task for operand order and denominator

## Verification

Run `scripts/validate_formulas.py <input.xlsx> <output.xlsx>` to check:
- All highlighted cells contain formulas
- Number formats are preserved
- Formula breakdown by type

Then manually compute 2-3 expected values (step 5 above) to verify logic.
