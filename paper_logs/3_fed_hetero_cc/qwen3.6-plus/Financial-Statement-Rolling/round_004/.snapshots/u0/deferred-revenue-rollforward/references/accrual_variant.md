# Accrual and Warranty Reserve Rollforward Variants

Accrual and warranty reserve rollforwards use the same control-row logic as deferred revenue but differ in column headers and some terminology.

## Column Layout (Accrual — 3-month: Sep/Oct/Nov)

| Col | A | B | C | D | E | F | G | H | I | J | K | L |
|-----|---|---|---|---|---|---|---|---|---|---|---|---|
| Header | Accrual Bucket | Beg Bal | Sep Accruals | Sep Releases | Sep Ending | Oct Accruals | Oct Releases | Oct Ending | Nov Accruals | Nov Releases | Nov Ending | Reserve Months |

## Column Layout (Warranty Reserve — 4-month: Jun/Jul/Aug/Sep)

| Col | A | B | C | D | E | F | G | H | I | J | K | L | M | N | O | P | Q |
|-----|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Header | Claim Group | Beg Bal | Jun Accruals | Jun Claims Paid | Jun Ending | Jul Accruals | Jul Claims Paid | Jul Ending | Aug Accruals | Aug Claims Paid | Aug Ending | Sep Accruals | Sep Claims Paid | Sep Ending | Coverage Months | Notes | Reserve Account |

Compare to deferred revenue which uses: Billings, Recognition, Contract Months, Notes, Revenue Code.

## Key Differences

| Aspect | Deferred Revenue | Accrual | Warranty Reserve |
|--------|-----------------|---------|------------------|
| Activity columns | Billings / Recognition | Accruals / Releases | Accruals / Claims Paid |
| Month column | Contract Months | Reserve Months | Coverage Months |
| Extra columns | Notes, Revenue Code | Notes, Department Code | Notes, Reserve Account |
| Total column formula | `=C+F+I+L` (total billings) | `=C+F+I` (total accruals) | `=C+F+I+L` (total accruals) |
| Recognition/Paid total | `=D+G+J+M` | `=D+G+J` (total releases) | `=D+G+J+M` (total claims paid) |

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

## Control Row Formulas (Warranty Reserve — 4-month: Jun/Jul/Aug/Sep)

For 3 line items (rows 7–9), control rows at 10–13:

### Period Totals (row 10)
- B10: `=SUM(B7:B9)`
- C10: `=SUM(C7:C9)` … through N10
- O10: `=C10+F10+I10+L10` (total accruals)

### Ending Balance (row 11)
- B11: `=B10` (MUST reference Period Totals, not empty)
- E11: `=B11+C10-D10` (Jun Ending)
- H11: `=E11+F10-G10` (Jul Ending)
- K11: `=H11+I10-J10` (Aug Ending)
- N11: `=K11+L10-M10` (Sep Ending)
- O11: `=D10+G10+J10+M10` (total claims paid)

### Variance (row 12)
- N12: `=N13-N11` (GL Sep Ending minus Ending Balance Sep Ending)

### GL Balance (row 13)
- E13, H13, K13, N13: hardcoded from GL JSON per period
- O13: `=O10-O11` (total accruals minus total claims paid)

## Summary Sheet Pattern

Accrual and warranty reserve summaries often include a "Combined GL Balance" row that sums the GL Balance rows from each account:
- `B16 = B9 + B14` (Consumer GL + Commercial GL)

Always extract exact cell positions from the spec.
