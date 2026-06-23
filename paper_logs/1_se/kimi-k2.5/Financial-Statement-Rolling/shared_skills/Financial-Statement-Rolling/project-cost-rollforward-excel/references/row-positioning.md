# Row Positioning Variants

## Standard 3-Row Data Layout

When data has 3 line items (rows 6-8):

| Control | Row | Formula |
|---------|-----|---------|
| Period Totals | 9 | `=SUM(B6:B8)` etc. |
| Ending Balance | 10 | `=B10+C10-D10` etc. |
| Variance | 11 | `=O12-N12` |
| GL Balance | 12 | Hardcoded values, `=O9-O10` |

## Extended 4-Row Data Layout

When data has 4 line items (rows 6-9):

| Control | Row | Formula |
|---------|-----|---------|
| Period Totals | 10 | `=SUM(B6:B9)` etc. |
| Ending Balance | 11 | `=B11+C11-D11` etc. |
| Variance | 12 | `=O13-N13` |
| GL Balance | 13 | Hardcoded values, `=O10-O11` |

## Verification Pattern

```python
def verify_control_rows(ws, data_row_count, expected):
    """Verify control rows match spec."""
    data_end = 5 + data_row_count
    period_row = data_end + 1
    ending_row = period_row + 1
    variance_row = ending_row + 1
    gl_row = variance_row + 1
    
    assert ws.cell(period_row, 1).value == 'Period Totals'
    assert ws.cell(ending_row, 1).value == 'Ending Balance'
    assert ws.cell(variance_row, 1).value == 'Variance'
    assert ws.cell(gl_row, 1).value == 'GL Balance'
    
    # Verify formula patterns
    assert 'SUM' in str(ws.cell(period_row, 2).value)
    assert '=B' in str(ws.cell(ending_row, 5).value)  # E column
```

## Summary Sheet Spacing

Two common patterns:

**Tight spacing (rows 6/7/8):**
```
Row 6: Account header
Row 7: Period Totals → !O9
Row 8: Ending Balance → !O10
Row 9: GL Balance → !O12
```

**Loose spacing (rows 6/7/8/9 with gaps):**
```
Row 6: Account header
Row 7: Period Totals → !O10
Row 8: Ending Balance → !O11
Row 9: GL Balance → !O13
Row 10: gap
Row 11: Second account
```

**Always verify exact row numbers from task specification.**
