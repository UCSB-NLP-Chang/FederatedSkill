---
name: excel-workbook-construction
description: Build multi-sheet Excel workbooks from CSV/JSON inputs with cross-sheet formula references, control/summary rows, and specific column layouts. Use when tasks require constructing reconciliation, rollforward, or capacity planning workbooks where a summary sheet links to detail sheets via formulas, control rows aggregate data, and specific columns hold metadata or summary values.
---

# Excel Workbook Construction & Reconciliation

## CRITICAL ANTI-PATTERN: Never Overwrite Data Cells with Formulas

**The most common failure**: Writing summary formulas into columns that hold data values in line-item rows.

- **WRONG**: Writing `=SUM(...)` into column O of rows 6-11 when column O holds `amortization_months` for those rows
- **CORRECT**: Write summary values/formulas only into control rows (rows 13-16), then have the summary sheet reference those control row cells

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

## Typical Workbook Architecture (Harbor Format)

```
Summary Sheet
├── Links to Control Row cells in Detail Sheets (e.g., ='Detail'!O13)
├── Cross-sheet formulas (e.g., =B8+B14)
└── Metadata labels

Detail Sheet(s)
├── Row 5: Headers
├── Rows 6-11: Line items (data only, no summary formulas)
├── Row 12: Empty separator
├── Row 13: Control - Month Totals (SUM of monthly columns)
├── Row 14: Control - Ending Balance (link to totals)
├── Row 15: Control - Variance
├── Row 16: Control - GL Balance (static value, column O only)
```

## Column Mapping (CRITICAL)

| Column | Letter | Purpose |
|--------|--------|---------|
| 14 | N | April period values, monthly totals |
| 15 | O | Total/Grand Total, GL Balance |

**Summary sheet must reference column O (row 13) for totals, column O (row 16) for GL Balance.**

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
2. **Define Column Layout**: Map columns A-Q. **Column N = April values, Column O = totals**
3. **Create Workbook**: `wb = openpyxl.Workbook()`
4. **Build Detail Sheets First**:
   - Write headers at row 5
   - Write line items starting at row 6
   - Write control rows at rows 13-16 with SUM formulas or static values
   - **Do not** write summary formulas into data row columns
   - **Do not** call `merge_cells()` until ALL writes are complete (or skip merges entirely)
5. **Build Summary Sheet Last**:
   - Reference detail sheet control rows: `ws['B7'] = "='Detail Sheet'!O13"`
   - Use cross-sheet formulas for totals
6. **Apply Merges Last** (if required): Only after all values/formulas are written
7. **Save and Verify Immediately**

## Control Row Formula Pattern

For rollforward schedules (beginning balance + adds - amortization = ending balance), write formulas across ALL month columns:

```python
from openpyxl.utils import get_column_letter

# Row 13: Month Totals - sum line items for each month column
for col in range(2, 15):  # B through N
    ws.cell(row=13, column=col, value=f"=SUM({get_column_letter(col)}6:{get_column_letter(col)}11)")
ws.cell(row=13, column=15, value="=SUM(N6:N11)")  # O13 = total of Apr endings

# Row 14: Ending Balance - link to month totals
for col in range(2, 15):
    ws.cell(row=14, column=col, value=f"={get_column_letter(col)}13")
ws.cell(row=14, column=15, value="=O13")

# Row 15: Variance - difference
for col in range(2, 16):
    ws.cell(row=15, column=col, value=f"={get_column_letter(col)}14-{get_column_letter(col)}13")

# Row 16: GL Balance - static value, only in column O
ws.cell(row=16, column=15, value=float(gl_balance))
```

## Cross-Sheet Formula Syntax

```python
# Reference another sheet's cell (sheet name with spaces needs single quotes)
ws['B7'] = "='Compute Pool #8100'!O13"

# Dynamic reference with iteration
for i, pool in enumerate(pools, start=7):
    ws[f'B{i}'] = f"='{pool}'!O13"
```

## Verification Checklist

After saving, reload and verify:
```python
wb = openpyxl.load_workbook(path)
# 1. Sheet names and order
assert wb.sheetnames == ['Summary', 'Detail1', 'Detail2']
# 2. Data rows have correct types (ints for months, floats for amounts)
for row in range(6, 12):
    assert isinstance(ws.cell(row=row, column=15).value, int)  # amort months
# 3. Control rows have expected values/formulas at rows 13-16
assert 'SUM' in str(ws.cell(row=13, column=3).value) or isinstance(ws.cell(row=13, column=3).value, (int, float))
# 4. Summary sheet formulas reference correct cells (O13 for totals)
assert "'Detail1'!O13" in str(ws_summary.cell(row=6, column=2).value)
# 5. GL values are numeric, not strings (row 16, column O)
assert isinstance(ws.cell(row=16, column=15).value, float)
```

## Known Invariants (by sub-task)

### Harbor financial reconciliation
- **Row 13**: Month Totals (formulas in all month columns)
- **Row 14**: Ending Balance (formulas linking to row 13)
- **Row 15**: Variance (formulas)
- **Row 16**: GL Balance (static value, **only column O**, not formula)
- **Column N (14)**: April period values
- **Column O (15)**: Totals and GL Balance

### Transit subsidy rollforward
- Same pattern as Harbor
- Control rows must have formulas across all month columns (B-N), not just totals (O)

## Common Pitfalls

| Issue | Cause | Fix |
|-------|-------|-----|
| Summary formulas overwrite data | Wrote formulas into data row columns | Use control rows (13-16) for summaries |
| Control rows incomplete | Formulas only in totals column | Write formulas across ALL month columns (B-N) |
| `ws2` referenced but undefined | Copied code with wrong variable name | Use consistent `ws` parameter |
| Cross-sheet formula syntax error | Missing quotes around sheet name with spaces | Use `="'Sheet Name'!A1"` format |
| GL balance written as string | JSON value not cast to float | Use `float(ledger['gl_balance'])` |
| SUM formula references wrong range | Off-by-one in row indices | Verify: `SUM(N6:N11)` for 6 items starting row 6 |
| `MergedCell` read-only error | Wrote to cell after merging | Write all values first, merge last; or skip merges |
| Wrong row references | Used row 12 instead of 13-16 | Control rows are rows 13-16 per Harbor format |
| Wrong column refs | Used E/H/K instead of N/O | Column N = April, Column O = totals |

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

## Fallback

If the verifier rejects the workbook structure, check:
1. Are summary formulas in data rows? Move them to control rows (13-16).
2. Are cross-sheet references using correct columns (N/O) and sheet names with quotes?
3. Are control row values at rows 13-16, not 12-15?
4. Are numeric types correct (float for amounts, not strings)?
5. Did you hit a `MergedCell` error? Remove all `merge_cells()` calls and use styling-only approach.