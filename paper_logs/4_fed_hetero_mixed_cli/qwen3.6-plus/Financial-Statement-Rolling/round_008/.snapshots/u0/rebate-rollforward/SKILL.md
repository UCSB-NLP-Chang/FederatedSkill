---
name: rebate-rollforward
description: Build rebate, market development fund (MDF), refund reserve, and contract liability rollforward workbooks with running balance formulas. Use when tracking rebate accruals, channel incentives, MDF reserves, refund reserves, or contract liabilities with adds/releases (or accrued/credited/billings/revenue) per period. Distinct from standard rollforwards: uses running balance formulas for Ending Balance row (E=B+C-D, H=E+F-G), CSV patches with override/insert actions, and summary links to column O (total adds/releases). Supports flat CSV/JSON sources, nested JSON snapshots with version deduplication, and contract liability exports with bucket routing.
---

# Rebate / Refund Reserve / Contract Liability Rollforward Workbook Builder

## STOP: CHOOSE THE RIGHT PATTERN

**Before starting, check which rollforward pattern your data requires:**

| Criterion | Financial Rollforward (SUM Pattern) | Rebate/Contract/Refund (Running Balance Pattern) |
|-----------|-------------------------------------|--------------------------------------------------|
| Data row content | Pre-calculated ending balances per period | Adds/releases (or booked/earned) per period only |
| Ending Balance control row | `=SUM(E6:E8)` — sums data row endings | `=B{r}+C{totals}-D{totals}` — computes chain |
| Revision handling | Usually none | Deduplicate by key, keep highest revision |

**Decision Rule:**
```python
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
- Contract liability schedules with booked/revenue tracking
- Any rollforward with adds/releases per period where Ending Balance uses running balance chain
- CSV patches that override specific fields or insert new rows
- Source data filtered by status field (e.g., status=open, active_flag=true) or approval flags (approved=true, row_kind=detail, record_type=detail)

## Key Differences from Other Rollforward Skills

| Aspect | Financial Rollforward | Project Cost Rollforward | Rebate / Refund / Contract |
|--------|----------------------|--------------------------|-----------------------------|
| Ending Balance row | SUM of data rows | Running balance chain | Running balance chain |
| Summary links | Column N | Column O | Column O |
| Patch format | Not typical | Override by row_id | Override + Insert actions |
| GL Balance column O | Hard-coded | Formula: totals O - ending O | Formula: totals O - ending O |
| Variance formula | GL - Calculated Ending | O(GL) - N(GL) | O(GL) - N(GL) |

## Data Source Variants

### Variant A: Flat CSV/JSON with status filtering

Filter to `status=="open"` or `active_flag==true`. See workflow below.

### Variant B: Nested JSON Snapshot with version dedup (Refund Reserve pattern)

Source JSON has structure: `segments[] → snapshots[]`. Each snapshot has:
- `case_id`, `version` (int), `approved` (bool), `row_kind` (string)
- `customer_name`, `opening_amount`, `flow_months`, `term_hint`, `memo_text`, `account_code`
- `flow_months`: `{aug, sep, oct, nov}` each with `{accrued, credited}`

**Filter**: Keep only items where `approved == true` AND `row_kind == "detail"`.

**Deduplicate**: Group by `case_id`, keep the item with the highest `version` number.

```python
from collections import defaultdict

# Flatten and filter
all_items = []
for segment in data['segments']:
    for snap in segment['snapshots']:
        if snap.get('approved') and snap.get('row_kind') == 'detail':
            all_items.append(snap)

# Deduplicate by case_id, keep highest version
by_case = defaultdict(list)
for item in all_items:
    by_case[item['case_id']].append(item)

deduped = []
for case_id, items in by_case.items():
    deduped.append(max(items, key=lambda x: x['version']))
```

**Field mapping to workbook columns**:
- `accrued` → adds column
- `credited` → release column
- `term_hint` → term_months (column O)
- `memo_text` → comments/notes (column P)
- `account_code` → reserve account (column Q)

### Variant C: Contract Liability with bucket routing

Source JSON has structure: `exports[] → clusters[] → records[]`. Each record has:
- `contract_key`, `revision_no`, `active_flag` (bool), `record_type` (string)
- `party_name`, `opening_amount`, `contract_months`, `notes`, `liability_account`
- `month_roll`: `{sep, oct, nov, dec}` each with `{booked, earned}`

**Filter**: Keep only items where `active_flag == true` AND `record_type == "detail"`.

**Deduplicate**: Group by `contract_key`, keep the item with the highest `revision_no`.

**Bucket routing**: Use aliases CSV to map `source_bucket` to sheet name:
```python
bucket_to_sheet = {row["source_bucket"]: row for row in aliases}
```

**Field mapping to workbook columns**:
- `booked` → billings/adds column
- `earned` → revenue/release column
- `contract_months` → term_months (column O)
- `notes` → comments (column P)
- `liability_account` → account number (column Q)

## Workflow

### 1. Load and Filter Source Data

**CRITICAL: Apply the correct filter for your data source.**

- Variant A: Filter to `status=="open"` or `active_flag==true`
- Variant B: Filter to `approved==true` AND `row_kind=="detail"`
- Variant C: Filter to `active_flag==true` AND `record_type=="detail"`

```python
import json
import csv

# Load base schedule (CSV or JSON)
rows = {}
with open('schedule_base.csv') as f:
    for row in csv.DictReader(f):
        if row.get('status') == 'open' or row.get('active_flag') == 'true':
            rows[row['row_key']] = dict(row)
```

### 2. Apply CSV Patches

Patch file columns: `action, target_bucket, row_id, customer_name, beginning_balance, aug_adds, aug_release, sep_adds, sep_release, oct_adds, oct_release, nov_adds, nov_release, term_months, comments, account_number`

**CRITICAL: Never manually count commas. Always use Python's csv.DictReader:**

```python
import csv
with open('adjustments.csv', newline='') as f:
    reader = csv.DictReader(f)
    print('Fieldnames:', reader.fieldnames)
    for row in reader:
        for k, v in row.items():
            print(f'  {k!r}: {v!r}')
```

**Override action**: Match by row_id (or case_id/contract_key), apply only non-empty fields:
```python
for p in patches:
    if p['target_bucket'] != target_bucket:
        continue
    if p['action'] == 'override':
        rk = p['row_id']
        if rk in rows:
            for key, value in p.items():
                if key in ('action', 'target_bucket', 'row_id'):
                    continue
                if value and value.strip():
                    rows[rk][key] = value.strip()
```

**Insert action**: Add new row. **CRITICAL: Set status/approval flag**:
```python
for p in patches:
    if p['target_bucket'] != target_bucket:
        continue
    if p['action'] == 'insert':
        new_row = {k: v.strip() if v else v for k, v in p.items()
                   if k not in ('action', 'target_bucket')}
        new_row['status'] = 'open'  # INSERTED ROWS GET FILTERED OUT WITHOUT THIS
        rows[p['row_id']] = new_row
```

### 3. Clear Template Content

If working from a template workbook, **clear any old template content from row 6 downward** before writing:
```python
for r in range(6, ws.max_row + 1):
    for c in range(1, ws.max_column + 1):
        ws.cell(row=r, column=c).value = None
```

### 4. Sort and Write Data Rows

Sort by customer/partner name, then by row_id/case_id/contract_key:
```python
sorted_rows = sorted(rows.values(), key=lambda r: (r.get('customer_name', ''), r.get('row_id', '')))
```

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

The column letter must appear on BOTH sides of the range:

```python
# WRONG: Missing column letter after colon → produces =SUM(B6:8)
formula = f"=SUM({col_letter}{start}:{end})"

# RIGHT: Column letter on both sides → produces =SUM(B6:B8)
formula = f"=SUM({col_letter}{start}:{col_letter}{end})"
```

#### Ending Balance Row — RUNNING BALANCE CHAIN

**CRITICAL**: Use running balance formulas, NOT SUM of data rows.

```python
# Column B: Beginning balance from totals
ws.cell(row=ending_row, column=2, value=f"=B{totals_row}")

# Column E: Aug/Jul Ending = Beginning + Adds - Release
ws.cell(row=ending_row, column=5, value=f"=B{ending_row}+C{totals_row}-D{totals_row}")

# Column H: Sep/Aug Ending = Previous Ending + Adds - Release
ws.cell(row=ending_row, column=8, value=f"=E{ending_row}+F{totals_row}-G{totals_row}")

# Column K: Oct/Sep Ending = Previous Ending + Adds - Release
ws.cell(row=ending_row, column=11, value=f"=H{ending_row}+I{totals_row}-J{totals_row}")

# Column N: Nov/Oct Ending = Previous Ending + Adds - Release
ws.cell(row=ending_row, column=14, value=f"=K{ending_row}+L{totals_row}-M{totals_row}")

# Column O: Total releases
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
# Enterprise section
ws_summary.cell(row=7, column=2, value=f"='Enterprise Refunds #2215'!O{totals_row}")  # Period Totals
ws_summary.cell(row=8, column=2, value=f"='Enterprise Refunds #2215'!O{ending_row}")  # Ending Balance
ws_summary.cell(row=9, column=2, value=f"='Enterprise Refunds #2215'!O{gl_row}")  # GL Balance

# Total GL Balance
ws_summary.cell(row=16, column=2, value="=B9+B14")
```

Quote sheet names containing spaces or special characters (#).

## CRITICAL: Ending Balance Formula Verification

**The #1 bug in rollforward workbooks is referencing the wrong row for adds/releases.**

Before claiming completion, verify each Ending Balance formula:

| Column | WRONG (references empty cells) | RIGHT (references Period Totals) |
|--------|-------------------------------|----------------------------------|
| E | `=B{ending}+C{ending}-D{ending}` | `=B{ending}+C{totals}-D{totals}` |
| H | `=E{ending}+F{ending}-G{ending}` | `=E{ending}+F{totals}-G{totals}` |
| K | `=H{ending}+I{ending}-J{ending}` | `=H{ending}+I{totals}-J{totals}` |
| N | `=K{ending}+L{ending}-M{ending}` | `=K{ending}+L{totals}-M{totals}` |

**Verification script**:
```python
import openpyxl
wb = openpyxl.load_workbook('workbook.xlsx')
for sheet_name in wb.sheetnames[1:]:  # Skip summary
    ws = wb[sheet_name]
    for row in range(1, ws.max_row + 1):
        if ws.cell(row=row, column=1).value == 'Ending Balance':
            e_formula = str(ws.cell(row=row, column=5).value)
            if f'C{row}' in e_formula or f'D{row}' in e_formula:
                print(f"ERROR: {sheet_name} Ending Balance row {row} refs own row")
```

## Anti-Patterns

| Issue | Wrong | Right |
|-------|-------|-------|
| Ending Balance adds/releases | `=B{r}+C{r}-D{r}` (own row) | `=B{r}+C{totals}-D{totals}` (Period Totals) |
| Ending Balance formulas | `=SUM(E6:E8)` | Running balance: `=B{r}+C{totals}-D{totals}` |
| Summary links | Link to column N | Link to column O (total adds/releases) |
| Patch override | Replace entire row | Apply only non-empty fields |
| Status filtering | Include all rows | Filter to status=open OR active_flag=true OR approved=true+row_kind=detail OR record_type=detail+active_flag=true |
| GL column O | Hard-coded value | Formula: `=O{totals}-O{ending}` |
| Variance formula | `=N{gl}-N{ending}` | `=O{gl}-N{gl}` |
| Inserted rows missing status | `new_row = {...}` | `new_row['status'] = 'open'` |
| CSV field alignment | Manual comma counting | Use `csv.DictReader` and print parsed result |
| Template stale data | Overwrite without clearing | Clear row 6+ before writing |
| Version dedup | Use all versions | Keep highest version per case_id/contract_key |
| SUM formula range | `=SUM(B6:8)` (missing col letter) | `=SUM(B6:B8)` (column letter on both sides) |
| Skipping verification | Claiming success without verify | Run verify_workbook.py first |

## Output Precision

Never round, truncate, or fixed-format numeric values. Pass raw float values directly:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision.

## Known Invariants (by sub-task)

### rebate-rollforward

- Filter to `status == "open"` only — exclude superseded/archived rows
- Patch CSV with `action` column: `override` (match by row_key, patch non-empty fields) or `insert` (add new row)
- **Inserted rows MUST have `status="open"`** — they lack a status field from the patch and will be filtered out otherwise
- Ending Balance row uses running balance chain (E=B+C-D, H=E+F-G, K=H+I-J, N=K+L-M)
- Summary links to column O (total adds/releases), NOT column N (final period ending)
- GL Balance column O is a formula: `=O{totals}-O{ending}`
- Variance column O: `=O{gl}-N{gl}`
- Cross-sheet references use single quotes for sheet names with spaces or #

### mdf-accrual-rollforward

- Same invariants as rebate-rollforward
- Source data may be JSON or CSV with same filtering rules
- Partner name is primary sort field

### refund-reserve-rollforward

- Filter to `approved == true` AND `row_kind == "detail"` — exclude unapproved and summary rows
- Deduplicate by `case_id`, keeping highest `version` number
- Field mapping: `accrued`→adds, `credited`→release, `term_hint`→term_months, `memo_text`→comments
- Clear template content from row 6 downward before writing
- Ending Balance row uses running balance chain
- Summary links to column O (total adds/releases), NOT column N
- GL Balance column O is a formula: `=O{totals}-O{ending}`
- Variance column O: `=O{gl}-N{gl}`

### contract-liability-rollforward

- Filter to `active_flag == true` AND `record_type == "detail"` — exclude summary rows and inactive records
- Deduplicate by `contract_key`, keeping highest `revision_no`
- Field mapping: `booked`→adds/billings, `earned`→release/revenue, `contract_months`→term_months, `notes`→comments
- Use aliases CSV for bucket→sheet routing
- Clear template content from row 6 downward before writing
- Ending Balance row uses running balance chain
- Summary links to column O (total adds/releases), NOT column N
- GL Balance column O is a formula: `=O{totals}-O{ending}`
- Variance column O: `=O{gl}-N{gl}`

## Verification

**MANDATORY**: Run `scripts/verify_workbook.py` before claiming success:

```bash
python3 financial-rollforward-workbook/scripts/verify_workbook.py /path/to/workbook.xlsx
```

The script checks:
- Sheet existence and order
- Headers at row 5
- Control row labels
- Circular reference detection (formula referencing its own row)
- Cross-sheet reference syntax
- Formula syntax (`=` prefix)

**Do NOT claim task success until the verify script exits with code 0.**

## Validation Checklist

1. Data filtered correctly (status=open OR active_flag=true OR approved=true+row_kind=detail OR record_type=detail+active_flag=true)
2. Version dedup applied (keep highest version per case_id/contract_key) if applicable
3. Patches applied: overrides update non-empty fields only, inserts get correct status
4. Template cleared from row 6 downward if working from template
5. Line items sorted by customer/partner name, then row_id/case_id/contract_key
6. Period Totals: SUM for B-N (column letter on both sides of range), adds formula for O
7. Ending Balance: Running balance chain (B→E→H→K→N), adds/releases from Period Totals row, O = total releases
8. GL Balance: Hard-coded values in E/H/K/N, O = totals O - ending O
9. Variance: O = GL O - GL N
10. Summary: Links to column O of control rows
11. Cross-sheet references use single quotes for sheet names with spaces or #
12. **Verify script exits with code 0**
