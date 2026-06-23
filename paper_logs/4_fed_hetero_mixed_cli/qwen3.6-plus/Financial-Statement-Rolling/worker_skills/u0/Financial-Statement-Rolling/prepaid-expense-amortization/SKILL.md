---
name: prepaid-expense-amortization
description: Build prepaid expense and insurance amortization rollforward workbooks from flat CSV source data. Use when tracking prepaid software subscriptions, IT services, insurance policies, or technical service fees with monthly adds and amortization. Distinct from deferred revenue: uses running balance formulas in Ending Balance control row (E=B+C-D chain), requires linking Month Totals cells to Ending Balance row, and links summary to column O (total amortization).
---

# Prepaid Expense Amortization Workbook Builder

## STOP: CHOOSE THE RIGHT PATTERN

**This skill uses RUNNING BALANCE formulas, not SUM.**

| Criterion | Financial Rollforward (SUM) | Prepaid Expense (Running Balance) |
|-----------|----------------------------|-----------------------------------|
| Ending Balance control row | `=SUM(E6:E8)` | `=B{r}+C{totals}-D{totals}` chain |
| Summary links | Column N (final period ending) | Column O (total amortization) |
| Input format | Flat CSV or JSON | Flat CSV with vendor-level line items |

**Decision Rule:**
```python
if task involves 'prepaid' or 'amortization' and source is flat CSV:
    use this skill (running balance pattern)
elif task involves 'deferred revenue' or 'accrual':
    use financial-rollforward-workbook skill (SUM pattern)
```

## When to Use

- Prepaid expense schedules (software, IT services, subscriptions)
- Insurance policy amortization schedules
- Technical service fee amortization
- Flat CSV input with columns: vendor, beginning_balance, [month]_adds, [month]_amortization, [month]_ending_balance, amortization_months, comments, account_number
- Monthly adds and amortization tracking across 4+ periods

## Column Layout

| Col | Header | Content |
|-----|--------|---------|
| A | Vendor | Vendor name |
| B | Beginning Balance | Opening balance |
| C | [Month] Adds | Monthly additions |
| D | [Month] Amortization | Monthly amortization |
| E | [Month] Ending Balance | Monthly ending |
| F-H | (repeat for month 2) | Adds, Amortization, Ending |
| I-K | (repeat for month 3) | Adds, Amortization, Ending |
| L-N | (repeat for month 4) | Adds, Amortization, Ending |
| O | Amortization Months | Term in months |
| P | Comments | Notes |
| Q | Account Number | GL account |

Headers at row 5. Data rows start at row 6.

## Control Row Formulas

Compute positions dynamically:
```python
totals_row = start_row + len(data_rows)
ending_row = totals_row + 1
variance_row = ending_row + 1
gl_row = variance_row + 1
```

### Month Totals Row

- Columns B-N: `=SUM(B{start}:B{end})` etc.
- Column O: `=C{totals_row}+F{totals_row}+I{totals_row}+L{totals_row}` (total adds)

### Ending Balance Row — RUNNING BALANCE CHAIN

**CRITICAL: You MUST link the adds/amortization columns from Month Totals to the Ending Balance row BEFORE writing the rollforward formulas.**

```python
# STEP 1: Link B, C, D, F, G, I, J, L, M from Month Totals
ws.cell(row=ending_row, column=2, value=f"=B{totals_row}")   # Beginning
ws.cell(row=ending_row, column=3, value=f"=C{totals_row}")   # Adds
ws.cell(row=ending_row, column=4, value=f"=D{totals_row}")   # Amortization
ws.cell(row=ending_row, column=6, value=f"=F{totals_row}")
ws.cell(row=ending_row, column=7, value=f"=G{totals_row}")
ws.cell(row=ending_row, column=9, value=f"=I{totals_row}")
ws.cell(row=ending_row, column=10, value=f"=J{totals_row}")
ws.cell(row=ending_row, column=12, value=f"=L{totals_row}")
ws.cell(row=ending_row, column=13, value=f"=M{totals_row}")

# STEP 2: Write rollforward formulas (these reference the linked cells above)
ws.cell(row=ending_row, column=5, value=f"=B{ending_row}+C{ending_row}-D{ending_row}")    # E
ws.cell(row=ending_row, column=8, value=f"=E{ending_row}+F{ending_row}-G{ending_row}")    # H
ws.cell(row=ending_row, column=11, value=f"=H{ending_row}+I{ending_row}-J{ending_row}")   # K
ws.cell(row=ending_row, column=14, value=f"=K{ending_row}+L{ending_row}-M{ending_row}")   # N
ws.cell(row=ending_row, column=15, value=f"=D{totals_row}+G{totals_row}+J{totals_row}+M{totals_row}")  # O = total amortization
```

**Why this matters**: Without Step 1, the rollforward formulas reference empty cells and produce 0. The formulas reference different columns on the same row — this is a valid running balance pattern, NOT a circular reference.

### GL Balance Row

- Columns E, H, K, N: Hard-coded values from JSON keyed by account and period
- Column O: `=O{totals_row}-O{ending_row}` (total adds minus total amortization)

### Variance Row

- Column O: `=O{gl_row}-N{gl_row}`

## Summary Sheet

Link to **column O** of control rows, NOT column N:
```python
ws_summary.cell(row=7, column=2, value=f"='PPD Exp #1250'!O{totals_row}")
ws_summary.cell(row=8, column=2, value=f"='PPD Exp #1250'!O{ending_row}")
ws_summary.cell(row=9, column=2, value=f"='PPD Exp #1250'!O{gl_row}")
```

Quote sheet names containing spaces or special characters (#).

## Anti-Patterns

| Issue | Wrong | Right |
|-------|-------|-------|
| Ending Balance formulas | `=SUM(E6:E8)` | Running balance chain with linked totals |
| Missing totals links | Rollforward formulas reference empty cells | Link B,C,D,F,G,I,J,L,M from Month Totals first |
| Summary links | Link to column N (final period ending) | Link to column O (total amortization) |
| Verifier false positives | Trusting circular reference warning for same-row different-column refs | These are valid running balance formulas; verify manually |
| GL column O | Hard-coded value | Formula: `=O{totals}-O{ending}` |

## Verification

Run `scripts/verify_workbook.py` from `financial-rollforward-workbook` skill directory.

**Note on false positives**: The verifier may flag same-row references in the Ending Balance row as circular. For running balance formulas like `=B48+C48-D48`, these reference different columns on the same row and are NOT circular. Verify manually that no formula references its own exact cell (e.g., E48 should not contain `E48`).

## Validation Checklist

1. Data rows written starting at row 6, sorted by vendor name
2. Month Totals: SUM for B-N, adds formula for O
3. Ending Balance: Link B,C,D,F,G,I,J,L,M from Month Totals, then write rollforward chain
4. GL Balance: Hard-coded values in E/H/K/N, O = totals O - ending O
5. Variance: O = GL O - GL N
6. Summary: Links to column O of control rows
7. Cross-sheet references use single quotes for sheet names with spaces or #
8. Number format `#,##0.00` applied to all monetary columns
