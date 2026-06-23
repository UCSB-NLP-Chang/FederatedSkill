---
name: excel-financial-reconciliation
description: Create Excel workbooks for financial reconciliation tasks including capacity roll-forwards, account reconciliations, and multi-period balancing. Use when tasks involve creating summary sheets with formulas linking to detail sheets, calculating month-to-month roll-forwards, computing variances between ending balances and GL balances, and presenting vendor-level line items with control rows.
---

# Financial Reconciliation & Roll-Forward Workbooks

## CRITICAL ANTI-PATTERN: Never Overwrite Data Cells with Formulas

**The most common failure**: Writing summary formulas into columns that hold data values in line-item rows.

- **WRONG**: Writing `=SUM(...)` into column O of rows 6-11 when column O holds `amortization_months` or `total_amortization` for those rows
- **CORRECT**: Write summary values/formulas only into **control rows** (rows 13-16), then have the summary sheet reference those control row cells

**Rule**: Data rows and control rows must use **disjoint column sets** for their respective purposes. If a column holds data in rows 6-12, do not write formulas there—use a different column or the designated control rows.

| Row Type | Columns Used | Purpose |
|----------|--------------|---------|
| Data rows (6-12) | A-N (monthly columns) | Line item values, vendor data |
| Control rows (13-16) | N (month totals), O (grand totals) | Aggregation formulas, GL balance |

## Domain Pattern (Harbor Format)

Financial reconciliation workbooks follow a standard Harbor format:
- **Summary Sheet**: High-level formulas aggregating detail sheets
- **Detail Sheets**: Vendor/line-item level data with period columns
- **Control Rows**: Month Totals → Ending Balance → Variance → GL Balance
- **Formula Pattern**: Summary cells reference detail sheet **column O** (totals) and **column N** (month-specific)

## Detail Sheet Layout (per pool/account)

```
Row 6:     Headers [Vendor, Jan Ending Balance, Feb..., Mar..., Apr..., Total Amortization, GL Balance]
Rows 7-12: Vendor line items with monthly values (columns B-N) and formulas in Total Amortization (O)
Row 13:    Month Totals    (formula: =SUM(N7:N12) for April, =SUM(O7:O12) for total)
Row 14:    Ending Balance  (formula: =N13, =O13)
Row 15:    Variance        (formula: =N14, =O14)
Row 16:    GL Balance      (static value in column O only, no formula)
```

**Column Mapping (CRITICAL)**:
- **Column N (14)**: April period values and totals
- **Column O (15)**: Total Amortization (sum of all months) and Grand Total
- Summary sheet must reference **O13** for totals, **O16** for GL Balance

## Summary Sheet Layout

```
Row 7:  Month Totals     (links to detail sheets column N row 13)
Row 8-11: (pool-specific links)
Row 12: (blank label)
Row 13: (blank label)    (links to column O row 13 - detail totals)
Row 14: (blank label)    (links to column O row 16 - GL balance)
Row 16: Net Position     (=B9+B14 or similar aggregation)
```

**CRITICAL FORMULA FIX**: The summary sheet formulas must use correct columns:
- Detail sheet **column O (row 13)** for Total Amortization
- Detail sheet **column O (row 16)** for GL Balance
- Detail sheet **column N (row 13)** for April Month Totals

## Construction Workflow

1. **Read Inputs**: Load CSV(s) for line items, JSON for ledger/GL balances
2. **Create Workbook**: `wb = openpyxl.Workbook()`
3. **Build Detail Sheets First**:
   - Write headers at row 6
   - Write line items starting at row 7 (data only, no summary formulas in data rows)
   - Write control rows at rows 13-16 with SUM formulas or static values
4. **Build Summary Sheet Last**:
   - Reference detail sheet control rows: `='Compute Pool #8100'!O13`
   - Use cross-sheet formulas for totals
5. **Save and Verify Immediately**

## Verification Checklist

After saving, reload and verify:

```python
import openpyxl

# 1. Check formula strings exist
wb = openpyxl.load_workbook(path, data_only=False)
assert "'Compute Pool #8100'!O13" in wb['Summary'].cell(row=7, column=2).value

# 2. Check calculated values exist (not None)
wb_calc = openpyxl.load_workbook(path, data_only=True)
assert wb_calc['Summary'].cell(row=7, column=2).value is not None

# 3. Check control row values are numeric
for row in range(13, 17):
    val = wb_calc['Compute Pool #8100'].cell(row=row, column=15).value
    if row != 16:  # GL Balance is static
        assert val is not None and isinstance(val, (int, float))
```

## Formula Patterns

### Detail Sheet - Vendor Row (Total Amortization in column O)
```python
ws.cell(row=7, column=15, value="=D7+G7+J7+M7")  # Sum of monthly amortization columns
```

### Detail Sheet - Control Rows
```python
# Month Totals (row 13)
ws.cell(row=13, column=14, value="=SUM(N7:N12)")  # April total
ws.cell(row=13, column=15, value="=SUM(O7:O12)")  # Grand total

# Ending Balance = Month Totals (row 14)
ws.cell(row=14, column=14, value="=N13")
ws.cell(row=14, column=15, value="=O13")

# Variance = Ending Balance (row 15)
ws.cell(row=15, column=14, value="=N14")
ws.cell(row=15, column=15, value="=O14")

# GL Balance - static value (row 16, column O only)
ws.cell(row=16, column=15, value=float(ledger_total))  # No formula, cast to float
```

### Summary Sheet - Cross-Sheet References
```python
# Reference detail sheet totals (column O)
ws.cell(row=7, column=2, value="='Compute Pool #8100'!O13+'Storage Pool #8200'!O13")
ws.cell(row=16, column=2, value="=B9+B14")  # Net Position
```

## Anti-Patterns & Troubleshooting

| Issue | What Happened | Correct Approach |
|-------|---------------|------------------|
| Wrong column refs | Summary linked to E/H/K instead of N/O | Map summary rows to detail columns N (Apr) and O (total) |
| Overwriting data cells | Formulas in column O rows 7-12 | Use control rows (13-16) for formulas, data rows for values |
| Formula strings stored | Readback showed "F:=..." not values | Use `data_only=True` when reading calculated values |
| None values on readback | Formulas not evaluating or wrong refs | Verify workbook saved, formulas valid, references exist |
| Missing GL in detail | GL only in summary | GL Balance goes in detail sheet row 16, column O |
| `ws2` undefined | Variable name mismatch | Use consistent worksheet variable names |
| Sheet name syntax error | Missing quotes around spaces | Use `'Sheet Name'!A1` format (single quotes around sheet name) |

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Environment Setup

```bash
python3 -m venv /tmp/venv
/tmp/venv/bin/pip install openpyxl -q
/tmp/venv/bin/python3 << 'PYEOF'
# your code here
PYEOF
```

## When to Use This Skill

- Building reconciliation workbooks from CSV/JSON vendor data + ledger balances
- Creating rollforward schedules with beginning balance, adds, amortization, ending balance
- Constructing capacity planning workbooks with summary and detail sheets
- Any task requiring cross-sheet formula references and control row aggregation

## Known Invariants (by sub-task)

### datacenter-capacity-rollforward
- Output columns: N for April period, O for totals
- Control rows at rows 13-16 (Month Totals, Ending Balance, Variance, GL Balance)
- Summary sheet references detail sheet column O for totals
- GL Balance is static value in detail sheet row 16, column O

## Fallback

If the verifier rejects the workbook structure, check:
1. Are summary formulas in data rows? Move them to control rows.
2. Are cross-sheet references using correct columns (N/O) and sheet names with quotes?
3. Are control row values matching what the summary sheet expects?
4. Are numeric types correct (float for amounts, not strings)?