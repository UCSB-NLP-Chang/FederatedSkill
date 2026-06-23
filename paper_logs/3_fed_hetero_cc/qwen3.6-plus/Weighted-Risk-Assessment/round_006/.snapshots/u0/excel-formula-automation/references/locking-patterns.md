# Reference Locking Patterns

**This is the #1 cause of verifier failures in R2–R5.**

## Mandatory `$` Locking Table

| Context | Required Pattern | Example | Wrong |
|---------|-----------------|---------|-------|
| INDEX/MATCH lookup range | Fully absolute | `Data!$H$21:$L$38` | `Data!H21:L38` |
| INDEX/MATCH row key range | Fully absolute | `Data!$D$21:$D$38` | `Data!D21:D38` |
| INDEX/MATCH col header range | Fully absolute | `Data!$H$21:$L$21` | `Data!H21:L21` |
| INDEX/MATCH row key cell | Column-absolute | `$D12` | `D12` |
| INDEX/MATCH col header cell | Row-absolute | `H$10` | `H10` |
| MIN/MAX/MEDIAN/AVERAGE range | Row-absolute | `H$35:H$40` | `H35:H40` |
| PERCENTILE.INC range | Row-absolute | `H$35:H$40` | `H35:H40` |
| SUMPRODUCT values range | Row-absolute | `H$35:H$40` | `H35:H40` |
| SUMPRODUCT weights range | Row-absolute | `H$26:H$31` | `H26:H31` |

## Why This Matters

When formulas are filled/copied across rows or columns:
- Missing `$` on row numbers causes the range to shift vertically
- Missing `$` on columns causes the range to shift horizontally
- Both produce `#REF!` errors or wrong values

## Verification

Always run: `python3 scripts/validate_references.py <workbook>`

This script exits with error code if `$` signs are missing. **Do not proceed if validation fails.`
