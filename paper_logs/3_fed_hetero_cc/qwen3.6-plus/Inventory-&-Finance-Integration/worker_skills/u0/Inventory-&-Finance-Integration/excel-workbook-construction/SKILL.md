---
name: excel-workbook-construction
description: Build multi-sheet Excel workbooks from CSV/JSON inputs with cross-sheet formula references, control/summary rows, and specific column layouts. Use when tasks require constructing reconciliation, rollforward, or capacity planning workbooks where a summary sheet links to detail sheets via formulas, control rows aggregate data, and specific columns hold metadata or summary values.
---

# Excel Workbook Construction & Reconciliation

## CRITICAL ANTI-PATTERN: Never Overwrite Data Cells with Formulas

**The most common failure**: Writing summary formulas into columns that hold data values in line-item rows.

- **WRONG**: Writing `=SUM(...)` into column O of rows 6-11 when column O holds `amortization_months` for those rows
- **CORRECT**: Write summary values/formulas only into control rows, then have the summary sheet reference those control row cells

**Rule**: Data rows and control rows must use disjoint column sets for their respective purposes. If a column holds data in rows 6-11, do not write formulas there—use a different column or different rows.

## CRITICAL ANTI-PATTERN: MergedCell Read-Only Error

**Symptom**: `AttributeError: 'MergedCell' object attribute 'value' is read-only`

**Cause**: In openpyxl, merging a range (e.g., `ws.merge_cells('A1:E1')`) converts cells A2:E1 into `MergedCell` objects that are **read-only**. Any subsequent `ws.cell(row, col, value=...)` call targeting those cells will fail.

**Decision Rule**: Choose ONE of these approaches:

| Approach | When to use | How |
|----------|-------------|-----|
| **No merges (recommended)** | Most tasks; avoids all merge-related bugs | Skip `merge_cells()` entirely. Use styling (borders, fills, alignment) to visually group cells. Write values normally. |
| **Write-then-merge** | When merges are explicitly required by the spec | 1. Write ALL values and formulas to the worksheet first. 2. Call `merge_cells()` as the **very last step** before saving. |
| **Top-left only** | When you must merge but also write | Write only to the top-left cell of the merge range. Secondary cells will display the same value automatically. |

**WRONG ordering** (causes read-only error):
```python
ws.merge_cells('A1:E1')
ws.cell(row=1, column=3, value='Title')  # FAILS: C1 is now a MergedCell
```

**CORRECT ordering** (write first, merge last):
```python
ws.cell(row=1, column=1, value='Title')
# ... write all other values ...
ws.merge_cells('A1:E1')  # Do this LAST, after all writes
```

**Safest approach** (no merges at all):
```python
# Skip merge_cells() entirely. Use styling for visual grouping.
from openpyxl.styles import Alignment
ws.cell(row=1, column=1, value='Title').alignment = Alignment(horizontal='center')
# Apply borders/fills to create visual sections without merge complexity
```

## CRITICAL ANTI-PATTERN: Fixed Control Row Positions

**The most common structural failure**: Assuming control rows are always at rows 13-16.

**Rule**: Control row positions are **dynamic**, determined by data row count:

```python
first_data_row = 6  # or wherever data starts
num_data_rows = len(items)  # count of line items
last_data_row = first_data_row + num_data_rows - 1

month_totals_row = last_data_row + 1
ending_balance_row = last_data_row + 2
variance_row = last_data_row + 3
gl_balance_row = last_data_row + 4
```

**Harbor format** happens to use 6 data rows (6-11), so control rows land at 12-15. **Other workbooks may have different data row counts.** Always compute positions from the data, never hardcode.

**Summary sheet formulas must reference the computed control row positions**, not assumed row numbers. If Film has 6 vendors and Music has 6 vendors starting at different rows, their control rows will be at different absolute positions.

## Typical Workbook Architecture

```
Summary Sheet
├── Links to Control Row cells in Detail Sheets (e.g., ='Detail'!O{month_totals_row})
├── Cross-sheet formulas (e.g., =B8+B14)
└── Metadata labels

Detail Sheet(s)
├── Row N: Headers
├── Rows N+1 to N+k: Line items (data only, no summary formulas)
├── Row N+k+1: Control - Month Totals (SUM of monthly columns)
├── Row N+k+2: Control - Ending Balance (link to totals)
├── Row N+k+3: Control - Variance
├── Row N+k+4: Control - GL Balance (static value, summary column only)
```

## Column Mapping Strategy

**Do not assume column letters.** Determine the summary column from the spec:
- Identify which column holds the "total" or "summary control" values
- Ensure data rows have `None` or data values in that column (no formulas)
- Ensure control rows have formulas/values in that column
- Summary sheet references that column at control row positions

**Harbor format example** (do not treat as universal):
| Column | Letter | Purpose |
|--------|--------|---------|
| 14 | N | April period values, monthly totals |
| 15 | O | Total/Grand Total, GL Balance |

**Rights rollforward example** (different layout):
| Column | Letter | Purpose |
|--------|--------|---------|
| 15 | O | Summary Control (total adds, total amort, ending balance, GL) |
| 16 | P | Amort Months |
| 17 | Q | Comments |

## Environment Setup

### Venv-first pattern (recommended)
```bash
python3 -m venv /tmp/venv
/tmp/venv/bin/pip install openpyxl -q
```

Run all Python through the venv:
```bash
/tmp/venv/bin/python3 << 'PYEOF'
# your code here
PYEOF
```

### Alternative: break-system-packages
For isolated agent runs:
```bash
pip install openpyxl -q --break-system-packages
```

## Construction Workflow

1. **Read Inputs**: Load CSV(s) for line items, JSON for ledger/GL balances
2. **Define Column Layout**: Map columns from spec. Identify the summary control column.
3. **Create Workbook**: `wb = openpyxl.Workbook()`
4. **Build Detail Sheets First**:
   - Write headers
   - Write line items starting at the specified first data row
   - **Compute control row positions** from data row count (see anti-pattern above)
   - Write control rows at computed positions with SUM formulas or static values
   - **Do not** write summary formulas into data row columns
   - **Do not** call `merge_cells()` until ALL writes are complete (or skip merges entirely)
5. **Build Summary Sheet Last**:
   - Reference detail sheet control rows using **computed row positions**: `ws['B7'] = f"='Detail Sheet'!O{month_totals_row}"`
   - Use cross-sheet formulas for totals
6. **Apply Merges Last** (if required): Only after all values/formulas are written
7. **Save and Verify Immediately** (see verification checklist below)

## Control Row Formula Pattern

For rollforward schedules (beginning balance + adds - amortization = ending balance), write formulas across ALL month columns:

```python
from openpyxl.utils import get_column_letter

# Compute positions
first_data = 6
num_items = len(items)
last_data = first_data + num_items - 1
mt_row = last_data + 1  # Month Totals
eb_row = last_data + 2  # Ending Balance
var_row = last_data + 3  # Variance
gl_row = last_data + 4  # GL Balance

# Row mt_row: Month Totals - sum line items for each month column
for col in range(2, 15):  # B through N (adjust to your month columns)
    ws.cell(row=mt_row, column=col, value=f"=SUM({get_column_letter(col)}{first_data}:{get_column_letter(col)}{last_data})")

# Row eb_row: Ending Balance - link to month totals
for col in range(2, 16):
    ws.cell(row=eb_row, column=col, value=f"={get_column_letter(col)}{mt_row}")

# Row var_row: Variance - difference
for col in range(2, 16):
    ws.cell(row=var_row, column=col, value=f"={get_column_letter(col)}{eb_row}-{get_column_letter(col)}{mt_row}")

# Row gl_row: GL Balance - static value, only in summary column
summary_col = 15  # O
ws.cell(row=gl_row, column=summary_col, value=float(gl_balance))
```

## Cross-Sheet Formula Syntax

```python
# Reference another sheet's cell (sheet name with spaces needs single quotes)
ws['B7'] = f"='{detail_sheet_name}'!O{mt_row}"

# Dynamic reference with iteration
for i, (label, sheet_name, ctrl_row) in enumerate(summary_items, start=7):
    ws[f'B{i}'] = f"='{sheet_name}'!O{ctrl_row}"
```

## CRITICAL: Formula Verification Strategy

**openpyxl CANNOT evaluate formulas**. Formulas are stored as strings and only calculate when opened in Excel. This affects verification:

### DO NOT USE data_only=True for Verification
```python
# WRONG - This returns None for all formula cells!
wb_calc = openpyxl.load_workbook(path, data_only=True)
val = wb_calc['Detail'].cell(row=13, column=15).value  # Always None!
```

### Correct Verification: Check Formula Strings
```python
import openpyxl
from openpyxl.utils import get_column_letter

wb = openpyxl.load_workbook(path, data_only=False)  # Default, reads formulas

# 1. Check control rows have formulas in ALL columns
for row in [mt_row, eb_row, var_row]:  # Month Totals, Ending Balance, Variance
    for col in range(2, 16):  # B through O
        val = wb['Detail'].cell(row=row, column=col).value
        assert val is not None and '=' in str(val), f"Missing formula at {get_column_letter(col)}{row}"

# 2. Check GL Balance is only in summary column (static float, not formula)
assert wb['Detail'].cell(row=gl_row, column=14).value is None, "GL Balance should NOT be in column N"
assert isinstance(wb['Detail'].cell(row=gl_row, column=15).value, (int, float)), "GL Balance missing in O{gl_row}"

# 3. Check cross-sheet references in summary
summary_val = wb['Summary'].cell(row=7, column=2).value
assert "='" in str(summary_val) and "'!" in str(summary_val), "Summary formula malformed"
```

**Rule**: Verify formula strings are correct. Do NOT verify calculated values—they don't exist until Excel opens the file.

### Pre-Save Verification Script
Run `scripts/verify_rollforward.py` before saving to catch incomplete control rows:
```bash
/tmp/venv/bin/python3 scripts/verify_rollforward.py /path/to/output.xlsx
```

## Verification Checklist

After saving, reload and verify:
```python
wb = openpyxl.load_workbook(path, data_only=False)  # DO NOT use data_only=True

# 1. Sheet names and order
assert wb.sheetnames == expected_sheets

# 2. For each detail sheet, verify control row positions
for ws_detail in detail_sheets:
    # Find last data row by scanning for None in column A or checking item count
    # Verify control rows have expected content
    assert 'SUM' in str(ws_detail.cell(row=mt_row, column=summary_col).value) or isinstance(ws_detail.cell(row=mt_row, column=summary_col).value, (int, float))
    assert isinstance(ws_detail.cell(row=gl_row, column=summary_col).value, float)

# 3. Summary sheet formulas reference CORRECT control row positions
for cell_ref, expected_ref in summary_formula_checks.items():
    actual = str(ws_summary[cell_ref].value)
    assert expected_ref in actual, f"Expected {expected_ref} in {actual}"

# 4. Data rows have correct types (ints for months, floats for amounts)
for row in range(first_data, last_data + 1):
    val = ws_detail.cell(row=row, column=summary_col).value
    assert val is None or isinstance(val, (int, float)), f"Data row {row} summary col should be None or numeric, got {type(val)}"

# 5. Numeric types are correct (float for amounts, not strings)
assert isinstance(ws_detail.cell(row=gl_row, column=summary_col).value, float)
```

## Known Invariants (by sub-task)

### Harbor financial reconciliation
- **6 data rows** starting at row 6 → control rows at 12-15
- **Row 12**: Month Totals (formulas in all month columns)
- **Row 13**: Ending Balance (formulas linking to row 12)
- **Row 14**: Variance (formulas)
- **Row 15**: GL Balance (static value, **only column O**, not formula)
- **Column N (14)**: April period values
- **Column O (15)**: Totals and GL Balance

### Transit subsidy rollforward
- Same pattern as Harbor
- Control rows must have formulas across all month columns (B-N), not just totals (O)

### Media rights rollforward
- **Variable data row counts** per detail sheet → compute control row positions dynamically
- **Summary column** (typically O) holds control values; data rows have None in this column
- **Summary sheet** references control rows at computed positions, not fixed rows
- **Hierarchical grouping**: Account headers (no formula), indented line items (formulas to detail sheets)

## Common Pitfalls

| Issue | Cause | Fix |
|-------|-------|-----|
| Summary formulas overwrite data | Wrote formulas into data row columns | Use control rows for summaries |
| Control rows incomplete | Formulas only in totals column | Write formulas across ALL month columns |
| `ws2` referenced but undefined | Copied code with wrong variable name | Use consistent `ws` parameter |
| Cross-sheet formula syntax error | Missing quotes around sheet name with spaces | Use `="'Sheet Name'!A1"` format |
| GL balance written as string | JSON value not cast to float | Use `float(ledger['gl_balance'])` |
| SUM formula references wrong range | Off-by-one in row indices | Verify range covers all data rows |
| `MergedCell` read-only error | Wrote to cell after merging | Write all values first, merge last; or skip merges |
| **Wrong control row positions** | Hardcoded rows 13-16 instead of computing from data | Compute: `last_data + 1, +2, +3, +4` |
| **Summary refs point to data rows** | Referenced O7-O9 instead of control rows | Reference control row positions (e.g., O12-O15) |
| **Different sheets, different control rows** | Assumed all detail sheets share same control row numbers | Compute per-sheet based on that sheet's data row count |

## Style & Formatting Guidelines

- **Amounts**: `#,##0.00` format
- **Integers** (months, counts): `0` format
- **Headers**: Bold font, thin borders
- **Control rows**: Bold + italic font, thin borders
- **Data cells**: Thin borders, appropriate number format
- **Visual grouping without merges**: Use borders, fills, alignment instead of `merge_cells()`

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## When to Use This Skill

- Building reconciliation workbooks from CSV/JSON vendor data + ledger balances
- Creating rollforward schedules with beginning balance, adds, amortization, ending balance
- Constructing capacity planning workbooks with summary and detail sheets
- Any task requiring cross-sheet formula references and control row aggregation
- Media rights, financial, or inventory rollforwards with hierarchical summary sheets

## Fallback

If the verifier rejects the workbook structure, check:
1. **Are control rows at computed positions?** Recalculate from data row count.
2. **Are summary formulas referencing control rows, not data rows?** Verify row numbers match control rows.
3. **Are cross-sheet references using correct columns and sheet names with quotes?**
4. **Are numeric types correct (float for amounts, not strings)?**
5. **Did you hit a `MergedCell` error?** Remove all `merge_cells()` calls and use styling-only approach.
6. **Does each detail sheet have its own control row positions?** Don't assume uniformity across sheets.
