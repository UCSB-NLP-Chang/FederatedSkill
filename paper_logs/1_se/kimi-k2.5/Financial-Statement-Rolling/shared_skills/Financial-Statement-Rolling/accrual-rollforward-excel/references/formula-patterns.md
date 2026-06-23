# Accrual Rollforward Formula Patterns

## Rolling Balance Chain

Unlike deferred revenue where each period's recognition is independent, accrual rollforwards chain:

```
Sep Ending = Sep Beginning + Sep Adds - Sep Releases
Oct Ending = Sep Ending      + Oct Adds - Oct Releases  
Nov Ending = Oct Ending      + Nov Adds - Nov Releases
```

## Column Layout (15-column detail sheets for quarterly+ data)

| Col | Header | Row 6+ Data | Row 9 Total | Row 10 Ending | Row 12 GL |
|-----|--------|-------------|-------------|---------------|-----------|
| A | Claim Group / Bucket | Name | "Period Totals" | "Ending Balance" | "GL Balance" |
| B | Beginning Balance | Value | `=SUM(B6:B8)` | 0 (carries forward) | — |
| C | Jun Accruals/Incurred | Value | `=SUM(C6:C8)` | — | — |
| D | Jun Releases/Paid | Value | `=SUM(D6:D8)` | — | — |
| E | Jun Ending Balance | Value | `=SUM(E6:E8)` | `=B10+C10-D10` | 15000 |
| F | Jul Accruals/Incurred | Value | `=SUM(F6:F8)` | — | — |
| G | Jul Releases/Paid | Value | `=SUM(G6:G8)` | — | — |
| H | Jul Ending Balance | Value | `=SUM(H6:H8)` | `=E10+F10-G10` | 17500 |
| I | Aug Accruals/Incurred | Value | `=SUM(I6:I8)` | — | — |
| J | Aug Releases/Paid | Value | `=SUM(J6:J8)` | — | — |
| K | Aug Ending Balance | Value | `=SUM(K6:K8)` | `=H10+I10-J10` | 13500 |
| L | Sep Accruals/Incurred | Value | `=SUM(L6:L8)` | — | — |
| M | Sep Releases/Paid | Value | `=SUM(M6:M8)` | — | — |
| N | Sep Ending Balance | Value | `=SUM(N6:N8)` | `=K10+L10-M10` | 7500 |
| O | Reserve/Coverage Months | Months | `=C9+F9+I9+L9` | `=D10+G10+J10+M10` | `=O9-O10` |
| P | Notes | Comment | — | — | — |
| Q | Reserve Account | Number | — | — | — |

## Why Row 10 is Sparse

Row 10 (Ending Balance) only has formulas in columns E, H, K, N, O because:
- E, H, K, N are the calculated ending balances for each period
- Other columns are intermediate inputs or don't apply to the rollup
- O10 sums all releases across periods for the total

## Common Formula Errors

**Wrong (cumulative like deferred revenue):**
```
O10: =D10+G10+J10+M10  # This is CORRECT for accruals — total releases
N10: =D10+G10+J10+M10  # WRONG — should be =K10+L10-M10
```

**Correct (rolling):**
```
E10: =B10+C10-D10  # Jun depends on B (beg) + C (adds) - D (releases)
H10: =E10+F10-G10  # Jul depends on E (prior ending) + F - G
K10: =H10+I10-J10  # Aug depends on H (prior ending) + I - J
N10: =K10+L10-M10  # Sep depends on K (prior ending) + L - M
```

## Multi-Period Extensions

For more than 4 periods, extend the pattern:
- Continue columns R-T, U-W, etc. for additional periods
- Row 10 formulas always reference prior period's ending column
- O9 formula accumulates all "adds" columns (every 3rd column starting from C)
- O10 formula accumulates all "releases" columns (every 3rd column starting from D)
