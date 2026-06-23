# Accrual Rollforward Variant

Accrual rollforwards use the same control-row logic as deferred revenue but differ in column headers and some terminology.

## Column Layout (Accrual)

| Col | A | B | C | D | E | F | G | H | I | J | K | L |
|-----|---|---|---|---|---|---|---|---|---|---|---|---|
| Header | Accrual Bucket | Beg Bal | Sep Accruals | Sep Releases | Sep Ending | Oct Accruals | Oct Releases | Oct Ending | Nov Accruals | Nov Releases | Nov Ending | Reserve Months |

Compare to deferred revenue which uses: Billings, Recognition, Contract Months, Notes, Revenue Code.

## Key Differences

| Aspect | Deferred Revenue | Accrual |
|--------|-----------------|---------|
| Activity columns | Billings / Recognition | Accruals / Releases |
| Month column | Contract Months | Reserve Months |
| Extra columns | Notes, Revenue Code | Notes, Department Code |
| Total column formula | `=C+F+I+L` (total billings) | `=C+F+I` (total accruals) |
| Recognition total | `=D+G+J+M` | `=D+G+J` (total releases) |

## Control Row Formulas (3-month: Sep/Oct/Nov)

### Period Totals (row 9 for 3 line items starting row 6)
- B9: `=SUM(B6:B8)`
- C9: `=SUM(C6:C8)` … through K9
- L9: `=C9+F9+I9` (total accruals)

### Ending Balance (row 10)
- B10: `=B9` (reference Period Totals Beg Bal)
- E10: `=B10+C9-D9` (Sep Ending)
- H10: `=E10+F9-G9` (Oct Ending)
- K10: `=H10+I9-J9` (Nov Ending)
- L10: `=D9+G9+J9` (total releases)

### Variance (row 11)
- K11: `=L12-K10` (GL Nov Ending minus Ending Balance Nov Ending)

### GL Balance (row 12)
- E12, H12, K12: hardcoded from GL JSON
- L12: `=L9-L10` (total accruals minus total releases)

## Summary Sheet Pattern

Accrual summaries often include a "Combined GL Balance" row that sums the GL Balance rows from each account:
- `B16 = B9 + B14` (Payroll GL + Bonus GL)

Always extract exact cell positions from the spec.
