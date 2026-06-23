---
name: excel-reconciliation-workbook
description: Build financial/capacity reconciliation Excel workbooks from JSON/CSV with rollforward schedules, control rows, and cross-sheet formulas. Use for tasks requiring detail sheets per pool/partition plus summary sheet linking to control rows.
---

# Excel Reconciliation Workbook Builder

## When to Use
- Input is JSON/CSV (not Excel) with vendor/partition monthly data
- Output requires multiple detail sheets + summary with cross-sheet formulas
- Control rows: Month Totals, Ending Balance, Variance, GL Balance

## Environment

```bash
source .venv/bin/activate && python3 script.py
```

## Control Row Structure (Detail Sheets)

Fixed positions for each month column:
| Row | Name | Formula/Value |
|-----|------|----------------|
| 12 | Month Totals | `=SUM(B6:B11)` per month |
| 13 | Ending Balance | Reference last month's ending total |
| 14 | Variance | `=Ending - GL` or `0` |
| 15 | GL Balance | Hardcoded from input |

## Rollforward Formula Constraints

**Business logic invariant**: Ending Balance = Prior Month Ending + Adds - Amortization

```python
# Each month: Beginning → Adds → Amortization → Ending
for month in months:
    beginning = prior_ending if month != first_month else input_beginning
    ending = beginning + adds - amortization
```

**Total Amortization column** (column O): `round(sum(monthly_amortization), 2)`

## Cross-Sheet Formula Syntax

```python
# Sheet names with spaces require single quotes
formula = f"='{sheet_name}'!{col}{row}"
ws.cell(row=r, column=c, value=formula)
```

## Summary Sheet Structure

1. Title + subtitle rows
2. Pool name rows with cross-sheet links to detail Month Totals (row 12)
3. Month Totals aggregation: `=SUM(B6:B7)`
4. Ending Balance: `=N8`
5. Reconciliation section: Total Amortization links, Variance=0, GL Balance formula

## Anti-Patterns

- **Border.Style doesn't exist**: Use `Side(style="thin")`, not `Border.Style(thin)`
- **MergedCell.value is read-only**: Unmerge first before clearing, or create fresh sheet
- **Float precision**: Wrap sums with `round(..., 2)` to avoid artifacts like 6376.72
- **Numeric vs string**: Write `float`/`int`, not formatted strings - verifier checks `isinstance(val, (int, float))`
- **Sheet names**: Case-sensitive, spaces preserved in cross-sheet formulas

## Verification

1. `wb.sheetnames` order matches expected
2. Cross-sheet formula strings exactly match sheet names
3. All numeric cells are `int`/`float`, not strings
4. Control rows at positions 12-15
