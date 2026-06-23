# Summary Sheet Layout Variants

## Standard Two-Account Layout (5+ periods)

```
Row 1: Company Name
Row 2: Period Ending

Row 4: Field Comm Asset #1510
Row 5: Description | Amount
Row 7: Period Totals     | ='Field'!O9
Row 8: Ending Balance    | ='Field'!O10
Row 9: GL Balance        | ='Field'!O12

Row 11: Partner Comm Asset #1515
Row 12: Description | Amount
Row 13: Period Totals    | ='Partner'!O9
Row 14: Ending Balance   | ='Partner'!O10
Row 15: GL Balance       | ='Partner'!O12

Row 16: Total            | =B9+B15
```

## Alternative Layout (compact)

Some specs use tighter spacing:

```
Row 4: Account Header
Row 5: Description | Amount
Row 6: Period Totals     | !O9
Row 7: Ending Balance    | !O10
Row 8: GL Balance        | !O12

Row 10: Second Account
...
```

## Verification Pattern

Always verify exact row positions:

```python
def verify_summary_layout(summary_sheet, expected):
    """Verify summary matches expected layout spec."""
    checks = [
        (expected['field_period'], 'B7', '!O9'),
        (expected['field_ending'], 'B8', '!O10'),
        (expected['field_gl'], 'B9', '!O12'),
        (expected['partner_period'], 'B13', '!O9'),
        (expected['partner_ending'], 'B14', '!O10'),
        (expected['partner_gl'], 'B15', '!O12'),
    ]
    for desc, cell, pattern in checks:
        val = str(summary_sheet[cell].value)
        assert pattern in val, f"{desc} at {cell}: expected {pattern}, got {val}"
```

## Anti-Pattern: Assuming Fixed Rows

Don't hardcode row numbers without verifying. The spec may vary:
- Some use rows 6-8, others 7-9
- Spacing between sections varies
- Total row position varies (16 vs 18 vs other)

Always read the spec for exact row numbers.