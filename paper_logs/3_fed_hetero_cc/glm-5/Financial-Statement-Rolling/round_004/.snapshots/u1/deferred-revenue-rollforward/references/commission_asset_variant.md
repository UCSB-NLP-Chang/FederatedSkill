# Commission Asset Rollforward Variant

Commission asset rollforwards track capitalized commission costs and their amortization over time. They use the same control-row logic as other rollforward variants but with commission-specific terminology and data structures.

## Data Structure

### Source JSON Activity File
Commission assets use a nested JSON structure with sections:
```json
{
  "sections": [
    {
      "sheet_code": "field",
      "rows": [
        {
          "line_key": "FC-001",
          "payee_name": "Apex Sellers",
          "eligible": true,
          "opening_amount": 0,
          "activity": {
            "jul_capitalized": 15000,
            "jul_amortization": 3000,
            "aug_capitalized": 0,
            "aug_amortization": 3000,
            "sep_capitalized": 0,
            "sep_amortization": 3000,
            "oct_capitalized": 0,
            "oct_amortization": 3000
          }
        }
      ]
    }
  ]
}
```

**Filtering**: Only include rows where `eligible == true`. Exclude ineligible/placeholder records.

### Metadata CSV
A separate CSV provides additional fields joined by `line_key`:
```csv
line_key,useful_life_months,narrative,account_number
FC-001,12,Field team annual plan,1510
```

### GL Balances JSON
Per-period GL balances by account key:
```json
{
  "field_comm_asset_1510": {
    "jul": 18750,
    "aug": 22500,
    "sep": 17250,
    "oct": 12000
  },
  "partner_comm_asset_1515": {
    "jul": 20000,
    "aug": 22750,
    "sep": 20000,
    "oct": 13250
  }
}
```

## Column Layout (4-month: Jul/Aug/Sep/Oct)

| Col | A | B | C | D | E | F | G | H | I | J | K | L | M | N | O | P | Q |
|-----|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Header | Payee | Beg Bal | Jul Cap | Jul Amort | Jul End | Aug Cap | Aug Amort | Aug End | Sep Cap | Sep Amort | Sep End | Oct Cap | Oct Amort | Oct End | Useful Life | Notes | Asset Account |

Compare to deferred revenue:
- **Capitalized** replaces Billings
- **Amortization** replaces Recognition
- **Payee** replaces Customer
- **Useful Life Months** replaces Contract Months
- **Asset Account** replaces Revenue Code

## Control Row Formulas (4-month: Jul/Aug/Sep/Oct)

For 3 line items (rows 6–8), control rows at 9–12:

### Period Totals (row 9)
- B9: `=SUM(B6:B8)`
- C9: `=SUM(C6:C8)` ... through N9
- O9: `=C9+F9+I9+L9` (total capitalized)

### Ending Balance (row 10)
- B10: `=B9` (MUST reference Period Totals, not empty)
- E10: `=B10+C9-D9` (Jul Ending = Beg + Cap - Amort from Period Totals)
- H10: `=E10+F9-G9` (Aug Ending)
- K10: `=H10+I9-J9` (Sep Ending)
- N10: `=K10+L9-M9` (Oct Ending)
- O10: `=D9+G9+J9+M9` (total amortized)

**CRITICAL**: The Ending Balance row's Beginning Balance (B10) must reference Period Totals (B9).

**WRONG**: `B10` empty or `=B10+C10-D10` — self-referencing, computes 0 + C - D
**RIGHT**: `B10` = `=B9`, `E10` = `=B9+C9-D9` — correctly rolls forward

### Variance (row 11)
- N11: `=N12-N10` (GL Balance Oct Ending minus Ending Balance Oct Ending)

**CRITICAL**: Variance formula MUST reference the Ending Balance row (N10), not compare two GL Balance cells.

**WRONG**: `=O12-N12` (comparing two GL cells)
**RIGHT**: `=N12-N10` (GL Balance minus Ending Balance)

### GL Balance (row 12)
- E12, H12, K12, N12: Hardcoded from GL JSON (Jul, Aug, Sep, Oct balances)
- O12: `=O9-O10` (total capitalized minus total amortized) or can be left empty

## Summary Sheet Pattern

Commission asset summaries typically show:
```
A1: Company Name
A2: Commission Asset Rollforward
A3: Period Ending: October 31, 2025

A5: Field Comm Asset #1510
A7: Total Capitalized    B7: ='Field Comm Asset #1510'!O9
A8: Total Amortization   B8: ='Field Comm Asset #1510'!O10
A9: Net                  B9: ='Field Comm Asset #1510'!O12

A11: Partner Comm Asset #1515
A12: Total Capitalized   B12: ='Partner Comm Asset #1515'!O9
A13: Total Amortization  B13: ='Partner Comm Asset #1515'!O10
A14: Net                 B14: ='Partner Comm Asset #1515'!O12

A16: Combined            B16: =B9+B14
```

Note: Cross-sheet references to sheet names with spaces or special characters must use single quotes: `='Field Comm Asset #1510'!O9`.

## Data Processing

### Filtering Eligible Records
```python
for section in activity_data['sections']:
    for row in section['rows']:
        if not row.get('eligible', False):
            continue  # Skip ineligible records
        # Process eligible record
```

### Joining Activity with Metadata
```python
metadata_lookup = {row['line_key']: row for row in metadata_rows}
for row in activity_rows:
    meta = metadata_lookup.get(row['line_key'])
    if meta:
        row['useful_life_months'] = int(meta['useful_life_months'])
        row['narrative'] = meta.get('narrative', '')
        row['account_number'] = meta['account_number']
```

### Sorting
Line items should be sorted by payee name, then by line_key:
```python
activity_rows.sort(key=lambda x: (x['payee_name'], x['line_key']))
```

## File Naming

Extract exact filename from task spec. Example: `Solstice_Commission_Assets_10-25.xlsx`
