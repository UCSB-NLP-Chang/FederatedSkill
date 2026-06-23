# Rollforward Detail Sheet Anatomy

## Row Layout

| Row | Content |
|-----|---------|
| 1–4 | Blank or title area |
| 5 | Column headers |
| 6–N | Line items (one per customer/contract) |
| N+1 | Period Totals (SUM formulas) |
| N+2 | Ending Balance (rollforward formulas) |
| N+3 | Variance (GL − Ending Balance) |
| N+4 | GL Balance (hardcoded GL values in ending-balance columns) |

## Column Layout

| Col | A | B | C | D | E | F | G | H | I | J | K | L | M | N | O | P | Q |
|-----|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Header | Customer | Beg Bal | May Bill | May Rec | May End | Jun Bill | Jun Rec | Jun End | Jul Bill | Jul Rec | Jul End | Aug Bill | Aug Rec | Aug End | Total Bill | Months | Notes |

## Formula Detail for 4 Line Items (rows 6–9)

### Period Totals (row 10)
- B10: `=SUM(B6:B9)`
- C10: `=SUM(C6:C9)` … through N10
- O10: `=C10+F10+I10+L10` (total billings)

### Ending Balance (row 11)
- B11: `=B10` — **MUST reference Period Totals Beginning Balance, NOT its own empty cell**
- E11: `=B11+C10-D10` (May Ending = BegBal + May Billings - May Recognition)
- H11: `=E11+F10-G10` (Jun Ending = May Ending + Jun Billings - Jun Recognition)
- K11: `=H11+I10-J10` (Jul Ending)
- N11: `=K11+L10-M10` (Aug Ending)
- O11: `=D10+G10+J10+M10` (total recognition)

**Key insight**: The Ending Balance control row's Beginning Balance (B11) must equal the Period Totals Beginning Balance (B10). Either set B11=`=B10` or hardcode the same value.

**WRONG**: `B11` left empty or zero → `=B11+C10-D10` produces wrong value because B11 is 0, not the sum of beginning balances.

**RIGHT**: `B11` = `=B10` → `=B11+C10-D10` correctly computes May Ending from the total beginning balance.

### Variance (row 12)
- N12: `=N13-N11` (GL Balance minus Ending Balance for August)
- Should equal 0 if books balance.

**WRONG**: `=N11-N13` (reversed sign — will be negative when it should be zero)

**RIGHT**: `=N13-N11` (GL minus Ending Balance)

### GL Balance (row 13)
- E13: hardcoded May GL ending balance from source
- H13: hardcoded Jun GL ending balance
- K13: hardcoded Jul GL ending balance
- N13: hardcoded Aug GL ending balance
- O13: `=N13` or total recognition per GL

## Summary Sheet Links
- Use exact cell references from spec.
- Format: `='Sheet Name'!CellRef`
- Example: `='SaaS Rev #2300'!O10`
- Single quotes required for sheet names containing spaces or special characters like `#`
