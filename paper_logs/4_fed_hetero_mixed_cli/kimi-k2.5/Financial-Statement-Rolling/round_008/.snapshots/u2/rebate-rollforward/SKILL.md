---
name: rebate-rollforward
description: Build rebate, market development fund (MDF), refund reserve, and contract liability rollforward workbooks with running balance formulas. Use when source data tracks adds/releases (or booked/earned, accrued/credited) per period and Ending Balance must be computed via running balance chain (E=B+C-D, H=E+F-G). Critical distinction from financial rollforwards: data rows contain adds/releases only, NOT pre-calculated ending balances. Use for nested JSON with revision tracking, CSV patches with override/insert actions, record type filtering (detail vs summary), and bucket routing via aliases.
---

# Rebate / Refund Reserve / Contract Liability Rollforward

## STOP: CHOOSE THE RIGHT ROLLOWORDER PATTERN

**The #1 failure mode is applying the wrong formula pattern. Two mutually exclusive patterns exist:**

| Criterion | Financial Rollforward (SUM Pattern) | Rebate/Contract Liability (Running Balance Pattern) |
|-----------|-------------------------------------|-----------------------------------------------------|
| **Data row content** | Pre-calculated ending balances per period | Adds/releases (or booked/earned) per period only |
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

**Wrong Pattern Consequences:**
- Using SUM on data rows that lack ending balances → zeros or errors
- Using running balance on data with pre-calculated ending balances → double counting

---

## When to Use

- **Rebate reserve schedules** (Channel Rebates, Partner Rebates)
- **Marketing development fund (MDF) accruals**
- **Refund reserve schedules** with accrued/credited tracking
- **Contract liability rollforwards** (booked/earned tracking for subscriptions/services)
- Any rollforward where:
  - Data rows track period activity (adds/releases) not resulting balances
  - Running balance must chain across periods (Jul ending = Aug beginning)
  - Source data has nested structure with revision numbers
  - CSV patches override specific fields or insert rows
  - Records filtered by `record_type`, `approved` flag, or `active` status

---

## Data Source Variants

### Variant A: Flat CSV/JSON with status filtering

Filter to `status=="open"` or `active_flag==true`.

### Variant B: Nested JSON Snapshot with version dedup (Refund Reserve pattern)

Source JSON: `segments[] → snapshots[]`. Each snapshot has:
- `case_id`, `version` (int), `approved` (bool), `row_kind` (string)
- `customer_name`, `opening_amount`, `flow_months`, `term_hint`, `memo_text`, `account_code`
- `flow_months`: `{aug, sep, oct, nov}` each with `{accrued, credited}`

**Filter**: `approved == true` AND `row_kind == "detail"`
**Deduplicate**: Group by `case_id`, keep highest `version`

### Variant C: Contract Liability with bucket routing

Source JSON: `exports[] → clusters[] → records[]`. Each record has:
- `contract_key`, `revision_no`, `active_flag` (bool), `record_type` (string)
- `party_name`, `opening_amount`, `contract_months`, `notes`, `liability_account`
- `month_roll`: `{sep, oct, nov, dec}` each with `{booked, earned}`

**Filter**: `active_flag == true` AND `record_type == "detail"`
**Deduplicate**: Group by `contract_key`, keep highest `revision_no`
**Bucket routing**: Use aliases CSV to map `source_bucket` to sheet name

---

## Data Processing Workflow

### 1. Load and Flatten Nested JSON

```python
from collections import defaultdict
import json, csv

# Load source data
with open('source_data.json') as f:
    data = json.load(f)

# Flatten nested structure
all_items = []
for segment in data['segments']:
    for snap in segment['snapshots']:
        if snap.get('approved') and snap.get('row_kind') == 'detail':
            all_items.append(snap)

# Deduplicate by key, keep highest revision
by_key = defaultdict(list)
for item in all_items:
    by_key[item['case_id']].append(item)

deduped = [max(group, key=lambda x: x['version']) for group in by_key.values()]
```

### 2. Route to Sheets via Bucket Aliases

If using aliases CSV for bucket routing:
```python
bucket_to_sheet = {}
with open('bucket_aliases.csv') as f:
    for row in csv.DictReader(f):
        bucket_to_sheet[row['source_bucket']] = row['sheet_name']
```

### 3. Apply CSV Patches

**Patch file format**: `action, source_bucket, contract_key, field1, field2,...`

**Override action**: Match by key, apply only non-empty fields:
```python
for patch in patches:
    if patch['action'] == 'override':
        item = find_by_key(patch['contract_key'])
        for field, value in patch.items():
            if field not in ('action', 'source_bucket', 'contract_key') and value:
                item[field] = value.strip()
```

**Insert action — CRITICAL: Set status flag**:
```python
if patch['action'] == 'insert':
    new_row = {k: v for k, v in patch.items() if k not in ('action', 'source_bucket')}
    new_row['status'] = 'open'        # REQUIRED: inserted rows lack status
    new_row['record_type'] = 'detail' # REQUIRED: ensure type flag set
    items.append(new_row)
```

### 4. Clear Template Before Writing

```python
for r in range(6, ws.max_row + 1):
    for c in range(1, ws.max_column + 1):
        ws.cell(row=r, column=c).value = None
```

### 5. Sort Before Writing

```python
sorted_items = sorted(items, key=lambda x: (x.get('party_name', ''), x.get('contract_key', '')))
```

---

## Control Row Formulas

Compute positions dynamically:
```python
totals_row = start_row + len(data_rows)  # Row N+1
ending_row = totals_row + 1               # Row N+2
variance_row = ending_row + 1             # Row N+3
gl_row = variance_row + 1                 # Row N+4
```

### Period Totals Row

- Columns B-N: `=SUM(B{start}:B{end})` — **column letter on BOTH sides**
- Column O: `=C{totals_row}+F{totals_row}+I{totals_row}+L{totals_row}` (total adds)

**CRITICAL: SUM formula construction in openpyxl**

The column letter must appear on BOTH sides of the range:

```python
# WRONG: Missing column letter after colon → =SUM(B6:8) (Excel rejects this)
formula = f"=SUM({col_letter}{start}:{end})"

# RIGHT: Column letter on both sides → =SUM(B6:B8)
formula = f"=SUM({col_letter}{start}:{col_letter}{end})"
```

### Ending Balance Row — RUNNING BALANCE CHAIN

**CRITICAL: NOT `=SUM(E6:E8)` — that pattern is for financial rollforwards only**

**The #2 bug is referencing the wrong row for adds/releases. Always use Period Totals row:**

| Column | WRONG (references empty cells in Ending row) | RIGHT (references Period Totals row) |
|--------|---------------------------------------------|--------------------------------------|
| E | `=B{ending}+C{ending}-D{ending}` | `=B{ending}+C{totals}-D{totals}` |
| H | `=E{ending}+F{ending}-G{ending}` | `=E{ending}+F{totals}-G{totals}` |
| K | `=H{ending}+I{ending}-J{ending}` | `=H{ending}+I{totals}-J{totals}` |
| N | `=K{ending}+L{ending}-M{ending}` | `=K{ending}+L{totals}-M{totals}` |

```python
# Column B: Beginning balance total
ws.cell(row=ending_row, column=2, value=f"=B{totals_row}")

# P1 Ending (E): Beginning + P1 Adds - P1 Releases (from Period Totals!)
ws.cell(row=ending_row, column=5, value=f"=B{ending_row}+C{totals_row}-D{totals_row}")

# P2 Ending (H): P1 Ending + P2 Adds - P2 Releases
ws.cell(row=ending_row, column=8, value=f"=E{ending_row}+F{totals_row}-G{totals_row}")

# P3 Ending (K): P2 Ending + P3 Adds - P3 Releases
ws.cell(row=ending_row, column=11, value=f"=H{ending_row}+I{totals_row}-J{totals_row}")

# P4 Ending (N): P3 Ending + P4 Adds - P4 Releases
ws.cell(row=ending_row, column=14, value=f"=K{ending_row}+L{totals_row}-M{totals_row}")

# Column O: Total releases
ws.cell(row=ending_row, column=15, value=f"=D{totals_row}+G{totals_row}+J{totals_row}+M{totals_row}")
```

**Note:** These formulas reference Ending Balance row's cells (B, E, H, K) for the chain — NOT circular. But adds/releases MUST come from Period Totals row.

### Variance Row

```python
ws.cell(row=variance_row, column=15, value=f"=O{gl_row}-N{gl_row}")
```

### GL Balance Row

```python
# Per-period GL values (hard-coded from JSON)
ws.cell(row=gl_row, column=5, value=gl_data['sep'])
ws.cell(row=gl_row, column=8, value=gl_data['oct'])
ws.cell(row=gl_row, column=11, value=gl_data['nov'])
ws.cell(row=gl_row, column=14, value=gl_data['dec'])

# Column O: Total adds - total releases
ws.cell(row=gl_row, column=15, value=f"=O{totals_row}-O{ending_row}")
```

---

## Summary Sheet

Link to **column O** of control rows:
```python
ws_summary.cell(row=7, column=2, value=f"='Subscriptions #2350'!O{totals_row}")  # Period Totals
ws_summary.cell(row=8, column=2, value=f"='Subscriptions #2350'!O{ending_row}")  # Ending Balance
ws_summary.cell(row=9, column=2, value=f"='Subscriptions #2350'!O{gl_row}")      # GL Balance

# Total GL Balance
ws_summary.cell(row=16, column=2, value="=B9+B14")
```

Always quote sheet names with spaces or special characters (`#`).

---

## Anti-Patterns

| Issue | Wrong | Right |
|-------|-------|-------|
| Pattern confusion | `=SUM(E6:E8)` for Ending Balance | Running balance: `=B{r}+C{totals}-D{totals}` |
| Ending Balance adds/releases | `=B{r}+C{r}-D{r}` (own row, empty!) | `=B{r}+C{totals}-D{totals}` (Period Totals) |
| SUM formula range | `=SUM(B6:8)` (missing col letter) | `=SUM(B6:B8)` (col letter on both sides) |
| Summary links | Link to column N (final ending) | Link to column O (total adds/releases) |
| Missing status on insert | `new_row = patch_data` | `new_row['status'] = 'open'` |
| CSV parsing | Manual comma counting | `csv.DictReader` with fieldname print |
| Template contamination | Overwrite without clearing | Clear rows 6+ before writing |
| No revision dedup | Use all versions | Keep max revision per key |
| Wrong filter | `if item['active']:` (truthy) | `if item.get('active') is True:` |

---

## Output Precision

Never round, truncate, or fixed-format numeric values. Pass raw float values directly:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision.

---

## Known Invariants (by sub-task)

### rebate-rollforward

- Filter to `status == "open"` — exclude superseded/archived rows
- Patch CSV with `action` column: `override` or `insert`
- **Inserted rows MUST have `status="open"`**
- Ending Balance: running balance chain, adds/releases from Period Totals
- Summary links to column O, NOT N
- GL Balance column O: `=O{totals}-O{ending}`
- Variance column O: `=O{gl}-N{gl}`

### mdf-accrual-rollforward

- Same as rebate-rollforward
- Partner name is primary sort field

### refund-reserve-rollforward

- Filter to `approved == true` AND `row_kind == "detail"`
- Deduplicate by `case_id`, highest `version`
- Field mapping: `accrued`→adds, `credited`→release, `term_hint`→term_months

### contract-liability-rollforward

- Filter to `active_flag == true` AND `record_type == "detail"`
- Deduplicate by `contract_key`, highest `revision_no`
- Field mapping: `booked`→adds/billings, `earned`→release/revenue
- Use aliases CSV for bucket→sheet routing

---

## Verification

**MANDATORY: Run verification before claiming success.**

```bash
python3 financial-rollforward-workbook/scripts/verify_workbook.py workbook.xlsx
```

**Also verify Ending Balance formulas manually:**
```python
import openpyxl
wb = openpyxl.load_workbook('workbook.xlsx')
for sheet_name in wb.sheetnames[1:]:
    ws = wb[sheet_name]
    for row in range(1, ws.max_row + 1):
        if ws.cell(row=row, column=1).value == 'Ending Balance':
            e_formula = str(ws.cell(row=row, column=5).value)
            if f'C{row}' in e_formula or f'D{row}' in e_formula:
                print(f"ERROR: {sheet_name} Ending Balance row {row} references own row for adds/releases")
```

**Run the task's official test suite** — do not rely solely on manual inspection.

---

## Validation Checklist

1. STOP block checked: running balance pattern confirmed (no `ending_balance` fields in data)
2. Data filtered: status=open OR approved=true+row_kind=detail OR active_flag=true+record_type=detail
3. Dedup applied: highest revision per key
4. Patches applied: overrides non-empty only, inserts have status set
5. Template cleared from row 6+
6. Sorted by party name, then contract key
7. Period Totals: SUM with column letter on both sides, O = total adds
8. Ending Balance: Running balance chain, adds/releases from Period Totals row
9. GL Balance: Hard-coded values, O = totals O - ending O
10. Variance: O = GL O - GL N
11. Summary: Links to column O
12. Sheet names quoted if contain spaces or `#`
13. Verify script exits with code 0
14. Official test suite passes