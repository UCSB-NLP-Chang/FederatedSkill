---
name: transit-subsidy-rollforward
description: Multi-program reconciliation workbook pattern for transit pass liability tracking, media rights rollforwards, or any paired-asset reconciliation (e.g., Bus+Rail, Film+Music, Harbor+Storage). Use when building workbooks with multiple detail sheets that aggregate to a summary with cross-sheet formula linking.
---

# Multi-Program Reconciliation Pattern

Build reconciliation workbooks with multiple detail sheets (e.g., Bus+Rail, Film+Music) that aggregate to a summary sheet with cross-sheet formula linking.

**Applies to**: Transit subsidy pass liability (Bus + Rail programs), Media rights rollforwards (Film + Music), Intangible asset reconciliations with paired categories, Harbor/Storage capacity reconciliations.

## Key Structural Differences from Single-Program

| Aspect | Single-Program (Harbor) | Multi-Program (Transit/Media Rights) |
|--------|------------------------|--------------------------------------|
| Summary GL Balance | Static value from JSON | Formula linking to detail sheets: `='Bus'!B16+'Rail'!B16` |
| Month Totals | Single row | Aggregate row: `=B7+B8` (sum of program rows) |
| Total Ending | N/A or simple | `=B9+B14` (month totals + GL balance) |
| Detail Sheets | One | Two or more (e.g., Film #2710 + Music #2720) |

## Summary Sheet Structure

| Row | Purpose | Formula Pattern |
|-----|---------|-----------------|
| 7-8 | Program rows | Link to each detail sheet's Month Totals row |
| 9 | Month Totals | `=B7+B8` (aggregate across programs) |
| 12 | Ending Balance | `=B9` (links to Month Totals) |
| 13 | Variance | `=B14-B12` (GL minus Ending Balance) |
| 14 | GL Balance | **Formula** linking to detail sheets, NOT static values |
| 16 | Total Ending | `=B9+B14` (month totals + GL balance) |

**Critical**: GL Balance row (14) must reference detail sheets via formulas to maintain audit trail and allow tracing.

```python
# GL Balance references detail sheets
ws_summary['B14'] = "='Bus Program #4310'!B16+'Rail Program #4320'!B16"  # Jan
ws_summary['E14'] = "='Bus Program #4310'!E16+'Rail Program #4320'!E16"  # Feb
# ... etc for each month column through totals
ws_summary['N14'] = "='Bus Program #4310'!N16+'Rail Program #4320'!N16"  # Total column
```

## Detail Sheet Structure (Each Program)

Same structure for both/all detail sheets:

| Row | Content | Example |
|-----|---------|---------|
| 1-5 | Title and metadata | "Aurora Stream - Film Rights Rollforward" |
| 6 | Column headers | Vendor, Beginning Balance, Jan Adds, Jan Amortization, Jan Ending Balance, ... |
| 7-12 | Data rows (6 vendors typical) | Silver Screen Studios, 5747.32, ... |
| 13 | Month Totals | `=SUM(B7:B12)` for each month column |
| 14 | Ending Balance | `=B13` (links to Month Totals) |
| 15 | Variance | `=B16-B14` (GL minus Ending Balance) |
| 16 | GL Balance | Static value from JSON source |
| O column | Summary links | `=E13`, `=H13`, etc. pointing to each month's Ending Balance |

**Row Position Rule**: Calculate control row positions dynamically based on data length:
```python
first_data_row = 7
control_start = first_data_row + len(df) + 1  # +1 for gap row
month_totals_row = control_start
ending_balance_row = control_start + 1
variance_row = control_start + 2
gl_balance_row = control_start + 3
```

## Cross-Sheet Linking Strategy

```python
# Summary row 7-8 links to detail sheets' Month Totals
col_letters = ['B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O']
for col in col_letters:
    ws_summary[f'{col}7'] = f"='Film Rights #2710'!{col}13"  # Jan, Feb, Mar, Apr, totals
    ws_summary[f'{col}8'] = f"='Music Rights #2720'!{col}13"

# Month totals aggregates programs
for col in col_letters:
    ws_summary[f'{col}9'] = f'={col}7+{col}8'

# Ending Balance links to month totals
for col in col_letters:
    ws_summary[f'{col}12'] = f'={col}9'

# Variance = GL - Ending (note direction)
for col in col_letters:
    ws_summary[f'{col}13'] = f'={col}14-{col}12'

# GL Balance links to detail sheets (formula, not static)
for col in col_letters:
    ws_summary[f'{col}14'] = f"='Film Rights #2710'!{col}16+'Music Rights #2720'!{col}16"

# Total Ending
ws_summary['C16'] = '=C9+C14'  # Film variance + Music variance (or adjust columns as needed)
```

## Media Rights / Film Rights Specifics

When applying this pattern to media rights (Film #2710 + Music #2720):

1. **Account numbers** in source data identify the program (2710=Film, 2720=Music)
2. **GL balances** come from JSON with keys matching account identifiers
3. **Vendor line items** include: beginning_balance, monthly adds/amortization/ending_balance
4. **Same control row structure** as transit subsidy
5. **Same summary formula patterns** - just different sheet names

Example input CSV structure:
```
vendor,beginning_balance,jan_adds,jan_amortization,jan_ending_balance,...
Silver Screen Studios,5747.32,13079.6,3137.82,15689.1,...,2710
Auric Music Group,4563.93,23518.83,4680.46,23402.3,...,2720
```

## Column O Convention for Summary Links

In detail sheets, place formulas in column O to expose ending balances for summary reference:

```python
# In Film Rights #2710 detail sheet
ws['O6'] = "=E13"   # Jan ending balance (column E = Jan Ending Balance)
ws['O7'] = "=H13"   # Feb ending balance (column H = Feb Ending Balance)
ws['O8'] = "=K13"   # Mar ending balance
ws['O9'] = "=N13"   # Apr ending balance
# O10 could hold totals if needed
```

Then summary references these:
```python
ws_summary['C7'] = "='Film Rights #2710'!O6"   # Jan rollforward ending
ws_summary['C8'] = "='Music Rights #2720'!O6"  # Jan rollforward ending
```

## Validation Checklist

1. **Sheet order**: Summary first, then detail sheets in consistent order
2. **Control rows**: Position calculated dynamically from data length, not hardcoded
3. **Summary GL Balance**: Must be formulas linking to details, never static JSON values
4. **Variance direction**: GL - Ending Balance (positive = under-recorded liability)
5. **Cross-sheet references**: Sheet names quoted if containing spaces/hashes: `'Film Rights #2710'`
6. **Numeric types**: All values written as Python int/float, not strings
7. **Formula verification**: Load with `data_only=False`, check `.value` shows `=` prefix
8. **Aggregation math**: Month totals (row 9) = sum of program rows; Total ending = variance sum

## Common Errors to Avoid

| Error | Cause | Prevention |
|-------|-------|------------|
| GL balances only in total column | Static placement | Write GL to all month columns B-E, not just N |
| Static GL in summary | Copied from single-program pattern | Use formulas: `='Film'!B16+'Music'!B16` |
| Control rows misaligned | Hardcoded row numbers | Calculate: `control_start = 7 + len(df) + 1` |
| Variance sign reversed | Wrong subtraction order | GL - Ending, not Ending - GL |
| Missing quotes in references | Sheet names with spaces | `'Film Rights #2710'` not `Film Rights #2710` |
| Summary references wrong column | Confusing data cols with O column | O column holds the link formulas, not data columns |

## Complete Implementation Template

See `../scripts/reconciliation_template.py` for runnable code. Adapt sheet names and account numbers for your specific domain (transit, media rights, harbor/storage, etc.).
