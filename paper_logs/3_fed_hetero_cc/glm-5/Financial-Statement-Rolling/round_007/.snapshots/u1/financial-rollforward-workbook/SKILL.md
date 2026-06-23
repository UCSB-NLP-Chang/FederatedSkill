---
name: financial-rollforward-workbook
description: Build multi-sheet Excel financial rollforward workbooks with formulas, cross-sheet references, and control rows. Use for rebate reserve schedules, accrual rollforwards, warranty reserves, commission assets, refund reserves, or any period-over-period financial reconciliation spreadsheet.
---

# Financial Rollforward Workbook Builder

## When to Use
- Creating financial rollforward schedules (rebates, accruals, reserves, warranties, refunds)
- Multi-sheet workbooks with summary + detail sheet structure
- Period-over-period balance tracking with GL reconciliation
- Data sourced from CSV schedules + JSON GL balances + optional patch files
- **Template-based builds**: When task provides an existing `.xlsx` template to populate (see Template-Based Workflow below)

## Pre-Coding Checklist (MANDATORY - Do This First)

Before writing ANY formulas, write down these three items:

1. **Variance formula**: Must be `=N{gl_row}-N{ending_row}` (column N for BOTH operands)
2. **Ending Balance first period**: Must be `=B{period_totals}+C{period_totals}-D{period_totals}`
3. **Control row indices**: Period Totals = last_data_row + 1, Ending Balance = +2, Variance = +3, GL Balance = +4

If you don't write these down before coding, you will make mistakes.

## Core Structure

### Sheet Order
1. Summary sheet first (links to detail sheets)
2. Detail sheets in account number order
3. Each detail sheet follows identical row structure

### Detail Sheet Row Pattern
```
Row 5:    Headers (Partner, Beginning Balance, [Month] Accruals/Utilization/Ending Balance..., Reserve Months, Notes, Expense Account)
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
| C-D | Period 1 Accruals / Utilization |
| E | Period 1 Ending Balance |
| F-G | Period 2 Accruals / Utilization |
| H | Period 2 Ending Balance |
| I-J | Period 3 Accruals / Utilization |
| K | Period 3 Ending Balance |
| L-M | Period 4 Accruals / Utilization |
| N | Period 4 Ending Balance |
| O | Reserve/Result (formula) |

## Formula Patterns

### Data Row Ending Balance (Cascading)
```python
# Period 1: Beg + Accruals - Utilization
ws['E6'] = '=B6+C6-D6'

# Period 2: Prior End + Accruals - Utilization
ws['H6'] = '=E6+F6-G6'

# Period 3: Prior End + Accruals - Utilization
ws['K6'] = '=H6+I6-J6'

# Period 4: Prior End + Accruals - Utilization
ws['N6'] = '=K6+L6-M6'
```

### Period Totals Row
```python
# Sum each column across all data rows
first_row, last_row = 6, 8  # adjust based on partner count
ws['B9'] = f'=SUM(B{first_row}:B{last_row})'
ws['C9'] = f'=SUM(C{first_row}:C{last_row})'
# ... repeat for D through N

# Reserve column: sum of period accruals
ws['O9'] = '=C9+F9+I9+L9'
```

### Ending Balance Control Row (CRITICAL)

**First period uses Beginning Balance from Period Totals:**
```python
# Row 10 = Ending Balance row
ws['E10'] = '=B9+C9-D9'   # Jul: Beg_Bal + Accruals - Util (references Period Totals row 9)
ws['H10'] = '=E10+F9-G9'  # Aug: Jul_End + Accruals - Util
ws['K10'] = '=H10+I9-J9'  # Sep: Aug_End + Accruals - Util
ws['N10'] = '=K10+L9-M9'  # Oct: Sep_End + Accruals - Util
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
ws['E12'] = gl_json['jul']    # Jul GL ending balance
ws['H12'] = gl_json['aug']    # Aug GL ending balance
ws['K12'] = gl_json['sep']    # Sep GL ending balance
ws['N12'] = gl_json['oct']    # Oct GL ending balance
ws['O12'] = '=O9-O10'         # Total additions - Total ending
```

### Cross-Sheet Summary Links
```python
# Sheet names with spaces require single quotes
sheet_name = "Channel Rebates #6120"
summary['B7'] = f"='{sheet_name}'!O9"   # Period Additions
summary['B8'] = f"='{sheet_name}'!O10"  # Ending Balance
summary['B9'] = f"='{sheet_name}'!O12"  # GL Balance
summary['B10'] = f"='{sheet_name}'!N11" # Variance
```

## Validation Steps

1. **Run test suite** (mandatory, not optional): `pytest test_output.py -v`
2. **Run validation script** before submitting: `python scripts/validate_rollforward.py <workbook_path>`
3. **Inspect formulas manually**: Load with `data_only=False` and print Variance cell
4. **Verify Variance uses column N**: Check that formula is `=N{X}-N{Y}`, NOT `=O{X}-N{Y}`

## Template-Based Workflow (when template.xlsx provided)

When the task provides an existing Excel template file to populate, use this workflow instead of building from scratch.

### Key Differences from Scratch Build
- **Input**: Load existing template with `openpyxl.load_workbook(template_path)` — preserve all formatting
- **Output**: Data populated into template structure, template formatting preserved
- **Validation**: MUST run actual test suite; self-verification is insufficient

### Template Workflow Steps

1. **Load template first** (MANDATORY):
   ```python
   wb = load_workbook(template_path)  # NOT Workbook()
   ```
   Check for placeholder text (e.g., "OLD TEMPLATE" in A1) to confirm template loaded.

2. **Parse and normalize data**:
   - Filter: Keep `approved=true` AND `row_kind='detail'` records
   - Dedup: Group by `case_id`/`row_id`, keep highest `version`
   - Overrides: CSV with `action=override` modifies existing records by key
   - Insertions: CSV with `action=insert` adds new records to correct bucket

3. **Populate detail sheets**: Write data into template's existing row structure. Do NOT recreate headers.

4. **Write control rows**: Use formula patterns above (Period Totals → Ending Balance → Variance → GL Balance).

5. **Build summary sheet**: Cross-sheet links with aligned row positions:
   ```python
   # CORRECT: Label and formula in same row
   ws['A7'] = 'Period Totals'
   ws['B7'] = f"='Sheet Name'!O{pt_row}"
   ws['A8'] = 'Ending Balance'
   ws['B8'] = f"='Sheet Name'!O{eb_row}"
   ws['A9'] = 'GL Balance'
   ws['B9'] = f"='Sheet Name'!N{gl_row}"  # N not O!
   ```

6. **Run actual test suite**: `pytest test_output.py -v` — self-verification passing does NOT guarantee test suite passing.

### Template Anti-Patterns

| Wrong | Right | Why |
|-------|-------|-----|
| `Workbook()` | `load_workbook(template)` | Loses template formatting |
| Self-verification | Run pytest | Self-verification ≠ test suite |
| `='Sheet'!O{gl_row}` | `='Sheet'!N{gl_row}` | GL Balance in column N |
| Label A7, formula B8 | Same row | Off-by-one alignment |

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

### template-based variant
- Load existing template.xlsx, preserve formatting
- Data normalization: filter → dedup → overrides → insertions
- CSV overrides may target nested paths (e.g., `nov_adds` → `flow_months.nov.accrued`)
- Summary GL Balance links use column N (not O)
- Self-verification insufficient: MUST run actual test suite

## Anti-Patterns

| Wrong | Why | Right |
|-------|-----|-------|
| `=O12-N10` | GL is in column N, not O | `=N12-N10` |
| `=O12-N12` | Both operands are GL Balance | `=N12-N10` |
| `=B10+C10-D10` | B10 is empty (self-reference) | `=B9+C9-D9` |
| `=SUM(B6:8)` | Missing column letter | `=SUM(B6:B8)` |
| `=Sheet!A1` | Unquoted sheet name with spaces | `='Sheet Name'!A1` |

## References

- `references/formula-reference.md` - Complete formula templates by control row type
- `scripts/validate_rollforward.py` - Post-build assertion script (run before submitting)

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.
