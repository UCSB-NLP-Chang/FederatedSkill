---
name: excel-workbook-construction
description: Build multi-sheet Excel workbooks from CSV/JSON inputs with cross-sheet formula references, control/summary rows, and specific column layouts. Use when tasks require constructing reconciliation, rollforward, or capacity planning workbooks where a summary sheet links to detail sheets via formulas, control rows aggregate data, and specific columns hold metadata or summary values.
---

# Excel Workbook Construction & Reconciliation

## CRITICAL ANTI-PATTERN: Never Overwrite Data Cells with Formulas

**The most common failure**: Writing summary formulas into columns that hold data values in line-item rows.

- **WRONG**: Writing `=SUM(...)` into column O of rows 6-11 when column O holds `amortization_months` for those rows
- **CORRECT**: Write summary values/formulas only into control rows (e.g., rows 12-15), then have the summary sheet reference those control row cells

**Rule**: Data rows and control rows must use disjoint column sets for their respective purposes. If a column holds data in rows 6-11, do not write formulas there—use a different column or different rows.

## Typical Workbook Architecture

```
Summary Sheet
├── Links to Control Row cells in Detail Sheets (e.g., ='Detail'!O12)
├── Cross-sheet formulas (e.g., =B8+B14)
└── Metadata labels

Detail Sheet(s)
├── Row 5: Headers
├── Rows 6-11: Line items (data only, no summary formulas)
├── Row 12: Control - Month Totals (SUM of monthly columns)
├── Row 13: Control - Ending Balance (SUM or specific column)
├── Row 14: Control - Variance (Ending - Beginning)
└── Row 15: Control - GL Balance (from external ledger)
```

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
2. **Define Column Layout**: Map columns A-Q (or similar) to fields. Document which columns hold data vs. metadata vs. summary links
3. **Create Workbook**: `wb = openpyxl.Workbook()`
4. **Build Detail Sheets First**:
   - Write headers at row 5
   - Write line items starting at row 6
   - Write control rows at rows 12-15 with SUM formulas or static values
   - **Do not** write summary formulas into data row columns
5. **Build Summary Sheet Last**:
   - Reference detail sheet control rows: `ws['B7'] = "='Detail Sheet'!O12"`
   - Use cross-sheet formulas for totals
6. **Save and Verify Immediately**

## Cross-Sheet Formula Syntax

```python
# Reference another sheet's cell (sheet name with spaces needs single quotes)
ws['B7'] = "='Compute Pool #8100'!O12"

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
# 3. Control rows have expected values/formulas
assert 'SUM' in str(ws.cell(row=12, column=3).value) or isinstance(ws.cell(row=12, column=3).value, (int, float))
# 4. Summary sheet formulas reference correct cells
assert "'Detail1'!O12" in str(ws_summary.cell(row=6, column=2).value)
# 5. GL values are numeric, not strings
assert isinstance(ws.cell(row=15, column=14).value, float)
```

## Common Pitfalls

| Issue | Cause | Fix |
|-------|-------|-----|
| Summary formulas overwrite data | Wrote formulas into data row columns | Use control rows for summaries, reference them from summary sheet |
| `ws2` referenced but undefined | Copied code with wrong variable name | Use consistent `ws` parameter or pass worksheet explicitly |
| Cross-sheet formula syntax error | Missing quotes around sheet name with spaces | Use `="'Sheet Name'!A1"` format (single quotes around sheet name) |
| GL balance written as string | JSON value not cast to float | Use `float(ledger['gl_balance'])` |
| SUM formula references wrong range | Off-by-one in row indices | Verify: `SUM(C6:C11)` for 6 line items starting at row 6 |

## Style & Formatting Guidelines

- **Amounts**: `#,##0.00` format
- **Integers** (months, counts): `0` format
- **Headers**: Bold font, thin borders
- **Control rows**: Bold + italic font, thin borders
- **Data cells**: Thin borders, appropriate number format

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## When to Use This Skill

- Building reconciliation workbooks from multiple input sources
- Creating rollforward schedules with beginning balance, adds, amortization, ending balance
- Constructing capacity planning workbooks with summary and detail sheets
- Any task requiring cross-sheet formula references and control row aggregation

## Fallback

If the verifier rejects the workbook structure, check:
1. Are summary formulas in data rows? Move them to control rows.
2. Are cross-sheet references using correct sheet names with quotes?
3. Are control row values matching what the summary sheet expects?
4. Are numeric types correct (not strings)?
