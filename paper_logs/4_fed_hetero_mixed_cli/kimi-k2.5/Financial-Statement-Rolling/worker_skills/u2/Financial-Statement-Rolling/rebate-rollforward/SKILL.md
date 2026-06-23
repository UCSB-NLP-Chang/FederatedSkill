---
name: rebate-rollforward
description: Build rebate, market development fund (MDF), refund reserve, contract liability, and prepaid expense amortization rollforward workbooks with running balance formulas. Use when source data tracks adds/releases (or booked/earned, accrued/credited, capitalized/amortized) per period and Ending Balance must be computed via running balance chain (E=B+C-D, H=E+F-G). Critical distinction from standard rollforwards: data rows contain adds/releases only, NOT pre-calculated ending balances. Use for nested JSON with revision tracking, CSV patches with override/insert actions, record type filtering (detail vs summary), and bucket routing via aliases.
---

# Rebate / Refund Reserve / Contract Liability / Prepaid Expense Rollforward

## STOP: THE #1 BUG — WRONG ROW REFERENCE IN ENDING BALANCE FORMULAS

**Every round, agents write Ending Balance formulas that reference the wrong row. This produces zeros or incorrect values.**

### The Bug Pattern

When writing the Ending Balance row's formulas, you MUST reference the **Period Totals row** for adds/releases, NOT the Ending Balance row itself.

| Column | WRONG (references empty cells) | RIGHT (references Period Totals) |
|--------|-------------------------------|----------------------------------|
| E | `=B{ending}+C{ending}-D{ending}` | `=B{ending}+C{totals}-D{totals}` |
| H | `=E{ending}+F{ending}-G{ending}` | `=E{ending}+F{totals}-G{totals}` |
| K | `=H{ending}+I{ending}-J{ending}` | `=H{ending}+I{totals}-J{totals}` |
| N | `=K{ending}+L{ending}-M{ending}` | `=K{ending}+L{totals}-M{totals}` |
| **O** | `=D{ending}+G{ending}+J{ending}+M{ending}` | `=D{totals}+G{totals}+J{totals}+M{totals}` |

### Why This Happens

Copy-paste error: you write `=D{row}+G{row}+J{row}+M{row}` using the current row number instead of the totals row number.

### MANDATORY CHECKPOINT

Before writing ANY Ending Balance formula, ask:
1. What row is the **Period Totals** row? (e.g., row 47)
2. What row is the **Ending Balance** row? (e.g., row 48)
3. Does this formula reference the Ending Balance row for adds/releases?
4. If YES → STOP. Use Period Totals row instead.

### Verification Script

**RUN `scripts/verify_workbook.py` BEFORE CLAIMING COMPLETION.** It catches this exact bug.

---

## STOP: CHOOSE THE RIGHT ROLLFORWARD PATTERN

**The #2 failure mode is applying the wrong formula pattern. Two mutually exclusive patterns exist:**

| Criterion | Financial Rollforward (SUM Pattern) | Rebate/Contract Liability/Prepaid (Running Balance Pattern) |
|-----------|-------------------------------------|-------------------------------------------------------------|
| **Data row content** | Pre-calculated ending balances per period | Adds/releases (or booked/earned, capitalized/amortized) per period only |
| **Ending Balance control row** | `=SUM(E6:E8)` — sums data row ending balances | `=B{r}+C{totals}-D{totals}` — computes running balance |
| **Source data shape** | Flat CSV/JSON with ending_balance fields | Nested JSON with month_roll {adds, release} fields |
| **Revision handling** | Usually none | Deduplicate by key, keep highest revision |
| **Active filtering** | status == 'active' | record_type == 'detail' AND approved == true |

**Decision Rule:**
```python
# Check the first data row's fields
if 'ending_balance' in data_row and data_row['ending_balance'] is not None:
    # Use financial-rollforward-workbook skill (SUM pattern)
else:
    # Use this skill (running balance pattern)
```

---

## When to Use

- Rebate reserve schedules (Channel Rebates, MDF Accruals)
- Marketing development fund rollforwards
- Refund reserve schedules with accrued/credited tracking
- Contract liability schedules with billings/revenue tracking
- **Prepaid expense amortization schedules** (Adds/Amortization per period)
- Any rollforward with adds/releases per period where Ending Balance uses running balance chain
- CSV patches that override specific fields or insert new rows
- Source data filtered by status field (e.g., status=open) or approval flags (approved=true, row_kind=detail, active_flag=true)

---

## Data Source Variants

### Variant A: Flat CSV/JSON with status filtering

Filter to `status=="open"` or `active_flag==true`. See workflow below.

### Variant B: Nested JSON Snapshot with version dedup (Refund Reserve pattern)

Source JSON has structure: `segments[] -> snapshots[]`. Each snapshot has:
- `case_id`, `version` (int), `approved` (bool), `row_kind` (string)
- `customer_name`, `opening_amount`, `flow_months`, `term_hint`, `memo_text`, `account_code`
- `flow_months`: `{aug, sep, oct, nov}` each with `{accrued, credited}`

**Filter**: Keep only items where `approved == true` AND `row_kind == "detail"`.

**Deduplicate**: Group by `case_id`, keep the item with the highest `version` number.

### Variant C: Contract Liability with bucket routing

Source JSON has structure: `exports[] -> clusters[] -> records[]`. Each record has:
- `contract_key`, `revision_no`, `active_flag` (bool), `record_type` (string)
- `party_name`, `opening_amount`, `contract_months`, `notes`, `liability_account`
- `month_roll`: `{sep, oct, nov, dec}` each with `{booked, earned}`

**Filter**: Keep only items where `active_flag == true` AND `record_type == "detail"`.

**Deduplicate**: Group by `contract_key`, keep the item with the highest `revision_no`.

### Variant D: Prepaid Expense Amortization

Source JSON has structure: `accounts[] -> line_items[]`. Each item has:
- `vendor_name`, `beginning_balance`, `useful_life_months`, `memo`, `account_number`
- `months`: `{jan, feb, mar, apr}` each with `{adds, amortization, ending_balance}`

**Column mapping**:
- `adds` → Adds column (capitalized/prepaid)
- `amortization` → Amortization column (expense recognition)
- `useful_life_months` → Term Months (column O)
- `memo` → Notes (column P)
- `account_number` → Account Number (column Q)

**Control rows**: Month Totals, Ending Balance, Variance, GL Balance

---

## Workflow

### 1. Load and Filter Source Data

**CRITICAL: Apply the correct filter for your data source.**

- Variant A: Filter to `status=="open"` or `active_flag==true`
- Variant B: Filter to `approved==true` AND `row_kind=="detail"`
- Variant C: Filter to `active_flag==true` AND `record_type=="detail"`
- Variant D: Usually no filtering needed (all line items are active)

### 2. Apply CSV Patches (if applicable)

Patch file columns: `action, target_bucket, row_id, customer_name, beginning_balance, aug_adds, aug_release, ...`

**CRITICAL: Never manually count commas to determine field alignment. Always use Python's `csv.DictReader`:**

```python
import csv
with open('adjustments.csv', newline='') as f:
    reader = csv.DictReader(f)
    print('Fieldnames:', reader.fieldnames)
    for row in reader:
        for k, v in row.items():
            print(f'  {k!r}: {v!r}')
```

**Override action**: Match by row_id (or case_id/contract_key), apply only non-empty fields.

**Insert action**: Add new row. **CRITICAL: Set status/approval flag**:
```python
new_row['status'] = 'open'  # INSERTED ROWS GET FILTERED OUT WITHOUT THIS
```

### 3. Clear Template Content (if applicable)

If working from a template workbook, **clear any old template content from row 6 downward** before writing.

### 4. Sort and Write Data Rows

Sort by customer/partner/vendor name, then by row_id/case_id/contract_key.

Write data rows starting at row 6. Apply `#,##0.00` format to monetary columns.

### 5. Build Control Rows

Compute positions dynamically:
```python
totals_row = start_row + len(data_rows)
ending_row = totals_row + 1
variance_row = ending_row + 1
gl_row = variance_row + 1
```

#### Period Totals Row

- Columns B-N: `=SUM(B{start}:B{end})` etc.
- Column O (total adds): `=C{totals_row}+F{totals_row}+I{totals_row}+L{totals_row}`

**CRITICAL: SUM formula construction in openpyxl**

```python
# WRONG: Missing column letter after colon
formula = f"=SUM({col_letter}{start}:{end})"  # produces =SUM(B6:8)

# RIGHT: Column letter on both sides
formula = f"=SUM({col_letter}{start}:{col_letter}{end})"  # produces =SUM(B6:B8)
```

#### Ending Balance Row — RUNNING BALANCE CHAIN

**CRITICAL**: Use running balance formulas referencing **Period Totals row** for adds/releases.

```python
# Column B: Beginning balance from totals
ws.cell(row=ending_row, column=2, value=f"=B{totals_row}")

# Column E: First period Ending = Beginning + Adds - Release
ws.cell(row=ending_row, column=5, value=f"=B{ending_row}+C{totals_row}-D{totals_row}")

# Column H: Second period Ending = Previous Ending + Adds - Release
ws.cell(row=ending_row, column=8, value=f"=E{ending_row}+F{totals_row}-G{totals_row}")

# Column K: Third period Ending
ws.cell(row=ending_row, column=11, value=f"=H{ending_row}+I{totals_row}-J{totals_row}")

# Column N: Fourth period Ending
ws.cell(row=ending_row, column=14, value=f"=K{ending_row}+L{totals_row}-M{totals_row}")

# Column O: Total releases/amortization — MUST REFERENCE TOTALS ROW
ws.cell(row=ending_row, column=15, value=f"=D{totals_row}+G{totals_row}+J{totals_row}+M{totals_row}")
```

#### GL Balance Row

- Columns E, H, K, N: Hard-coded values from JSON
- Column O: `=O{totals_row}-O{ending_row}` (total adds minus total releases)

#### Variance Row

- Column O: `=O{gl_row}-N{gl_row}` (GL Balance column O minus GL Balance column N)

### 6. Build Summary Sheet

Link to **column O** of control rows:
```python
ws_summary.cell(row=7, column=2, value=f"='Sheet Name'!O{totals_row}")  # Period Totals
ws_summary.cell(row=8, column=2, value=f"='Sheet Name'!O{ending_row}")  # Ending Balance
ws_summary.cell(row=9, column=2, value=f"='Sheet Name'!O{gl_row}")  # GL Balance
```

Quote sheet names containing spaces or special characters (#).

---

## Anti-Patterns

| Issue | Wrong | Right |
|-------|-------|-------|
| Pattern confusion | `=SUM(E6:E8)` for Ending Balance on running-balance data | Running balance: `=B{r}+C{totals}-D{totals}` |
| Ending Balance adds/releases | `=B{r}+C{r}-D{r}` (own row) | `=B{r}+C{totals}-D{totals}` (Period Totals) |
| **Ending Balance column O** | `=D{ending}+G{ending}+J{ending}+M{ending}` | `=D{totals}+G{totals}+J{totals}+M{totals}` |
| Summary links | Link to column N (final period ending) | Link to column O (total adds/releases) |
| Patch override | Replace entire row | Apply only non-empty fields |
| Status filtering | Include all rows | Filter to status=open OR approved=true+row_kind=detail |
| GL column O | Hard-coded value | Formula: `=O{totals}-O{ending}` |
| Variance formula | `=N{gl}-N{ending}` | `=O{gl}-N{gl}` |
| Inserted rows missing status | `new_row = {...}` | `new_row['status'] = 'open'` |
| CSV field alignment | Manual comma counting | Use `csv.DictReader` and print parsed result |
| Template stale data | Overwrite without clearing | Clear row 6+ before writing |
| Version dedup | Use all versions | Keep highest version per case_id/contract_key |
| SUM formula range | `=SUM(B6:8)` (missing col letter) | `=SUM(B6:B8)` (column letter on both sides) |

---

## Output Precision

Never round, truncate, or fixed-format numeric values. Pass raw float values directly:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float

---

## Scripts

- `scripts/verify_workbook.py` — Validates workbook structure, detects wrong-row references in Ending Balance formulas, checks summary links point to column O. **RUN THIS BEFORE CLAIMING COMPLETION.**

---

## Verification

**MANDATORY**: Run `scripts/verify_workbook.py` after generation. Do not claim success until it passes.

```bash
python3 rebate-rollforward/scripts/verify_workbook.py /path/to/workbook.xlsx
```

The script checks:
- Ending Balance column O references Period Totals row (NOT its own row)
- Running balance formulas (E, H, K, N) reference Period Totals for adds/releases
- Summary links point to column O
- No circular references
- Cross-sheet reference syntax

---

## Validation Checklist

1. Data filtered correctly (status=open OR approved=true+row_kind=detail OR active_flag=true+record_type=detail)
2. Version dedup applied (keep highest version per case_id/contract_key) if applicable
3. Patches applied: overrides update non-empty fields only, inserts get correct status
4. Template cleared from row 6 downward if working from template
5. Line items sorted by customer/partner/vendor name, then row_id/case_id/contract_key
6. Period Totals: SUM for B-N (with column letter on both sides), adds formula for O
7. **Ending Balance: Running balance chain (B→E→H→K→N), adds/releases from Period Totals row, O = total releases from Period Totals row**
8. GL Balance: Hard-coded values in E/H/K/N, O = totals O - ending O
9. Variance: O = GL O - GL N
10. Summary: Links to column O of control rows
11. Cross-sheet references use single quotes for sheet names with spaces or #
12. **Verify script exits with code 0** — do not claim success until it passes
