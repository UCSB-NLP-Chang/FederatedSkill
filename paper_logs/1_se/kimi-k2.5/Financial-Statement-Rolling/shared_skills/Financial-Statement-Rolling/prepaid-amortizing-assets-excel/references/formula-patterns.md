# Prepaid/Amortizing Asset Formula Patterns

## Column Layout (17-column detail sheets)

| Col | Header | Row 6+ Data | Row 9 Total | Row 10 Ending | Row 12 GL |
|-----|--------|-------------|-------------|---------------|-----------|
| A | Payee / Entity | Name | "Period Totals" | "Ending Balance" | "GL Balance" |
| B | Beginning Balance | Value | `=SUM(B6:B8)` | Carries forward | — |
| C | Jul Capitalized | Value | `=SUM(C6:C8)` | — | — |
| D | Jul Amortized | Value | `=SUM(D6:D8)` | — | — |
| E | Jul Ending Balance | Value | `=SUM(E6:E8)` | `=B10+C10-D10` | [hardcoded] |
| F | Aug Capitalized | Value | `=SUM(F6:F8)` | — | — |
| G | Aug Amortized | Value | `=SUM(G6:G8)` | — | — |
| H | Aug Ending Balance | Value | `=SUM(H6:H8)` | `=E10+F10-G10` | [hardcoded] |
| I | Sep Capitalized | Value | `=SUM(I6:I8)` | — | — |
| J | Sep Amortized | Value | `=SUM(J6:J8)` | — | — |
| K | Sep Ending Balance | Value | `=SUM(K6:K8)` | `=H10+I10-J10` | [hardcoded] |
| L | Oct Capitalized | Value | `=SUM(L6:L8)` | — | — |
| M | Oct Amortized | Value | `=SUM(M6:M8)` | — | — |
| N | Oct Ending Balance | Value | `=SUM(N6:N8)` | `=K10+L10-M10` | [hardcoded] |
| O | Useful Life Months | Months | `=C9+F9+I9+L9` | `=D10+G10+J10+M10` | `=O9-O10` |
| P | Notes | Comment | — | — | — |
| Q | Asset Account | Number | — | — | — |

## Rolling Chain Pattern

```
E10: =B10+C10-D10    (Jul: beg + cap - amort)
H10: =E10+F10-G10    (Aug: prior ending + cap - amort)
K10: =H10+I10-J10    (Sep: prior ending + cap - amort)
N10: =K10+L10-M10    (Oct: prior ending + cap - amort)
```

## Why O9 and O10 Differ

Unlike deferred revenue where O11 sums recognition, this pattern:
- **O9** sums additions (capitalized amounts) to track total capitalized
- **O10** sums reductions (amortized amounts) to track total expensed
- **O12** reconciles: `=O9-O10` (total capitalized minus total amortized)

This matches the GL balance which represents remaining unamortized cost.

## Summary Sheet Cross-References

Standard pattern (verify exact rows in your spec):

```python
# Field section
ws['B7'] = "='Field Comm Asset #1510'!O9"   # Period Totals
ws['B8'] = "='Field Comm Asset #1510'!O10"  # Ending Balance
ws['B9'] = "='Field Comm Asset #1510'!O12"  # GL Balance

# Partner section
ws['B13'] = "='Partner Comm Asset #1515'!O9"
ws['B14'] = "='Partner Comm Asset #1515'!O10"
ws['B15'] = "='Partner Comm Asset #1515'!O12"

# Total
ws['B16'] = '=B9+B15'
```

## Multi-Period Extensions

For additional periods, extend the pattern:
- Continue columns R-T (Nov), U-W (Dec), etc.
- Row 10 formulas always reference prior period's ending column
- O9 accumulates every 3rd column starting from C (capitalized)
- O10 accumulates every 3rd column starting from D (amortized)