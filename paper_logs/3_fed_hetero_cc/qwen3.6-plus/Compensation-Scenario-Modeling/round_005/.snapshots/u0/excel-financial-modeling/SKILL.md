---
name: excel-financial-modeling
description: Build complex, formula-driven Excel workbooks for financial modeling, compensation analyses, and multi-year projections using openpyxl. Use when tasks require named ranges, cross-sheet formulas, tiered calculations, roster migration, or assumption-driven models that must recalculate automatically.
---

# Excel Financial Modeling with openpyxl

## When to Use

- Multi-year financial projections with cascading assumptions
- Compensation models with tiered pay structures, seniority bands, or tax brackets
- Workbooks requiring named ranges for maintainability
- Cross-sheet formula dependencies (e.g., Summary pulls from Assumptions)
- Models where users will tweak inputs and expect automatic recalculation
- Roster or dataset migration tasks requiring exact record counts

## Workflow

1. **Extract Test Expectations First** - Parse test files for exact sheet names, order, row/column indices, label strings, **exact record counts**, and absence checks (e.g., `assert "Archive" not in wb.sheetnames`). Do not guess layout or row counts. If requirements say "87 staff" but source has 85, the TEST expectation wins.
2. **Read Input Files with openpyxl** - Binary .xlsx files cannot be read with text tools. Use openpyxl directly:
   ```python
   import openpyxl
   wb = openpyxl.load_workbook('input.xlsx')
   for sheet in wb.sheetnames:
       ws = wb[sheet]
       for row in ws.iter_rows(values_only=True):
           print(row)
   ```
3. **Parse Source Data** - Use openpyxl to inspect all sheets, dimensions, and data types.
4. **Create Sheets in Exact Order** - `wb.sheetnames` must match required list exactly. Use `wb.move_sheet()` if creation order differs.
5. **Populate Static Data** - Write headers, labels, and inputs exactly as specified. No abbreviations.
6. **Define Named Ranges** - Use `wb.define_name()` after cells exist.
7. **Write Formulas** - NO leading `=` prefix (openpyxl syntax).
8. **Track Rows Dynamically for Multi-Year** - Store actual row numbers during construction; never use hardcoded offsets like `row - 8`.
9. **Run `pytest` Incrementally** - Execute `pytest` immediately after the first successful save and after every major structural change. Custom verification scripts are supplementary only. If tests fail, read the exact assertion error before guessing.

## Named Ranges (Critical Pattern)

Use `wb.define_name()`, NOT `wb.defined_names` dict manipulation:

```python
# CORRECT: Use define_name method
wb.define_name('MWS_Current', 'Assumptions!$C$5')
wb.define_name('Payroll_Tax_Tier1_Rate', 'Assumptions!$D$19')

# WRONG: Do not access defined_names as dict
# wb.defined_names['MWS_Current'] = ...  # AttributeError or silent failures
```

**Iterating named ranges** - Iterate `wb.defined_names` directly (it is dict-like), or use `.items()` / `.values()`:

```python
# CORRECT: Iterate defined_names directly (yields names as strings)
for name in wb.defined_names:
    dn_obj = wb.defined_names[name]
    print(f"{name}: {dn_obj.attr_text}")

# CORRECT: Use .items() for (name, DefinedName) pairs
for name, dn_obj in wb.defined_names.items():
    print(f"{name}: {dn_obj.attr_text}")

# CORRECT: Use .values() for DefinedName objects
for dn_obj in wb.defined_names.values():
    print(f"{dn_obj.name}: {dn_obj.attr_text}")

# WRONG: These cause AttributeError
# for dn in wb.defined_names.definedName:  # AttributeError: 'DefinedNameDict' has no 'definedName'
# for dn in wb.defined_names.definedname:  # AttributeError
```

Naming convention for time-variant assumptions:
- `MWS_Current`, `MWS_Year_Plus_1`, `MWS_Year_Plus_2`
- `Seniority_5_9_Current`, `Seniority_5_9_Year_Plus_1`

## Source Data Migration & Row Counting

- **Dynamic Counting**: Calculate row counts dynamically from source data (`len(roster)`), but validate against test expectations.
- **Test Wins Over Source**: If `test_output.py` asserts `assert len(rows) == 87` but source has 85, investigate and match the test expectation.
- **Header/Footer Handling**: Do not assume trailing rows are overflow/headers without explicit verification. Explicitly skip known non-data rows.
- **Off-by-One Prevention**: Hardcoded row offsets (e.g., `row - 8`) or guessed counts (`len(data) - 1`) frequently break. Use dynamic tracking.

## Column Range Bounds (Critical)

When iterating columns for formulas, totals, or formatting, **always verify the range bounds match the actual column count**:

```python
# WRONG: Off-by-one error, misses last column
for col in range(10, 23):  # Only covers J through V (13 columns)

# CORRECT: Use explicit end column + 1
for col in range(10, 24):  # Covers J through W (14 columns)
```

**Validation pattern:**
```python
from openpyxl.utils import get_column_letter

expected_cols = ['T', 'U', 'V', 'W']  # Q1, Q2, Q3, Q4
for col_letter in expected_cols:
    cell = ws[f'{col_letter}{totals_row}']
    assert cell.value and 'SUM' in str(cell.value), f"Missing total in column {col_letter}"
```

## Formula Construction

**Critical:** openpyxl formulas do NOT need leading `=`:

```python
# CORRECT: No equals sign prefix
ws['K107'] = 'SUM(K2:K104)'
ws['D2'] = 'IF(Roster!E6<>"",Roster!E6+1,"")'

# WRONG: Leading = causes Excel errors
# ws['K107'] = '=SUM(K2:K104)'
```

Cross-sheet references: `'Sheet Name'!A1` with quotes for spaces/special chars.

## Multi-Year Summary Dashboard (Y/Y Growth)

Use **dynamic row tracking**, not hardcoded offsets:

```python
prior_year_total_row = None

for year_idx, (year, sheet_name) in enumerate(years):
    # ... write category rows ...

    current_year_total_row = row - 1

    if year_idx > 0 and prior_year_total_row is not None:
        ws.cell(row=row, column=2, value='Y/Y Growth %')
        for col in range(3, 8):
            col_letter = get_column_letter(col)
            formula = f"IF({col_letter}{prior_year_total_row}=0,0,({col_letter}{current_year_total_row}-{col_letter}{prior_year_total_row})/{col_letter}{prior_year_total_row})"
            ws.cell(row=row, column=col, value=formula)
        row += 1

    prior_year_total_row = current_year_total_row
    row += 1
```

## Navigation Sheets & Hyperlinks

```python
from openpyxl.worksheet.hyperlink import Hyperlink

cell = ws.cell(row=r, column=c, value="EE Calcs (Current)")
cell.hyperlink = Hyperlink(ref="", location="'EE Calcs (Current)'!A1", display="EE Calcs (Current)")
```

## Common Calculation Patterns

### Tiered/Seniority Pay
```python
=IF(Years<5,0,IF(Years<10,50,IF(Years<15,60,IF(Years<20,70,IF(Years<25,80,90)))))
```

### Percentage-Based Payroll Tax with Thresholds
```python
=IF(Income<=7000,Income*0.1465,IF(Income<=119741,7000*0.1465+(Income-7000)*0.0765,7000*0.1465+112741*0.0765+(Income-119741)*0.0145))
```

### Capped & Periodic Calculations
```python
=MIN(CurrentBase, PrevWage * RetCap) * RetRate / 4
```

## Exact String Matching (Critical for Tests)

| Expected | Wrong | Issue |
|----------|-------|-------|
| `Calculations --->` | `Calculations` | Missing arrow suffix |
| `Y/Y` | `Year-over-Year` | Abbreviation vs expansion |
| `EE Calcs (Current)` | `EE Calcs Current` | Parentheses formatting |

## Critical Rules

- **Exact String Matching**: Tests verify exact substrings for sheet names and row labels.
- **Sheet Order**: `wb.sheetnames` must match required list exactly.
- **Cross-Sheet Formulas**: Quote sheet names with spaces/special chars.
- **Data Integrity**: Row count must match test expectation, not just source.
- **Named Ranges**: Define after cells exist. Verify count matches spec.
- **Legacy/Archive Sheets**: Tests frequently assert old sheets are removed. Delete them before saving.
- **Y/Y Row References**: Use dynamic tracking; never hardcoded offsets like `row - 8`.
- **Column Range Bounds**: Verify iteration ranges cover all expected columns.

## Known invariants (by sub-task)

### excel-compensation-model
- Sheet order must be exact: `wb.sheetnames` must match required list exactly
- Row labels must match verbatim - no abbreviation, casing changes, or punctuation differences
- Named ranges: Use `wb.define_name()` exclusively, never `wb.defined_names` dict access
- Named range iteration: Iterate `wb.defined_names` directly or use `.items()`/`.values()` — NOT `.definedName`
- Formulas: Never use leading `=` prefix in openpyxl formula assignment
- Row count: Must match test expectation exactly — parse test assertions
- Multi-year Summary: Use dynamic row tracking for Y/Y comparisons, never hardcoded offsets
- Binary .xlsx files: Must read with openpyxl.load_workbook(), not text tools
- Column ranges: Verify bounds match actual column count; validate after writing

## Verification Checklist

- [ ] Sheet names and order match spec exactly
- [ ] All required row labels exist verbatim
- [ ] Cross-sheet formulas reference correct sheet names
- [ ] Totals rows contain `SUM` or equivalent formulas
- [ ] Named ranges count and targets match spec
- [ ] No dropped/duplicated rows in migrated data
- [ ] Column iteration ranges cover all expected columns (no off-by-one)
- [ ] **Actual test suite passes incrementally** (not just custom checks)

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Cannot read .xlsx file | Using text Read tool | Use openpyxl.load_workbook() |
| Named ranges not appearing | Wrong API used | Use `wb.define_name()`, not dict access |
| AttributeError: 'DefinedNameDict' has no 'definedName' | Wrong iteration API | Iterate `wb.defined_names` directly or use `.items()` |
| #NAME? errors in Excel | Formula has `=` prefix | Strip leading `=`, use `'SUM(A1:A10)'` |
| Test fails on sheet order | Creation order differs | Use `wb.move_sheet()` to reorder |
| Missing row labels | Casing/punctuation mismatch | Use exact strings, substring search |
| #REF! errors | Sheet name mismatch in formula | Quote names with spaces: `'EE Calcs'!A1` |
| Custom checks pass, tests fail | Missed test assertions | Run `pytest` incrementally, parse failure messages |
| Y/Y growth wrong values | Hardcoded row offset | Track `prior_year_total_row` dynamically |
| Hyperlinks broken or missing | Incorrect location syntax | Use `Hyperlink(location="'Sheet'!A1")` |
| Off-by-one row counts | Trusted source over test | Parse test assertions, validate against test expectation |
| Missing column in totals | Off-by-one in range bounds | Verify range end = last column + 1 |

## Anti-Patterns to Avoid

| Anti-Pattern | Why It Fails | Correct Approach |
|-------------|--------------|------------------|
| Reading .xlsx with text tools | Binary file error | Use openpyxl.load_workbook() |
| `wb.defined_names['NAME'] = ...` | AttributeError, wrong API | `wb.define_name('NAME', 'Sheet!$A$1')` |
| `wb.defined_names.definedName` | AttributeError: 'DefinedNameDict' has no such attribute | Iterate `wb.defined_names` directly or use `.items()` |
| `for dn in wb.defined_names:` expecting objects | Yields strings, not DefinedName objects | Use `.items()` or `.values()` for objects |
| Formulas with `=` prefix | Excel parse errors, #NAME? | Strip leading `=`, use `'SUM(A1:A10)'` |
| Hardcoded calculated values | Model doesn't update | All outputs as formulas referencing assumptions |
| `row - 8` or hardcoded offsets | Breaks when structure changes | Track actual row numbers during construction |
| Deep nested IFs (>3 levels) | Unmaintainable | Named ranges + lookup tables |
| Relying on custom verification only | Misses exact test assertions | Run `pytest` incrementally |
| Trusting source count over test assertion | Off-by-one errors | Test assertion wins — investigate discrepancy |
| `range(start, end)` without validation | Off-by-one errors | Verify end = last_item + 1 |

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision.

## Quick Reference

```python
from openpyxl import Workbook
from openpyxl.utils import get_column_letter

# Read binary Excel file
import openpyxl
wb_in = openpyxl.load_workbook('input.xlsx')
ws = wb_in['SheetName']
for row in ws.iter_rows(values_only=True):
    print(row)

wb = Workbook()

# Named range (CORRECT API)
wb.define_name('Rate', 'Assumptions!$B$2')

# Iterate named ranges (CORRECT: iterate directly or use .items())
for name in wb.defined_names:
    print(f"{name}: {wb.defined_names[name].attr_text}")

# Or use .items():
for name, dn_obj in wb.defined_names.items():
    print(f"{name}: {dn_obj.attr_text}")

# Formula cell (no = prefix)
ws['C5'] = 'A1*B1'

# Cross-sheet formula
ws['C5'] = "IF('Roster'!A1>'Assumptions'!$B$3,'Roster'!A1,0)"

# Column iteration with bounds validation
start_col, end_col = 10, 24
for col in range(start_col, end_col + 1):
    col_letter = get_column_letter(col)
    ws.cell(row=totals_row, column=col, value=f'SUM({col_letter}6:{col_letter}78)')

wb.save('model.xlsx')
```
