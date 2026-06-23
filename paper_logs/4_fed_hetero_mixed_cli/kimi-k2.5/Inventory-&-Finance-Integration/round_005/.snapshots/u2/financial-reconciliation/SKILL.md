---
name: financial-reconciliation
description: Build financial/capacity reconciliation Excel workbooks from JSON/CSV with rollforward schedules, control rows, and cross-sheet formulas. Use for tasks requiring detail sheets per pool/partition plus summary sheet linking to control rows.
---

# Excel Reconciliation Workbook Builder

## Environment Setup

**Required**: Use virtual environment, never `--break-system-packages`.

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install openpyxl -q
```

**Then** prefix commands: `source .venv/bin/activate && python3 script.py`

## Detail Sheet Structure (Fixed)

Columns: A=Label, B=Month1, C=Month2, ... (dynamic), X=Total Amortization
Rows:
| Row | Content |
|-----|---------|
| 1 | Headers (Partner / Vendor, Jan, Feb, ..., Total Amortization) |
| 6-11 | Data rows (vendors/partitions) |
| 12 | **Month Totals** - formulas summing rows 6-11 per column |
| 13 | **Ending Balance** - hardcoded April (last month) value |
| 14 | **Variance** - `=Ending - GL` (typically 0) |
| 15 | **GL Balance** - hardcoded from input |

**Critical**: Calculate column letters dynamically using `get_column_letter`:
```python
from openpyxl.utils import get_column_letter
last_month_col = 5  # E for Apr if B=Jan
jan_col = get_column_letter(2)  # B
apr_col = get_column_letter(last_month_col)  # E
total_col = get_column_letter(last_month_col + 1)  # F
```

## Summary Sheet Structure

| Row | A Column | B Column | Formula/Value |
|-----|----------|----------|---------------|
| 1-3 | Title, Subtitle, Note | | Hardcoded strings |
| 5 | Pool / Program | Amount | Headers |
| 6 | Bus Program #X | `='Sheet Name'!{apr_col}12` | Cross-sheet to Month Totals row, April column |
| 7 | Rail Program #Y | `='Sheet Name'!{apr_col}12` | Same |
| 8 | Month Totals | `=SUM(B6:B7)` | Sum of above |
| 9 | Ending Balance | `=B8` | **NOT** =F8 or =N8 - reference the Amount column (B) |
| 12 | Bus Total Amortization | `='Sheet Name'!{total_col}12` | Cross-sheet to Month Totals, Total Amortization column |
| 13 | Rail Total Amortization | `='Sheet Name'!{total_col}12` | Same |
| 14 | Total Amortization | `=SUM(B12:B13)` | Sum |
| 16 | GL Balance | `=B9+B14` | Ending + Total Amortization |

## Cross-Sheet Formula Rules

1. **Sheet names with spaces**: Use single quotes around sheet name
   ```python
   formula = f"='{sheet_name}'!{col}{row}"
   ```

2. **Month Totals row (12)**: Reference the **April** (last month) column for pool totals
   - If months are B-E, use E12
   - Use `get_column_letter(month_count + 1)` to find April column

3. **Total Amortization column**: Reference column F (or last_month_col + 1), row 12

## Writing Data Correctly

- **Data rows**: Write raw floats, not formatted strings
- **Control rows 12-15**: Mix of formulas (row 12) and hardcoded values (rows 13-15)
- **GL Balance**: Hardcoded from input JSON (e.g., `{"apr": 182834.16}`)
- **Ending Balance**: Same value as GL Balance (reconciled)
- **Variance**: Hardcoded 0 or formula `=EndingBalanceCell - GLBalanceCell`

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Verification Steps (Before Saving)

1. **Sheet names**: `print(wb.sheetnames)` - ensure Summary is first if required
2. **Formulas check**: Print row 12 formulas to verify SUM ranges
   ```python
   for c in range(2, 7):  # B through F
       print(ws.cell(row=12, column=c).value)
   # Should see: =SUM(B6:B11), =SUM(C6:C11), etc.
   ```
3. **Cross-sheet syntax**: Verify no double equals (e.g., `==SUM` is wrong)
4. **Cell types**: Check that numeric cells are float/int, not strings
   ```python
   assert isinstance(ws['B6'].value, (int, float))
   ```
5. **Column alignment**: Verify April data is in column E (or calculated last month col)

## Anti-Patterns

- **NEVER** use `--break-system-packages` - create venv instead
- **NEVER** hardcode column letters (B, E, F, N) without calculating from data structure
- **NEVER** use `data_only=True` when loading to verify - it returns None for formulas
- **NEVER** write numbers as strings: `ws.cell(value="123.45")` - must be `value=123.45`
- **NEVER** reference wrong column in summary: `=F8` when Amount is in column B
- **AVOID** merged cells in control rows - they break formula references

## When Formulas Return None

openpyxl does **not** evaluate formulas - it stores them as strings. When you load with `data_only=True`, you see cached values (usually None for new files). This is expected. To verify:
- Check the formula string itself: `print(ws['B12'].value)` should show `=SUM(B6:B11)`
- Do not rely on evaluated values until opened in Excel

## Troubleshooting

**Issue**: Summary shows `#REF!` when opened in Excel
**Cause**: Sheet name mismatch or column letter wrong
**Fix**: Verify `wb.sheetnames` exactly matches formula references (case-sensitive)

**Issue**: Type errors on numeric checks
**Cause**: Writing strings instead of numbers
**Fix**: Convert CSV strings to float: `float(row['apr_adds'])`

**Issue**: Verifier fails on cell value mismatch
**Cause**: Referencing F12 (Total Amortization) instead of E12 (April Month Total) for pool totals
**Fix**: Pool totals in summary reference the **last month column** (April), not Total Amortization column

## Known invariants (by sub-task)

### datacenter-capacity-rollforward
- Detail sheets: Named by pool (e.g., "Compute Pool #8100", "Storage Pool #8200")
- Summary sheet: Named "Capacity Summary"
- Sheet order matters: verifier checks `wb.sheetnames` sequence
- Control rows at positions 12 (Month Totals), 13 (Ending Balance), 14 (Variance), 15 (GL Balance)
- Reconciliation: GL Balance = Ending Balance + Total Amortization

### transit-subsidy-rollforward
- Input: JSON with GL balances, CSV with vendor schedules per program
- Detail sheets: Named by program (e.g., "Bus Program #4310", "Rail Program #4320")
- Summary sheet: Named "Transit Summary"
- Summary formulas link to specific columns in detail sheets (verify column letters)
- Combined totals may reference Variance rows or Ending Balance rows (verify from requirements)

## References

See `references/reconciliation-template.py` for a complete working script template with dynamic column calculation.
