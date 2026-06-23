---
name: financial-rollforward-workbook
description: Build multi-period Excel rollforward workbooks with formulas, cross-sheet references, and control rows. Use for rebate reserve schedules, accrual rollforwards, warranty reserves, commission assets, refund reserves, contract liability, prepaid amortization, or any period-over-period financial reconciliation spreadsheet.
---

# Financial Rollforward Workbook Builder

## When to Use
- Creating financial rollforward schedules (rebates, accruals, reserves, warranties, refunds, contract liability, prepaid amortization)
- Multi-sheet workbooks with summary + detail sheet structure
- Period-over-period balance tracking with GL reconciliation
- Data sourced from CSV schedules + JSON GL balances + optional patch files
- **Recognition trigger**: Any task with CSV containing beginning_balance, periodic adds/accruals, periodic amortization/utilization, and ending_balance columns, plus a separate JSON file with GL ending balances by account.

## Pre-Coding Checklist (MANDATORY - Do This First)

Before writing ANY formulas, write down these three items:

1. **Variance formula**: Must be `=N{gl_row}-N{ending_row}` (column N for BOTH operands)
2. **Ending Balance first period**: Must be `=B{period_totals}+C{period_totals}-D{period_totals}`
3. **Control row indices**: Period Totals = last_data_row + 1, Ending Balance = +2, Variance = +3, GL Balance = +4

If you don't write these down before coding, you will make mistakes.

## Workflow (MANDATORY sequence)

1. **RUN skeleton script first.** Load and adapt `scripts/build_rollforward.py`. Do NOT build from scratch.
2. **Parse input files.** Load CSV schedules, JSON GL balances, optional JSON account mappings, optional CSV overrides.
3. **Filter records.** Active/eligible only. For project cost: dedup by row_id (highest revision), apply CSV overrides.
4. **Write detail sheets.** Headers, data rows, control rows in exact order: Period Totals → Ending Balance → Variance → GL Balance.
5. **Write formulas.** Use exact patterns below. **Variance MUST use column N for both operands.**
6. **Write summary sheet.** Cross-sheet links to control rows. Sheet names with spaces need single quotes. **GL Balance links MUST use column N, not O.**
7. **Run quick validation.** `python scripts/quick_validate.py <workbook>` — catches the two most common fatal bugs in seconds.
8. **Run full validation script.** `python scripts/validate_rollforward.py <workbook>` before saving.
9. **Run the test suite.** `pytest test_output.py -v` — self-verification is insufficient.

## Core Structure

### Sheet Order
1. Summary sheet first (links to detail sheets)
2. Detail sheets in account number order
3. Each detail sheet follows identical row structure

### Detail Sheet Row Pattern
```
Row 5:    Headers (Partner, Beginning Balance, [Month] Adds/Amortization/Ending Balance..., Reserve Months, Notes, Expense Account)
Row 6-N:  Partner data rows with formulas
Row N+1:  Period Totals (SUM formulas)
Row N+2:  Ending Balance (references Period Totals for activity, prior ending for balance)
Row N+3:  Variance (GL vs calculated)
Row N+4:  GL Balance (hardcoded values from JSON)
```

### Period Column Layout (B-N)
| Col | Purpose |
|-----|--------|
| A | Partner/Description |
| B | Beginning Balance |
| C-D | Period 1 Adds / Amortization (or Accruals / Utilization) |
| E | Period 1 Ending Balance |
| F-G | Period 2 Adds / Amortization |
| H | Period 2 Ending Balance |
| I-J | Period 3 Adds / Amortization |
| K | Period 3 Ending Balance |
| L-M | Period 4 Adds / Amortization |
| N | Period 4 Ending Balance |
| O | Reserve/Result (formula) |

## Control Row Formula Patterns (CRITICAL)

### Data Row Ending Balance (Cascading)
```python
# Period 1: Beg + Adds - Amortization
ws['E6'] = '=B6+C6-D6'

# Period 2: Prior End + Adds - Amortization
ws['H6'] = '=E6+F6-G6'

# Period 3: Prior End + Adds - Amortization
ws['K6'] = '=H6+I6-J6'

# Period 4: Prior End + Adds - Amortization
ws['N6'] = '=K6+L6-M6'
```

### Period Totals Row
```python
# Sum each column across all data rows
first_row, last_row = 6, 8  # adjust based on partner count
ws['B9'] = f'=SUM(B{first_row}:B{last_row})'
ws['C9'] = f'=SUM(C{first_row}:C{last_row})'
# ... repeat for D through N

# Reserve column: sum of period adds
ws['O9'] = '=C9+F9+I9+L9'
```

### Ending Balance Control Row (CRITICAL)

**First period uses Beginning Balance from Period Totals:**
```python
# Row 10 = Ending Balance row
ws['E10'] = '=B9+C9-D9'   # Jul: Beg_Bal + Adds - Amort (references Period Totals row 9)
ws['H10'] = '=E10+F9-G9'  # Aug: Jul_End + Adds - Amort
ws['K10'] = '=H10+I9-J9'  # Sep: Aug_End + Adds - Amort
ws['N10'] = '=K10+L9-M9'  # Oct: Sep_End + Adds - Amort
ws['O10'] = '=E10+H10+K10+N10'  # Sum of ending balances
```

**Anti-pattern - Self-referencing:**
```python
# WRONG: Referencing own row instead of Period Totals
ws['E10'] = '=B10+C10-D10'  # WRONG! B10 is empty/zero

# RIGHT: Reference Period Totals row for beginning balance
ws['E10'] = '=B9+C9-D9'    # RIGHT! B9 has the Beginning Balance total
```

### Variance Row (CRITICAL - Most Common Bug)

**The correct formula uses column N for BOTH values:**
```python
# Row 11 = Variance row, Row 12 = GL Balance row
# Variance = GL Balance - Ending Balance, BOTH from column N

ws['N11'] = '=N12-N10'  # RIGHT: column N (GL) minus column N (Ending Balance)
ws['O11'] = '=O12-O10'  # RIGHT: same pattern for Reserve column
```

**Anti-patterns - WRONG formulas (these are the most common mistakes):**
```python
# WRONG: Using column O for GL
ws['N11'] = '=O12-N10'  # WRONG! GL is in column N, not O

# WRONG: Comparing two GL cells
ws['N11'] = '=O12-N12'  # WRONG! Both are GL Balance, meaningless

# WRONG: Wrong column reference
ws['N11'] = '=N12-O10'  # WRONG! GL should be first operand
```

### GL Balance Row
```python
# Row 12 = GL Balance row
# Static values from JSON source (not formulas)
ws['E12'] = gl_json['jan']    # Jan GL ending balance
ws['H12'] = gl_json['feb']    # Feb GL ending balance
ws['K12'] = gl_json['mar']    # Mar GL ending balance
ws['N12'] = gl_json['apr']    # Apr GL ending balance
ws['O12'] = '=O9-O10'         # Total additions - Total ending
```

### Cross-Sheet Summary Links
```python
# Sheet names with spaces require single quotes
sheet_name = "PPD Exp #1250"
summary['B7'] = f"='{sheet_name}'!O{totals_row}"   # Period Additions/Totals
summary['B8'] = f"='{sheet_name}'!O{ending_row}"  # Ending Balance
summary['B9'] = f"='{sheet_name}'!N{gl_row}"      # GL Balance (column N, NOT O)
summary['B10'] = f"='{sheet_name}'!N{variance_row}" # Variance
```

**CRITICAL**: Summary GL Balance links must use column N (`!N{gl_row}`), not column O. This is the most common summary sheet bug.

## Column Layout (standard)
| Col | Purpose |
|-----|---------|
| A | Partner/Description |
| B | Beginning Balance |
| C-D | Period 1 Adds/Amortization (or Accruals/Utilization) |
| E | Period 1 Ending |
| F-G | Period 2 Adds/Amortization |
| H | Period 2 Ending |
| I-J | Period 3 Adds/Amortization |
| K | Period 3 Ending |
| L-M | Period 4 Adds/Amortization |
| N | Period 4 Ending |
| O | Reserve/Formula column |

## Validation Steps

1. **Quick validation** (fast, catches fatal bugs): `python scripts/quick_validate.py <workbook_path>`
2. **Run test suite** (mandatory, not optional): `pytest test_output.py -v`
3. **Run full validation script** before submitting: `python scripts/validate_rollforward.py <workbook_path>`
4. **Inspect formulas manually**: Load with `data_only=False` and print Variance cell
5. **Verify Variance uses column N**: Check that formula is `=N{X}-N{Y}`, NOT `=O{X}-N{Y}`
6. **Verify Summary GL links use column N**: Check summary sheet GL Balance rows reference `!N{gl_row}`, not `!O{gl_row}`

## Known Invariants (by sub-task)

### rebate-reserve variant
- Sheet names match account names exactly (e.g., "Channel Rebates #6120")
- GL Balance values in column N (E, H, K, N)
- Variance = N(GL_row) - N(Ending_Balance_row)

### warranty-reserve variant
- Filter to `record_status='active'` before processing
- Account mapping JSON maps bucket/code to sheet name

### commission-asset variant
- Nested JSON with `sections`→`rows`→`eligible` flags
- Filter to `eligible=true`
- Metadata joined via `line_key`
- Sort by payee name then line_key

### project-cost variant
- Dedup by row_id (keep highest revision)
- Apply CSV overrides keyed by row_id

### refund-reserve variant
- Filter approved detail rows with `row_kind='detail'`
- Dedupe by case_id keeping highest version
- Apply CSV adjustments by case_id
- Insert new rows from adjustments file

### contract-liability variant
- Filter out `record_type='summary'` and `active_flag=false`
- Dedup by contract_key keeping highest revision
- Apply bridge CSV overrides/inserts after normalization
- Bridge CSV columns: `dec_adds`, `dec_release`, `comments`, `account_number`
- Sort by customer name then contract_key

### prepaid-amortization variant
- CSV columns: `vendor`, `beginning_balance`, `{month}_adds`, `{month}_amortization`, `{month}_ending_balance`, `amortization_months`, `comments`, `account_number`
- GL balances JSON keyed by account name (e.g., `prepaid_expenses_1250`, `prepaid_insurance_1251`) with month keys (`jan`, `feb`, `mar`, `apr`)
- Sheet names derived from account number with prefix (e.g., "PPD Exp #1250", "PPD Ins #1251")
- Summary sheet titled "Prepaid Summary" with sections per account
- Same control row formula patterns apply; terminology differs (adds/amortization vs accruals/utilization)

## Anti-Patterns

| Wrong | Why | Right |
|-------|-----|-------|
| `=O12-N10` | GL is in column N, not O | `=N12-N10` |
| `=O12-N12` | Both operands are GL Balance | `=N12-N10` |
| `=B10+C10-D10` | B10 is empty (self-reference) | `=B9+C9-D9` |
| `=SUM(B6:8)` | Missing column letter | `=SUM(B6:B8)` |
| `=Sheet!A1` | Unquoted sheet name with spaces | `='Sheet Name'!A1` |
| Summary GL link `!O{gl_row}` | GL Balance lives in column N | `!N{gl_row}` |
| Building from scratch | Loses template structure, error-prone | Adapt `scripts/build_rollforward.py` |
| Skipping validation | Fatal bugs slip through | Run `quick_validate.py` first |
| Skipping test suite | Self-verification misses structural bugs | Run `pytest test_output.py -v` |

## References

- `references/control-rows-template.md` - Exact formula templates for all control rows
- `scripts/build_rollforward.py` - Skeleton script to adapt (MANDATORY)
- `scripts/validate_rollforward.py` - Post-build assertion script (run before submitting)
- `scripts/quick_validate.py` - Fast pre-submission check for the two most common fatal bugs

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.
