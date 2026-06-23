---
name: excel-formula-automation
description: Construct and inject Excel formulas programmatically using openpyxl. Use for tasks requiring INDEX/MATCH lookups, statistical aggregations (MIN, MAX, MEDIAN, AVERAGE, PERCENTILE.INC), weighted calculations with SUMPRODUCT, or cross-sheet references. Trigger when you need to generate formulas that reference dynamic cell positions, build lookup tables, or compute derived metrics across multiple data blocks.
---

# Excel Formula Automation

Build complex Excel workbooks with formulas using openpyxl. Prioritize formula correctness through string verification and reference validation.

## Workflow (mandatory order)

1. **Explore structure first** - Load workbook with `openpyxl.load_workbook(path, data_only=False)`, identify sheet names, data ranges, header row location (usually row 4, NOT row 20), and key lookup keys (series codes, years, headers)
2. **Determine data structure** - Check if single-row-per-entity or multi-series-per-entity. For multi-series, MATCH on series code column (e.g., `*_REN_GEN`), NOT entity code
3. **Build formulas with correct reference locking** - Use `$` signs as specified in Reference Locking table below. THIS IS BLOCKING - missing `$` causes verifier failure
4. **Inject formulas** - Set `cell.value = formula_string` directly. Do not use `data_only=True`
5. **Run validation script** - Execute `scripts/validate_formulas.py` before saving. This script exits with code 1 on errors - BLOCKING GATE
6. **Save and verify** - Save workbook, reload, count formulas to verify injection count

## Reference Locking Table (MANDATORY)

| Context | Lock Pattern | Example | Why |
|---------|--------------|---------|-----|
| INDEX/MATCH lookup ranges | Fully absolute `$A$1:$B$10` | `Data!$H$21:$L$38` | Range must not shift when formula copies |
| Statistics ranges (MIN/MAX/MEDIAN/AVERAGE) | Row-absolute `A$1:A$10` | `H$35:H$40` | Column must adjust, rows must stay fixed |
| SUMPRODUCT/SUM weight ranges | Row-absolute `A$1:A$10` | `H$26:H$31` | Same as statistics - column adjusts, rows fixed |
| MATCH row key reference | Column-absolute `$A10` | `$D12` | Column fixed (series code), row adjusts per entity |
| MATCH column header reference | Row-absolute `A$10` | `H$10` | Row fixed (header), column adjusts per year |

**BLOCKING**: Run `scripts/validate_formulas.py` which detects missing `$` in required patterns and exits with error code 1.

## Critical Formula Patterns

### INDEX/MATCH Two-Dimensional Lookup (Multi-Series)
```python
# Pattern: Lookup value by series code (column D) and year header (row 10)
# CRITICAL: Series code column D is column-locked, year header row 10 is row-locked
formula = f"=INDEX(Data!$H$21:$L$38,MATCH($D{row},Data!$D$21:$D$38,0),MATCH({col}$10,Data!$H$21:$L$21,0))"
```
- `$D{row}`: Column D is locked, row number is dynamic
- `{col}$10`: Column letter is dynamic, row 10 is locked
- All lookup ranges fully locked: `Data!$H$21:$L$38`, `Data!$D$21:$D$38`, `Data!$H$21:$L$21`

### Statistical Aggregations on Formula Results
```python
# Row range must be row-absolute for fill-across columns
f"=MIN(H$35:H$40)"      # H is relative (fills to I, J), $35:$40 is fixed
f"=MAX(H$35:H$40)"
f"=MEDIAN(H$35:H$40)"
f"=AVERAGE(H$35:H$40)"
f"=PERCENTILE.INC(H$35:H$40,0.25)"  # CRITICAL: Use .INC suffix
```

### Weighted Mean with SUMPRODUCT
```python
# Value range and weight range must be row-absolute
f"=SUMPRODUCT(H$35:H$40,H$26:H$31)/SUM(H$26:H$31)"
```
- Ensure weight range has same row dimensions as value range

## Validation Checklist (before save)

- [ ] Formula strings match intended syntax exactly
- [ ] Cross-sheet references use correct sheet names with `!` separator
- [ ] **Absolute references (`$`) preserved in correct positions** - verify against Reference Locking Table
- [ ] Statistics use `PERCENTILE.INC` not deprecated `PERCENTILE` or `QUARTILE`
- [ ] Multi-series uses series code column (e.g., column D) for MATCH, not entity code
- [ ] Header row is row 4 (check actual workbook, do not assume row 20)

## Key Insight from Failures

**Visual verification of formula text is insufficient.** A formula that appears correct may:
1. Reference wrong rows or columns (offset by position)
2. Have missing `$` signs causing shift on copy
3. Use wrong function names (deprecated QUARTILE vs QUARTILE.INC)
4. Match on wrong key column (entity code vs series code for multi-series)

Always run the validation script and verify formula logic against task requirements character by character.

## Anti-Patterns

| Anti-Pattern | Correct Approach |
|--------------|------------------|
| `=MIN(H35:H40)` (no `$`) | `=MIN(H$35:H$40)` |
| `=PERCENTILE(range,0.25)` | `=PERCENTILE.INC(range,0.25)` |
| `=QUARTILE(range,1)` | `=PERCENTILE.INC(range,0.25)` or `=QUARTILE.INC(range,1)` |
| MATCH on entity code for multi-series | MATCH on series code column |
| Assume header row at row 20 | Check actual workbook - often row 4 |
| `data_only=True` when writing formulas | Keep `data_only=False` (default) |
| Visual inspection only | Run validation script + verify logic against task |

## Helper Scripts

- `scripts/formula_builder.py` - Functions for INDEX/MATCH, weighted mean, percentile
- `scripts/validate_formulas.py` - BLOCKING: Validates `$` locking, deprecated functions, exits 1 on error
- `scripts/excel_formula_utils.py` - Workbook inspection, cell range operations

Run validation script BEFORE saving:
```bash
python3 scripts/validate_formulas.py <workbook_path> <formula_range>
```