# Harbor Reconciliation Format

Reference file for Harbor-specific reconciliation workbook structures.

## Column Mapping

Harbor reconciliation workbooks use specific columns:

| Column | Letter | Purpose |
|--------|--------|---------|
| 1 | A | Vendor name |
| 2-5 | B-E | Jan: Beginning Balance, Adds, Amortization, Ending Balance |
| 5-8 | E-H | Feb: Beginning Balance, Adds, Amortization, Ending Balance |
| 9-12 | I-L | Mar: Beginning Balance, Adds, Amortization, Ending Balance |
| 13-14 | M-N | Apr: Amortization, Ending Balance |
| 15 | O | **Total Amortization** (SUM of monthly amortization) |
| 16 | P | GL Balance (static value) |

**CRITICAL**: Summary sheet must reference:
- Detail sheet **column N** (14) for April Ending Balance
- Detail sheet **column O** (15) for Total Amortization
- Detail sheet **column O row 16** for GL Balance

## Detail Sheet Control Rows

Standard control row layout:
```
Row 13: Month Totals    (formula: =SUM(N7:N12) for April, =SUM(O7:O12) for total)
Row 14: Ending Balance  (formula: =N13, =O13)
Row 15: Variance        (formula: =N14, =O14)
Row 16: GL Balance      (static value in column O only)
```

## Summary Sheet Links

```python
# Month Totals row - sum across detail sheets
ws_summary['B7'] = "='Compute Pool #8100'!O13+'Storage Pool #8200'!O13"

# GL Balance - pull from detail sheet control rows
ws_summary['B14'] = "='Compute Pool #8100'!O16+'Storage Pool #8200'!O16"

# Net Position calculation
ws_summary['B16'] = "=B9+B14"
```

## Verification

1. **Write with data_only=False** (preserves formulas)
2. **Read back with data_only=True** (verifies calculations)
3. **Assert expected values exist** - None values indicate broken references
4. **Check formula syntax** - Cross-sheet refs use `'Sheet Name'!Cell` format
