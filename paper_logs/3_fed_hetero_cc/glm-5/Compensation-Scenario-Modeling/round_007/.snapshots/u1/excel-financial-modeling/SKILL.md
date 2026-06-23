---
name: excel-financial-modeling
description: Build complex, formula-driven Excel workbooks for financial modeling, compensation analysis, and multi-year projections using openpyxl. Use when tasks require named ranges, cross-sheet formulas, tiered calculations, or assumption-driven models that must recalculate automatically.
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

1. **Extract Test Expectations First** - Parse test files for exact sheet names, order, row/column indices, label strings, **exact record counts**, and absence checks (e.g., `assert "Archive" not in wb.sheetnames`). Do not guess layout or row counts.
2. **Read Source Files with openpyxl** - Binary .xlsx files cannot be read with text tools. Use openpyxl directly:
   ```python
   import openpyxl
   wb = openpyxl.load_workbook('input.xlsx')
   for sheet in wb.sheetnames:
       ws = wb[sheet]
       for row in ws.iter_rows(values_only=True):
           print(row)
   ```
3. **Create Sheets in Exact Order** - `wb.sheetnames` must match required list exactly. Use `wb.move_sheet()` if creation order differs.
4. **Populate Static Data** - Write headers, labels, and inputs exactly as specified. No abbreviations.
5. **Define Named Ranges** - Use `wb.define_name()` after cells exist.
6. **Write Formulas** - NO leading `=` prefix (openpyxl syntax).
7. **Track Rows Dynamically for Multi-Year** - Store actual row numbers during construction; never use hardcoded offsets like `row - 8`.
8. **Run Actual Tests Incrementally** - Execute `pytest` immediately after the first successful save. Custom verification scripts are supplementary only. If tests fail, read the exact assertion error before guessing. Treat `pytest` as the ground truth; custom `print` checks often miss exact string matches, formula syntax, or hidden assertions.

## Safe Inline Verification (Copy-Paste)

When checking workbooks inline, use these patterns to avoid `AttributeError` on `defined_names`:
```python
# Count named ranges safely
count = len(wb.defined_names)

# List all names safely
all_names = list(wb.defined_names)

# Check specific name exists
if 'TargetName' in wb.defined_names:
    target_ref = wb.defined_names['TargetName'].attr_text
```

**Post-save checks:** Run `scripts/verify_workbook.py` and `scripts/verify_formulas.py` immediately after saving to catch structural mismatches before running `pytest`.

## Source Data Migration & Row Counting

- **Dynamic Counting**: Calculate row counts dynamically from source data (`len(roster)`), but validate against test expectations.
- **Header/Footer Handling**: Do not assume trailing rows are overflow/headers without explicit verification. If a source sheet contains a pre-calculated total or overflow row, explicitly skip it during iteration, but ensure the final migrated count matches the test's expected record count.
- **Off-by-One Prevention**: Hardcoded row offsets (e.g., `row - 8`) or guessed counts (`len(data) - 1`) frequently break when source structure changes. Use dynamic tracking and verify counts against test assertions early.

## Summary Sheet Cross-Sheet References (Critical)

When building Summary sheets that pull totals from calculation sheets:

1. **Verify column letters match actual data columns** - Common error: referencing A/B/C instead of J/N/R
2. **Validation pattern (COPY-PASTE THIS)**:
```python
# After writing Summary formulas, verify they reference correct columns
summary_ws = wb['Summary']
calcs_ws = wb['EE Calcs (Current)']

# Check that Base Salary Q1 pulls from column J (not C)
formula = summary_ws['C26'].value
assert 'J69' in str(formula), f"Base Salary should reference J69, got: {formula}"
```

## Column Range Bounds (Critical)

When iterating columns for formulas, totals, or formatting, **always verify the range bounds match the actual column count**:

```python
# WRONG: Off-by-one error, misses last column
for col in range(10, 23):  # Only covers J through V (23-10=13 columns)
    # But you need 14 columns (J through W)

# CORRECT: Use explicit end column + 1
for col in range(10, 24):  # Covers J through W (24-10=14 columns)
```

**Validation pattern:**
```python
from openpyxl.utils import get_column_letter

# After writing totals, verify all expected columns have formulas
expected_cols = ['T', 'U', 'V', 'W']  # Q1, Q2, Q3, Q4
for col_letter in expected_cols:
    cell = ws[f'{col_letter}{totals_row}']
    assert cell.value and 'SUM' in str(cell.value), f"Missing total in column {col_letter}"
```

**Common off-by-one scenarios:**
- Quarterly totals (4 quarters = 4 columns)
- Monthly breakdowns (12 months = 12 columns)
- Multi-year projections (N years = N columns)
- Tiered calculations with N tiers

## Navigation Sheets & Hyperlinks

For internal navigation sheets linking to calculation tabs:
```python
from openpyxl.worksheet.hyperlink import Hyperlink

# Create hyperlink cell
cell = ws.cell(row=r, column=c, value="EE Calcs (Current)")
cell.hyperlink = Hyperlink(ref="", location="'EE Calcs (Current)'!A1", display="EE Calcs (Current)")
# Ensure target sheet name matches exactly, including spaces/parentheses.
```

## Capped & Periodic Calculations

Common in benefits (retirement match, health caps, quarterly breakdowns):
```python
# Capped percentage: MIN(base, cap * multiplier) * rate / periods
# Example: Retirement match capped at previous year wage * RetCap, paid quarterly
=MIN(CurrentBase, PrevWage * RetCap) * RetRate / 4

# Quarterly breakdown of annual value
=AnnualValue / 4
```

## Named Ranges (Critical Pattern)

Use `wb.define_name()`, NOT `wb.defined_names` dict manipulation:

```python
# CORRECT: Use define_name method
wb.define_name('MWS_Current', 'Assumptions!$C$5')
wb.define_name('Payroll_Tax_Tier1_Rate', 'Assumptions!$D$19')

# WRONG: Do not access defined_names as dict
# wb.defined_names['MWS_Current'] = ...  # AttributeError or silent failures
```

**Iterating named ranges** - Iterate `wb.defined_names` directly (it is dict-like):
```python
# CORRECT: Iterate defined_names directly
for name in wb.defined_names:
    print(f"{name}: {wb.defined_names[name].attr_text}")

# Or access by name:
for name_obj in wb.defined_names.values():
    print(f"{name_obj.name}: {name_obj.attr_text}")

# WRONG: These cause AttributeError
# for name in wb.defined_names.definedName:  # AttributeError: 'DefinedNameDict' object has no attribute 'definedName'
# for name in wb.defined_names.definedname:  # AttributeError
```

Naming convention for time-variant assumptions:
- `MWS_Current`, `MWS_Year_Plus_1`, `MWS_Year_Plus_2`
- `Seniority_5_9_Current`, `Seniority_5_9_Year_Plus_1`

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
# ANTI-PATTERN: Hardcoded offset breaks when structure changes
prev_year_row = row - 8  # Brittle!

# CORRECT: Track actual total rows as you build
prior_year_total_row = None

for year_idx, (year, sheet_name) in enumerate(years):
    # ... write category rows ...

    # Store this year's Total Compensation row
    current_year_total_row = row - 1

    # Y/Y Growth row (skip for first year)
    if year_idx > 0 and prior_year_total_row is not None:
        ws.cell(row=row, column=2, value='Y/Y Growth %')
        for col in range(3, 8):
            col_letter = get_column_letter(col)
            formula = f"IF({col_letter}{prior_year_total_row}=0,0,({col_letter}{current_year_total_row}-{col_letter}{prior_year_total_row})/{col_letter}{prior_year_total_row})"
            ws.cell(row=row, column=col, value=formula)
        row += 1

    # Save for next iteration
    prior_year_total_row = current_year_total_row
    row += 1  # Spacer
```

## Common Calculation Patterns

### Tiered/Seniority Pay
```python
# Nested IF for tiered values
=IF(Years<5,0,IF(Years<10,50,IF(Years<15,60,IF(Years<20,70,IF(Years<25,80,90)))))
```

### Percentage-Based Payroll Tax with Thresholds
```python
# Multi-tier tax: different rates for income bands
=IF(Income<=7000,Income*0.1465,IF(Income<=119741,7000*0.1465+(Income-7000)*0.0765,7000*0.1465+112741*0.0765+(Income-119741)*0.0145))
```

## Exact String Matching (Critical for Tests)

Tests verify exact substrings; slight variations cause failures:

| Expected | Wrong | Issue |
|----------|-------|-------|
| `Calculations --->` | `Calculations` | Missing arrow suffix |
| `Y/Y` | `Year-over-Year` | Abbreviation vs expansion |
| `EE Calcs (Current)` | `EE Calcs Current` | Parentheses formatting |

## Critical Rules

- **Exact String Matching**: Tests verify exact substrings for sheet names and row labels.
- **Sheet Order**: `wb.sheetnames` must match required list exactly.
- **Cross-Sheet Formulas**: Quote sheet names with spaces/special chars.
- **Data Integrity**: Row count must match source. No duplicates.
- **Named Ranges**: Define after cells exist. Verify count matches spec.
- **Legacy/Archive Sheets**: Tests frequently assert old sheets are removed. Delete them before saving.
- **Y/Y Row References**: Use dynamic tracking; never hardcoded offsets like `row - 8`.
- **Column Range Bounds**: Verify iteration ranges cover all expected columns; off-by-one errors are common.

## Known invariants (by sub-task)

### excel-compensation-model
- Sheet order must be exact: `wb.sheetnames` must match required list exactly
- Row labels must match verbatim - no abbreviation, casing changes, or punctuation differences
- Named ranges: Use `wb.define_name()` exclusively, never `wb.defined_names` dict access
- Formulas: Never use leading `=` prefix in openpyxl formula assignment
- Row count: Must match source data exactly
- Multi-year Summary: Use dynamic row tracking for Y/Y comparisons, never hardcoded offsets
- Binary .xlsx files: Must read with openpyxl.load_workbook(), not text tools
- Column ranges: Verify bounds match actual column count; validate after writing
- Summary cross-sheet refs: Verify column letters (J, N, R not A, B, C); R6 failure was C69 instead of J69

## Verification Checklist

- [ ] Sheet names and order match spec exactly
- [ ] All required row labels exist verbatim
- [ ] Cross-sheet formulas reference correct sheet names
- [ ] Totals rows contain `SUM` or equivalent formulas
- [ ] Named ranges count and targets match spec
- [ ] No dropped/duplicated rows in migrated data
- [ ] Column iteration ranges cover all expected columns (no off-by-one)
- [ ] Actual test suite passes incrementally (not just custom checks)

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Cannot read .xlsx file | Using text Read tool | Use openpyxl.load_workbook() |
| Named ranges not appearing | Wrong API used | Use `wb.define_name()`, not dict access |
| AttributeError: 'DefinedNameDict' object has no attribute 'definedName' | Wrong iteration API | Iterate `wb.defined_names` directly or use `.values()` |
| #NAME? errors in Excel | Formula has `=` prefix | Strip leading `=`, use `'SUM(A1:A10)'` |
| Test fails on sheet order | Creation order differs | Use `wb.move_sheet()` to reorder |
| Missing row labels | Casing/punctuation mismatch | Use exact strings, substring search |
| #REF! errors | Sheet name mismatch in formula | Quote names with spaces: `'EE Calcs'!A1` |
| Custom checks pass, tests fail | Mismatch in exact indices, hidden assertions, or formula syntax | Run `pytest` immediately after generation. Parse exact failure messages. Do not rely on custom `print` checks for validation. |
| Y/Y growth wrong values | Hardcoded row offset | Track `prior_year_total_row` dynamically |
| Hyperlinks broken or missing | Incorrect location syntax | Use `Hyperlink(location="'Sheet'!A1")` with exact sheet name |
| Off-by-one row counts | Assumed header/footer/overflow without verification | Dynamically count source rows, explicitly skip known non-data rows, and validate final count against test expectations before building formulas. |
| Missing column in totals | Off-by-one in range bounds | Verify range end = last column + 1; validate after writing |

## Anti-Patterns to Avoid

| Anti-Pattern | Why It Fails | Correct Approach |
|-------------|--------------|------------------|
| Reading .xlsx with text tools | Binary file error | Use openpyxl.load_workbook() |
| `wb.defined_names['NAME'] = ...` | AttributeError, wrong API | `wb.define_name('NAME', 'Sheet!$A$1')` |
| `wb.defined_names.definedName` or `.definedname` | AttributeError: 'DefinedNameDict' has no such attribute | Iterate `wb.defined_names` directly or use `.values()` |
| Formulas with `=` prefix | Excel parse errors, #NAME? | Strip leading `=`, use `'SUM(A1:A10)'` |
| Hardcoded calculated values | Model doesn't update | All outputs as formulas referencing assumptions |
| `row - 8` or hardcoded offsets | Breaks when structure changes | Track actual row numbers during construction |
| Deep nested IFs (>3 levels) | Unmaintainable | Named ranges + lookup tables |
| Relying on custom verification only | Misses exact test assertions | Run actual test suite incrementally |
| Assuming source row counts without verification | Off-by-one errors in totals and cross-sheet refs | Dynamically count, skip non-data rows explicitly, validate against test expectations |
| `range(start, end)` without validation | Off-by-one errors | Verify end = last_item + 1; check after writing |

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Extension: Complex Models

For large models (500+ rows, 10+ sheets):
- See `references/large-model-patterns.md` for memory optimization
- Use `scripts/verify_formulas.py` to audit formula consistency

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

# Iterate named ranges (CORRECT: iterate directly)
for name in wb.defined_names:
    print(f"{name}: {wb.defined_names[name].attr_text}")

# Or use values():
for name_obj in wb.defined_names.values():
    print(f"{name_obj.name}: {name_obj.attr_text}")

# Formula cell (no = prefix)
ws['C5'] = 'A1*B1'

# Cross-sheet formula
ws['C5'] = "IF('Roster'!A1>'Assumptions'!$B$3,'Roster'!A1,0)"

# Column iteration with bounds validation
start_col, end_col = 10, 24  # J through W (inclusive)
for col in range(start_col, end_col + 1):  # +1 for Python range semantics
    col_letter = get_column_letter(col)
    ws.cell(row=totals_row, column=col, value=f'SUM({col_letter}6:{col_letter}78)')

# Verify all expected columns have formulas
for col in range(start_col, end_col + 1):
    cell = ws.cell(row=totals_row, column=col)
    assert cell.value and 'SUM' in str(cell.value), f"Missing total in column {get_column_letter(col)}"

wb.save('model.xlsx')

# CHECKPOINT: Run pytest immediately after save
import subprocess
result = subprocess.run(['pytest', '-v'], capture_output=True, text=True)
print(result.stdout)
if result.returncode != 0:
    print("FAILED:", result.stderr)
    # READ the exact assertion error before guessing
```
