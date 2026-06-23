# Rollforward Detail Sheet Anatomy

## Row Layout (for 4 line items)

| Row | Content |
|-----|---------|
| 1–4 | Blank or title area |
| 5 | Column headers |
| 6–9 | Line items (one per customer/contract) |
| 10 | Period Totals (SUM formulas) |
| 11 | Ending Balance (rollforward formulas) |
| 12 | Variance (GL − Ending Balance) |
| 13 | GL Balance (hardcoded GL values in ending-balance columns) |

**Note**: Row numbers shift based on number of line items. Always compute dynamically: `totals_row = last_data_row + 1`.

## Column Layout

| Col | A | B | C | D | E | F | G | H | I | J | K | L | M | N | O | P | Q |
|-----|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Header | Customer | Beg Bal | May Bill | May Rec | May End | Jun Bill | Jun Rec | Jun End | Jul Bill | Jul Rec | Jul End | Aug Bill | Aug Rec | Aug End | Total Bill | Months | Notes |

## Formula Detail (rows 6–9 for line items, rows 10–13 for controls)

### Period Totals (row 10)
- B10: `=SUM(B6:B9)`
- C10 through N10: `=SUM({col}6:{col}9)`
- O10: `=C10+F10+I10+L10` (total billings)

### Ending Balance (row 11) — **CRITICAL**

**The Ending Balance control row's Beginning Balance (B11) must equal Period Totals Beginning Balance (B10).**

- B11: `=B10` — references Period Totals, NOT empty cell
- E11: `=B11+C10-D10` — May: BegBal + Billings - Recognition (all from correct rows)
- H11: `=E11+F10-G10` — Jun: MayEnd + Billings - Recognition
- K11: `=H11+I10-J10` — Jul
- N11: `=K11+L10-M10` — Aug
- O11: `=D10+G10+J10+M10` (total recognition)

### Variance (row 12)
- N12: `=N13-N11` (GL Balance minus Ending Balance for August)
- Should equal 0 if books balance.

### GL Balance (row 13)
- E13: hardcoded May GL ending balance from source JSON
- H13: hardcoded Jun GL ending balance
- K13: hardcoded Jul GL ending balance
- N13: hardcoded Aug GL ending balance

## Key Insight

The most common failure is the Ending Balance control row self-referencing:

```
WRONG: E11 = B11+C11-D11   (B11, C11, D11 are all in the Ending Balance row = empty/zero)
RIGHT: E11 = B11+C10-D10   (B11 = =B10, C10 and D10 are Period Totals)
```
