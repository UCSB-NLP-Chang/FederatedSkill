# Rollforward Detail Sheet Anatomy

## Row Layout

| Row | Content |
|-----|---------|
| 1–4 | Blank or title area |
| 5 | Column headers (alternative: row 6 for some specs — verify per task) |
| 6–N | Line items (one per customer/contract), starting row 6 or 7 depending on header row |
| N+1 | Period Totals (SUM formulas) |
| N+2 | Ending Balance (rollforward formulas) |
| N+3 | Variance (GL − Ending Balance) |
| N+4 | GL Balance (hardcoded GL values in ending-balance columns) |

## Column Layout

| Col | A | B | C | D | E | F | G | H | I | J | K | L | M | N | O | P | Q |
|-----|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Header | Customer | Beg Bal | May Bill | May Rec | May End | Jun Bill | Jun Rec | Jun End | Jul Bill | Jul Rec | Jul End | Aug Bill | Aug Rec | Aug End | Total Bill | Months | Notes |

## Formula Detail (4 line items, rows 6–9)

### Period Totals (row 10)
- B10: `=SUM(B6:B9)`
- C10: `=SUM(C6:C9)` … through N10
- O10: `=C10+F10+I10+L10` (total billings)

### Ending Balance (row 11)
- B11: `=B10` (MUST equal Period Totals beginning balance)
- E11: `=B11+C10-D10` (May Ending = BegBal + Billings - Recognition from Period Totals)
- H11: `=E11+F10-G10` (Jun Ending = MayEnding + JunBillings - JunRecognition)
- K11: `=H11+I10-J10` (Jul Ending = JunEnding + JulBillings - JulRecognition)
- N11: `=K11+L10-M10` (Aug Ending = JulEnding + AugBillings - AugRecognition)
- O11: `=D10+G10+J10+M10` (total recognition)

**Key insight**: The Ending Balance control row's Beginning Balance (B11) must reference Period Totals (B10). The billings and recognition values also come from Period Totals row, not the Ending Balance row itself.

### Variance (row 12)
- N12: `=N13-N11` (GL Balance minus Ending Balance for August)
- Should equal 0 if books balance.

### GL Balance (row 13)
- E13: hardcoded May GL ending balance from source
- H13: hardcoded Jun GL ending balance
- K13: hardcoded Jul GL ending balance
- N13: hardcoded Aug GL ending balance
- O13: `=N13` or total recognition per GL

## Summary Sheet Link Pattern

Link to detail sheet control rows:
```
='SaaS Rev #2300'!O10   (Period Totals)
='SaaS Rev #2300'!O11   (Ending Balance)
='SaaS Rev #2300'!N12   (Variance)
='SaaS Rev #2300'!N13   (GL Balance)
```

Single quotes are **required** when sheet names contain spaces or `#`.
