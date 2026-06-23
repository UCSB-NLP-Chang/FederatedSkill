# Commission Asset Rollforward Variant

Commission asset rollforwards use the same control-row logic as deferred revenue but differ in column headers, data sources, and terminology.

## Data Structure

### Source JSON Structure
Commission activity data is typically nested JSON with sections:
```json
{
  "sections": [
    {
      "sheet_code": "field",
      "rows": [
        {
          "line_key": "FC-001",
          "payee_name": "Apex Sellers",
          "opening_amount": 0,
          "eligible": true,
          "activity": {
            "jul_capitalized": 15000,
            "jul_amortization": 3000,
            "aug_capitalized": 0,
            "aug_amortization": 3000,
            ...
          }
        }
      ]
    }
  ]
}
```

**Filtering**: Only include rows where `eligible == true`. Exclude ineligible/placeholder records.

### Metadata CSV
A separate CSV provides additional metadata joined by `line_key`:
- `line_key`: Join key
- `useful_life_months`: Asset useful life
- `narrative`: Description
- `account_number`: GL account code

### GL Balance JSON
Standard GL balance format with per-period ending balances:
```json
{
  "field_comm_asset_1510": {
    "jul": 18750,
    "aug": 22500,
    "sep": 17250,
    "oct": 12000
  }
}
```

## Column Layout (4-month: Jul/Aug/Sep/Oct)

| Col | A | B | C | D | E | F | G | H | I | J | K | L | M | N | O | P | Q |
|-----|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Header | Payee | Beg Bal | Jul Capitalized | Jul Amortization | Jul Ending | Aug Capitalized | Aug Amortization | Aug Ending | Sep Capitalized | Sep Amortization | Sep Ending | Oct Capitalized | Oct Amortization | Oct Ending | Useful Life Months | Notes | Asset Account |

Compare to deferred revenue which uses: Customer, Billings, Recognition, Contract Months, Notes, Revenue Code.

## Key Differences

| Aspect | Deferred Revenue | Commission Asset |
|--------|-----------------|------------------|
| Activity columns | Billings / Recognition | Capitalized / Amortization |
| Month column | Contract Months | Useful Life Months |
| Extra columns | Notes, Revenue Code | Notes, Asset Account |
| Data source | CSV schedules | Nested JSON + metadata CSV |
| Filtering | record_status=active | eligible=true |

## Control Row Formulas (4-month: Jul/Aug/Sep/Oct)

For 3 line items (rows 6–8), control rows at 9–12:

### Period Totals (row 9)
- B9: `=SUM(B6:B8)`
- C9: `=SUM(C6:C8)` … through N9
- O9: `=C9+F9+I9+L9` (total capitalized)

### Ending Balance (row 10)
- B10: `=B9` (MUST reference Period Totals, not empty or self-referencing)
- E10: `=B9+C9-D9` (Jul Ending = BegBal + Jul Cap - Jul Amort)
- H10: `=E9+F9-G9` (Aug Ending = Jul End + Aug Cap - Aug Amort)
- K10: `=H9+I9-J9` (Sep Ending)
- N10: `=K9+L9-M9` (Oct Ending)
- O10: `=D9+G9+J9+M9` (total amortization)

**CRITICAL**: The Ending Balance row's Beginning Balance (B10) must equal the Period Totals Beginning Balance (B9). Either set B10=`=B9` or use B9 directly in the first month formula.

**WRONG**: `B10` = `=B10+C10-D10` → self-referencing, computes 0 + C - D
**RIGHT**: `B10` = `=B9`, `E10` = `=B9+C9-D9` → correctly rolls forward

### Variance (row 11)
- N11: `=N12-N10` (GL Oct Ending minus Ending Balance Oct Ending)
- Should equal 0 if books balance.

### GL Balance (row 12)
- E12, H12, K12, N12: Hardcoded from GL JSON (Jul, Aug, Sep, Oct balances)
- O12: `=O9-O10` (total capitalized minus total amortization)

## Summary Sheet Pattern

Commission asset summaries typically group by account:

```
A6: Field Comm Asset #1510
A7: Period Totals    B7: ='Field Comm Asset #1510'!O9
A8: Ending Balance   B8: ='Field Comm Asset #1510'!O10
A9: GL Balance       B9: ='Field Comm Asset #1510'!O12

A11: Partner Comm Asset #1515
A12: Period Totals   B12: ='Partner Comm Asset #1515'!O9
A13: Ending Balance  B13: ='Partner Comm Asset #1515'!O10
A14: GL Balance      B14: ='Partner Comm Asset #1515'!O12

A16: Total GL Balance  B16: =B9+B14
```

Note: Cross-sheet references to sheet names with spaces must use single quotes: `='Field Comm Asset #1510'!O9`.

## Data Processing Workflow

1. Load activity JSON, metadata CSV, and GL JSON.
2. Flatten activity by section, filtering to `eligible=true` only.
3. Join each row to metadata by `line_key`.
4. Sort line items by payee name, then line_key.
5. Build detail sheets using the skeleton script pattern.
6. Build summary sheet with cross-sheet formula links.

## File Naming

Extract exact filename from task spec. Example: `Solstice_Commission_Assets_10-25.xlsx`
