---
name: excel-financial-reconciliation
description: Create Excel workbooks for financial reconciliation tasks including capacity roll-forwards, account reconciliations, and multi-period balancing. Use when tasks involve creating summary sheets with formulas linking to detail sheets, calculating month-to-month roll-forwards, computing variances between ending balances and GL balances, and presenting vendor-level line items with control rows. Critical for media rights, datacenter capacity, prepaid expenses, and any multi-period amortization tracking.
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
| Control rows (13-16) | N (April totals), O (grand totals) | Aggregation formulas, GL balance |

## CRITICAL: Control Rows Must Have Formulas Across ALL Month Columns

**Second most common failure**: Control rows with formulas only in totals column (O), leaving month columns (B-N) empty.

- **WRONG**: Control rows with formulas only in column O
  ```
  Row 13 (Month Totals): [empty, empty, ..., empty, =SUM(N6:N11)]  # WRONG!
  ```

- **CORRECT**: Control rows with formulas across ALL month columns (B-N) AND totals (O)
  ```python
  from openpyxl.utils import get_column_letter

  # Row 13: Month Totals - sum line items for each column
  for col in range(2, 16):  # B through O
      ws.cell(row=13, column=col, value=f"=SUM({get_column_letter(col)}6:{get_column_letter(col)}11)")
  ```

**Rule**: Every control row formula must exist in each month column where it makes sense, not just the totals column.

**Verification**: Run `scripts/verify_rollforward.py` before saving to catch incomplete control rows.

## Domain Pattern (Harbor Format)

Financial reconciliation workbooks follow a standard Harbor format:
- **Summary Sheet**: High-level formulas aggregating detail sheets
- **Detail Sheets**: Vendor/line-item level data with period columns
- **Control Rows**: Month Totals → Ending Balance → Variance → GL Balance
- **Formula Pattern**: Summary cells reference detail sheet **column O** (totals) and **column N** (April-specific)

**Important**: Row positions (13-16 for control rows) are Harbor-specific. For workbooks with different data row counts, compute control row positions dynamically:
```python
first_data_row = 6  # or wherever data starts
num_data_rows = len(items)
last_data_row = first_data_row + num_data_rows - 1
month_totals_row = last_data_row + 1
ending_balance_row = last_data_row + 2
variance_row = last_data_row + 3
gl_balance_row = last_data_row + 4
```

## Column Mapping (CRITICAL - MEMORIZE THIS)

| Column | Index | Purpose | What Goes Here |
|--------|-------|---------|----------------|
| **N** | 14 | April period values | April Month Totals, April Ending Balance, April Variance |
| **O** | 15 | Grand totals & GL | Total Amortization sum, GL Balance (row 16 only) |

**Key distinction:**
- **Column N (14)** = April's month-specific values
- **Column O (15)** = Grand total across all months AND GL Balance

**Common mistake**: Using column N for GL Balance. GL Balance goes in **column O, row 16 only**.

## Row Mapping (CRITICAL - MEMORIZE THIS)

### Detail Sheet Control Rows (rows 13-16)

| Row | Label | Column N (April) | Column O (Total) | Formula Pattern |
|-----|-------|------------------|------------------|-----------------|
| **13** | Month Totals | `=SUM(N6:N11)` | `=SUM(O6:O11)` | Sum of line items |
| **14** | Ending Balance | `=N13` | `=O13` | Equals Month Totals |
| **15** | Variance | `=N14-N13` | `=O14-O13` | Difference (or GL - Ending) |
| **16** | GL Balance | **EMPTY** | `float_value` | Static GL value, O only |

### Summary Sheet Row References

| Summary Row | Links To | Example Formula |
|-------------|----------|-----------------|
| Row 7 | Detail sheet N13 (April Month Totals) | `='Compute Pool #8100'!N13` |
| Row 8 | Pool 1 Ending/Total | `='Pool1'!O14` |
| Row 9 | Pool 1 GL Balance | `='Pool1'!O16` |
| Row 12 | Pool 2 Ending/Total | `='Pool2'!O14` |
| Row 13 | Pool 2 GL Balance | `='Pool2'!O16` |
| Row 16 | Net Position | `=B9+B14` (sum of GL balances) |

## Detail Sheet Layout (per pool/account)

```
Row 6:     Headers [Vendor, Jan Ending Balance, Feb..., Mar..., Apr..., Total Amortization, GL Balance]
Rows 7-12: Vendor line items with monthly values (columns B-N) and formulas in Total Amortization (O)
Row 13:    Month Totals    (formulas in ALL columns B-O)
Row 14:    Ending Balance  (formulas in ALL columns B-O)
Row 15:    Variance        (formulas in ALL columns B-O)
Row 16:    GL Balance      (static value in column O only, nothing in N)
```

## Summary Sheet Layout

```
Row 7:  April Month Totals (links to detail sheets column N row 13)
Row 8:  Pool 1 Ending Balance (links to Pool1!O14)
Row 9:  Pool 1 GL Balance (links to Pool1!O16)
Row 12: Pool 2 Ending Balance (links to Pool2!O14)
Row 13: Pool 2 GL Balance (links to Pool2!O16)
Row 16: Net Position (=B9+B13 or similar aggregation of GL balances)
```

## Construction Workflow

1. **Read Inputs**: Load CSV(s) for line items, JSON for ledger/GL balances
2. **Create Workbook**: `wb = openpyxl.Workbook()`
3. **Build Detail Sheets First**:
   - Write headers at row 6
   - Write line items starting at row 7 (data only, no summary formulas in data rows)
   - Write control rows at rows 13-16 with formulas in ALL month columns (B-O)
   - GL Balance: static value in row 16, column O only
4. **Build Summary Sheet Last**:
   - Reference detail sheet control rows: `='Compute Pool #8100'!O13`
   - Use cross-sheet formulas for totals
5. **Save and Verify Immediately**

## Formula Patterns

### Detail Sheet - Control Rows (Complete Example)

```python
from openpyxl.utils import get_column_letter

# Row 13: Month Totals - sum line items for each month column
for col in range(2, 16):  # B(2) through O(15)
    ws.cell(row=13, column=col, value=f"=SUM({get_column_letter(col)}6:{get_column_letter(col)}11)")

# Row 14: Ending Balance - equals Month Totals
for col in range(2, 16):
    ws.cell(row=14, column=col, value=f"={get_column_letter(col)}13")

# Row 15: Variance - difference (adjust formula based on requirements)
for col in range(2, 16):
    ws.cell(row=15, column=col, value=f"={get_column_letter(col)}14-{get_column_letter(col)}13")

# Row 16: GL Balance - static value in column O only
ws.cell(row=16, column=15, value=float(gl_balance))  # Column O only!
```

### Summary Sheet - Cross-Sheet References

```python
# Reference detail sheet April totals (column N)
ws.cell(row=7, column=2, value="='Compute Pool #8100'!N13")

# Reference detail sheet grand totals (column O)
ws.cell(row=8, column=2, value="='Compute Pool #8100'!O14")

# Reference detail sheet GL Balance (column O, row 16)
ws.cell(row=9, column=2, value="='Compute Pool #8100'!O16")

# Net Position - sum of GL balances
ws.cell(row=16, column=2, value="=B9+B13")
```

## CRITICAL: Formula Verification Strategy

**openpyxl CANNOT evaluate formulas**. Formulas are stored as strings and only calculate when opened in Excel. This affects verification:

### Verification WITHOUT data_only=True (Recommended)
Verify formula strings exist, not calculated values:

```python
import openpyxl
from openpyxl.utils import get_column_letter

wb = openpyxl.load_workbook(path, data_only=False)  # Default, reads formulas

# 1. Check control rows have formulas in ALL columns
for row in [13, 14, 15]:  # Month Totals, Ending Balance, Variance
    for col in range(2, 16):  # B through O
        val = wb['Detail'].cell(row=row, column=col).value
        assert val is not None and '=' in str(val), f"Missing formula at {get_column_letter(col)}{row}"

# 2. Check GL Balance is only in O16 (static float, not formula)
assert wb['Detail'].cell(row=16, column=14).value is None, "GL Balance should NOT be in column N"
assert isinstance(wb['Detail'].cell(row=16, column=15).value, (int, float)), "GL Balance missing in O16"

# 3. Check cross-sheet references in summary
summary_val = wb['Summary'].cell(row=7, column=2).value
assert "='" in str(summary_val) and "'!N13" in str(summary_val), "Summary formula malformed"
```

### DO NOT RELY ON data_only=True for Verification
```python
# WRONG - This returns None for all formula cells!
wb_calc = openpyxl.load_workbook(path, data_only=True)
val = wb_calc['Detail'].cell(row=13, column=15).value  # Always None!
```

**Rule**: Verify formula strings are correct. Do NOT verify calculated values—they don't exist until Excel opens the file.

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
- Summary sheet references detail sheet column O for totals, column N for April
- GL Balance is static value in detail sheet row 16, column O ONLY (not column N)
- Control rows must have formulas in ALL month columns (B-N) plus totals (O)

### media-rights-rollforward
- Same Harbor format as datacenter-capacity-rollforward
- Detail sheets: Film Rights #2710, Music Rights #2720 (or similar numbered accounts)
- Summary sheet: Rights Summary with cross-sheet formulas
- GL Balances from ledger JSON, placed in row 16, column O only
- Net Position in summary row 16 sums GL balances

## Anti-Patterns & Troubleshooting

| Issue | What Happened | Correct Approach |
|-------|---------------|------------------|
| Wrong column refs | Summary linked to E/H/K instead of N/O | Use column N for April, O for totals/GL |
| Wrong row refs | Used row 9 for Ending Balance instead of 14 | Control rows are 13-16, not 9-12 |
| Overwriting data cells | Formulas in column O rows 7-12 | Use control rows (13-16) for formulas |
| Incomplete control rows | Formulas only in column O | Write formulas across ALL columns B-O |
| GL Balance in wrong column | GL Balance in column N | GL Balance goes in column O, row 16 ONLY |
| Formula strings stored | Readback showed "F:=..." not values | Use `data_only=True` when reading calculated values |
| None values on readback | Formulas not evaluating or wrong refs | **Expected!** openpyxl doesn't evaluate formulas. Verify formula strings instead. |
| `ws2` undefined | Variable name mismatch | Use consistent worksheet variable names |
| Sheet name syntax error | Missing quotes around spaces | Use `'Sheet Name'!A1` format (single quotes around sheet name) |
| Verifier rejects calculated values | Checked with data_only=True | Verify formula strings exist, not calculated values |

## Fallback

If the verifier rejects the workbook structure, check:
1. Are summary formulas in data rows? Move them to control rows.
2. Are control row formulas complete across ALL columns (B-O), not just O?
3. Are cross-sheet references using correct columns (N for April, O for totals/GL)?
4. Are row references correct (13-16 for control rows, not 9-12)?
5. Is GL Balance in column O only, not column N?
6. Are numeric types correct (float for amounts, not strings)?
7. **Are you verifying with data_only=True?** Stop—verify formula strings instead.
