---
name: reconciliation-workbooks
description: Single-program reconciliation workbook pattern with formula-linked detail and summary sheets. Use for Harbor-style capacity reconciliations, financial subledger-to-GL reconciliations, or any single-category rollforward with Month Totals/Ending Balance/Variance/GL Balance control rows.
---

# Single-Program Reconciliation Pattern

Build reconciliation workbooks with one detail sheet and optional summary, using linked formulas for auditability.

**Use for**: Harbor capacity reconciliations, single-account financial rollforwards, subledger-to-GL reconciliations where only one account category exists.

## Control Row Structure

Standard 4-row control block at bottom of detail sheets:

| Row | Label | Formula | Notes |
|-----|-------|---------|-------|
| N | Month Totals | `=SUM(B7:B12)` | Sum of line item column |
| N+1 | Ending Balance | `=B13` | Links to month totals |
| N+2 | Variance | `=B14-B16` | Ending balance minus GL |
| N+3 | GL Balance | [static value] | From JSON/csv/verified source |

**Calculate row positions dynamically**:
```python
first_data_row = 7  # Assuming headers at row 6
gap_row = 1
control_start = first_data_row + len(df) + gap_row
month_totals_row = control_start
ending_balance_row = control_start + 1
variance_row = control_start + 2
gl_balance_row = control_start + 3
```

## Cross-Sheet Formula Linking (Optional Summary)

If including a summary sheet that references this detail:

```python
# Reference detail sheet control row in summary
ws['B7'] = "='Compute Pool #8100'!O13"   # Month Totals
ws['B8'] = "='Compute Pool #8100'!O14"   # Ending Balance  
ws['B9'] = "='Compute Pool #8100'!O15"   # Variance

# Combined total aggregates variances if multiple sections
ws['B16'] = '=B9+B14'
```

## Sheet Structure Template

### Detail Sheet

```
Rows 1-5:   Title/metadata (optional)
Row 6:      Column headers ['Line Item', 'Jan', 'Feb', 'Mar', 'Apr']
Rows 7-12:  Line item data (6 items typical)
Row 13:     Month Totals formula =SUM(B7:B12)
Row 14:     Ending Balance formula =B13
Row 15:     Variance formula =B14-B16 (Ending - GL)
Row 16:     GL Balance (static values from source)
```

### Summary Sheet (if needed)

```
Rows 1-5:   Title and metadata
Row 6:      Section header
Row 7:      Month Totals → linked formula from detail
Row 8:      Ending Balance → linked formula from detail
Row 9:      Variance → linked formula from detail
Row 16:     Combined Total = variance sum
```

## Formula String Construction

```python
# Correct - formula as string value
ws['B13'] = '=SUM(B7:B12)'
ws['B15'] = '=B14-B16'

# Cross-sheet reference with spaces in name - quote it
ws['B7'] = "='Compute Pool #8100'!O13"
```

## Column O Convention

Place summary-link formulas in column O to keep them visible but separate from data:

```python
# In detail sheet, expose key values for summary reference
ws['O13'] = '=SUM(B13:E13)'  # Month total across all months
# Or reference specific month ending balances
ws['O6'] = '=E13'  # Jan ending balance
ws['O7'] = '=H13'  # Feb ending balance
```

## Critical Implementation Notes

### GL Balance Source

In single-program reconciliations, GL Balance is a **static value** from verified source data:

```python
# From JSON/CSV
film_gl_balances = {
    'jan': 85628.01,
    'feb': 109834.29,
    'mar': 146435.51,
    'apr': 173432.44
}

# Write as static values
ws['B16'] = 85628.01  # Jan GL balance
ws['C16'] = 109834.29  # Feb GL balance
```

### Variance Direction

Standard: `=Ending Balance - GL Balance` or `=GL Balance - Ending Balance` depending on convention. Be consistent:

```python
# Convention A: GL - Ending (positive = under-recorded)
ws['B15'] = '=B16-B14'

# Convention B: Ending - GL (positive = over-recorded)
ws['B15'] = '=B14-B16'
```

## Data Validation

Verify formulas with `data_only=False` load:

```python
wb = openpyxl.load_workbook(path, data_only=False)
print(wb['Sheet1']['B13'].value)  # Should show '=SUM(B7:B12)'
print(wb['Sheet1']['B16'].value)  # Should show numeric value, not formula
```

## Anti-Patterns

- **Don't** calculate variances in Python; use Excel formulas for auditability
- **Don't** put GL balances in formulas in single-program mode; they're static inputs
- **Don't** use `data_only=True` when verifying formulas; it returns cached values (often None)
- **Don't** forget to quote sheet names containing spaces in cross-sheet references
- **Don't** hardcode control row positions; calculate from data length

## See Also

- `transit-subsidy-rollforward.md` - Multi-program variant with formula-linked GL balances
- `../scripts/reconciliation_template.py` - Runnable template
