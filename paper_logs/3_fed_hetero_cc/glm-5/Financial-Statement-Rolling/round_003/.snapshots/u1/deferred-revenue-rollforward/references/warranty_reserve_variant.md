# Warranty Reserve Rollforward Variant

Warranty reserve rollforwards use the accrual pattern with warranty-specific terminology (Incurred/Paid instead of Accruals/Releases). They often include record status filtering and account mapping JSON files.

## Data Structure

### Source CSV Columns
Typical warranty reserve CSV includes:
- `record_status`: "active" or "archived" (filter to active only)
- `bucket_code`: "consumer" or "commercial"
- `claim_group`: Name of the warranty claim group (e.g., "Nova Blender")
- `opening_reserve`: Beginning balance
- `{month}_incurred`: Warranty claims incurred (accruals)
- `{month}_paid` or `{month}_claims_paid`: Payments made (releases)
- `{month}_close` or `{month}_ending_balance`: Calculated ending
- `coverage_months`, `explanation`, `gl_code`

### Account Mapping JSON
Often provided as `reserve_account_map.json`:
```json
{
  "consumer": {
    "sheet_name": "Consumer Warranty #2440"
  },
  "commercial": {
    "sheet_name": "Commercial Warranty #2445"
  }
}
```

Use this mapping to determine sheet names rather than hardcoding.

## Column Layout (Warranty Reserve)

| Col | A | B | C | D | E | F | G | H | I | J | K | L | M | N | O | P | Q |
|-----|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Header | Claim Group | Beg Bal | Jun Incurred | Jun Claims Paid | Jun Ending | Jul Incurred | Jul Claims Paid | Jul Ending | Aug Incurred | Aug Claims Paid | Aug Ending | Sep Incurred | Sep Claims Paid | Sep Ending | Coverage Months | Notes | Reserve Account |

Compare to standard accrual:
- **Incurred** replaces Accruals
- **Claims Paid** (or Paid) replaces Releases
- **Coverage Months** replaces Reserve Months
- **Reserve Account** (GL code) replaces Department Code

## Control Row Formulas (4-month: Jun/Jul/Aug/Sep)

### Period Totals (row 10 for 3 line items starting row 7)
- B10: `=SUM(B7:B9)`
- C10: `=SUM(C7:C9)` … through N10
- O10: `=C10+F10+I10+L10` (total incurred/accruals)

### Ending Balance (row 11)
- B11: `=B10` (reference Period Totals Beg Bal)
- E11: `=B11+C10-D10` (Jun Ending = Beg + Incurred - Paid)
- H11: `=E11+F10-G10` (Jul Ending)
- K11: `=H11+I10-J10` (Aug Ending)
- N11: `=K11+L10-M10` (Sep Ending)
- O11: `=D10+G10+J10+M10` (total paid/releases)

### Variance (row 12)
- N12: `=N13-N11` (GL Sep Ending minus Ending Balance Sep Ending)
- O12: `=O13-O11` (optional check on totals)

### GL Balance (row 13)
- E13, H13, K13, N13: Hardcoded from GL JSON (Jun, Jul, Aug, Sep balances)
- O13: `=O10-O11` (total incurred minus total paid)

## Active Record Filtering

Always exclude archived records:
```python
data = [row for row in csv_data if row.get("record_status") == "active"]
# Sort by claim group name for consistency
data.sort(key=lambda x: x["claim_group"])
```

## Summary Sheet Pattern

Warranty summaries typically group by bucket (Consumer/Commercial):

```
A6: Consumer Warranty #2440
A7: Period Totals    B7: ='Consumer Warranty #2440'!O10
A8: Ending Balance   B8: ='Consumer Warranty #2440'!O11
A9: GL Balance       B9: ='Consumer Warranty #2440'!O13

A11: Commercial Warranty #2445
A12: Period Totals   B12: ='Commercial Warranty #2445'!O10
A13: Ending Balance  B13: ='Commercial Warranty #2445'!O11
A14: GL Balance      B14: ='Commercial Warranty #2445'!O13

A16: Total GL Balance  B16: =B9+B14
```

Note: Cross-sheet references to sheet names with spaces must use single quotes: `='Consumer Warranty #2440'!O10`.

## File Naming

Extract exact filename from task spec. Example: `Northstar_Warranty_Reserve_9-25.xlsx`