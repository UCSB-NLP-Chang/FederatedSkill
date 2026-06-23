---
name: rebate-rollforward
description: Build rebate and market development fund (MDF) rollforward workbooks with running balance formulas. Use when tracking rebate accruals, channel incentives, or MDF reserves with adds/releases per period. Distinct from standard rollforwards: uses running balance formulas for Ending Balance row (E=B+C-D, H=E+F-G), CSV patches with override/insert actions, and summary links to column O (total adds/releases).
---

# Rebate Rollforward Workbook Builder

## When to Use

- Rebate reserve schedules (Channel Rebates, MDF Accruals)
- Marketing development fund rollforwards
- Any rollforward with adds/releases per period where Ending Balance uses running balance chain
- CSV patches that override specific fields or insert new rows
- Source data filtered by status field (e.g., status=open)

## Key Differences from Other Rollforward Skills

| Aspect | Financial Rollforward | Project Cost Rollforward | Rebate Rollforward |
|--------|----------------------|--------------------------|-------------------|
| Ending Balance row | SUM of data rows | Running balance chain | Running balance chain |
| Summary links | Final period column (N) | Column O | Column O |
| Patch format | Not typical | Override by row_id | Override + Insert actions |
| GL Balance column O | Hard-coded | Formula: totals O - ending O | Formula: totals O - ending O |
| Variance formula | GL - Calculated Ending | O(GL) - N(GL) | O(GL) - N(GL) |

## Workflow

### 1. Load and Filter Source Data

```python
import json
import csv

# Load base schedule
with open('schedule_base.json') as f:
    data = json.load(f)

# Filter to active rows
rows = [r for r in data['rows'] if r.get('status') == 'open']
```

### 2. Apply CSV Patches

Patch file format:
```
action,target_sheet,row_key,partner,beginning_balance,jul_adds,jul_release,jul_ending_balance,...,comments,account_number
override,Channel Rebates #6120,CR-09,,,,,,,,,4000,,5500,,,4000,,Quarterly true-up,
insert,MDF Accrual #6125,MDF-07,Echo Events,0,0,0,0,8000,2000,6000,0,2000,4000,0,2000,2000,4,October summit,6125
```

**Override action**: Match by row_key, apply only non-empty fields:
```python
for patch in patches:
    if patch['action'] == 'override':
        for row in rows:
            if row['row_key'] == patch['row_key']:
                for key, value in patch.items():
                    if value not in (None, '', ' '):
                        row[key] = value
```

**Insert action**: Add new row to target sheet:
```python
for patch in patches:
    if patch['action'] == 'insert':
        new_row = {k: v for k, v in patch.items() if k not in ['action', 'target_sheet']}
        rows.append(new_row)
```

### 3. Sort and Write Data Rows

Sort by partner name (or primary sort field), then by row_key:
```python
rows.sort(key=lambda r: (r['partner'], r['row_key']))
```

Write data rows starting at row 6. Apply `#,##0.00` format to monetary columns.

### 4. Build Control Rows

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

#### Ending Balance Row — RUNNING BALANCE CHAIN

**CRITICAL**: Use running balance formulas, NOT SUM of data rows.

```python
# Column B: Beginning balance from totals
ws.cell(row=ending_row, column=2, value=f"=B{totals_row}")

# Column E: Jul Ending = Beginning + Jul Adds - Jul Release
ws.cell(row=ending_row, column=5, value=f"=B{ending_row}+C{totals_row}-D{totals_row}")

# Column H: Aug Ending = Jul Ending + Aug Adds - Aug Release
ws.cell(row=ending_row, column=8, value=f"=E{ending_row}+F{totals_row}-G{totals_row}")

# Column K: Sep Ending = Aug Ending + Sep Adds - Sep Release
ws.cell(row=ending_row, column=11, value=f"=H{ending_row}+I{totals_row}-J{totals_row}")

# Column N: Oct Ending = Sep Ending + Oct Adds - Oct Release
ws.cell(row=ending_row, column=14, value=f"=K{ending_row}+L{totals_row}-M{totals_row}")

# Column O: Total releases
ws.cell(row=ending_row, column=15, value=f"=D{totals_row}+G{totals_row}+J{totals_row}+M{totals_row}")
```

**Note**: These formulas reference the Ending Balance row's own cells (B, E, H, K) for the running balance chain. This is correct and NOT a circular reference because each formula references a different column.

#### GL Balance Row
- Columns E, H, K, N: Hard-coded values from JSON
- Column O: `=O{totals_row}-O{ending_row}` (total adds minus total releases)

#### Variance Row
- Column O: `=O{gl_row}-N{gl_row}` (GL Balance column O minus GL Balance column N)

### 5. Build Summary Sheet

Link to **column O** of control rows:
```python
# Channel Rebates section
ws_summary.cell(row=7, column=2, value=f"='Channel Rebates #6120'!O{totals_row}")  # Period Totals
ws_summary.cell(row=8, column=2, value=f"='Channel Rebates #6120'!O{ending_row}")  # Ending Balance
ws_summary.cell(row=9, column=2, value=f"='Channel Rebates #6120'!O{gl_row}")  # GL Balance

# Total GL Balance
ws_summary.cell(row=16, column=2, value="=B9+B14")
```

Quote sheet names containing spaces or special characters (#).

## Anti-Patterns

| Issue | Wrong | Right |
|-------|-------|-------|
| Ending Balance formulas | `=SUM(E6:E8)` | Running balance: `=B{r}+C{totals}-D{totals}` |
| Summary links | Link to column N (Oct Ending) | Link to column O (total adds/releases) |
| Patch override | Replace entire row | Apply only non-empty fields |
| Status filtering | Include all rows | Filter to status=open |
| GL column O | Hard-coded value | Formula: `=O{totals}-O{ending}` |
| Variance formula | `=N{gl}-N{ending}` | `=O{gl}-N{gl}` |

## Template Handling

If starting from a template file:
- Remove stale placeholder rows (marked with "STALE ROW - REMOVE", "TEMPLATE PLACEHOLDER")
- Preserve sheet structure and order
- Replace all template content with actual data
- Do not leave template text in final output

## Output Precision

Never round, truncate, or fixed-format numeric values. Pass raw float values directly:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`
- DO: `ws.cell(row=r, column=c, value=x)` with x as raw float

## Validation Checklist

1. Data filtered to status=open
2. Patches applied: overrides update non-empty fields only, inserts add new rows
3. Line items sorted by partner name, then row_key
4. Period Totals: SUM for B-N, adds formula for O
5. Ending Balance: Running balance chain (B→E→H→K→N), O = total releases
6. GL Balance: Hard-coded values in E/H/K/N, O = totals O - ending O
7. Variance: O = GL O - GL N
8. Summary: Links to column O of control rows
9. Cross-sheet references use single quotes for sheet names with spaces or #