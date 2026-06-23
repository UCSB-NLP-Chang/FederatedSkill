---
name: excel-capacity-reconciliation
description: Builds Excel workbooks for datacenter/cloud capacity reconciliation, vendor rollforwards, and financial control blocks. Use when tasks require multi-sheet workbooks with beginning balance + adds - amortization rollforwards, monthly control blocks (Totals, Ending Balance, Variance, GL Balance), cross-sheet summary aggregation, and strict legacy node/verifier checks.
---

# Excel Capacity Reconciliation & Rollforward

## Workflow
1. **Initialize Workbook**: 
   - `wb = openpyxl.Workbook()`
   - `wb.remove(wb.active)` (Remove default sheet immediately)
   - Create **Summary sheet first**, then detail sheets. Do not use `wb.move_sheet()`.
2. **Parse Inputs**: Extract vendor lists, beginning balances, monthly adds/amortization, and GL ledger balances.
3. **Build Detail Sheets**: One sheet per pool/account.
   - Row 4: Headers (`Vendor`, `Beg Balance`, `Jan Adds`, `Jan Amort`, ..., `Apr Ending`)
   - Rows 6+: Vendor data (store as Python `float`).
   - Control Rows: Calculate dynamically: `ctrl_start = 6 + num_vendors`.
     - `Beginning Balance`: `=SUM(B6:B{last})`
     - `Month Totals`: `=SUM(L6:L{last})` (or relevant month column)
     - `Ending Balance`: `=Beg + Adds - Amort` (chain monthly)
     - `Variance`: `=Ending_Balance - GL_Balance`
     - `GL Balance`: Hardcoded ledger values.
   - Place control rows at `ctrl_start` through `ctrl_start + 4`.
4. **Build Summary Sheet**:
   - Row 6: Beginning Balance (combined, cross-sheet refs)
   - Monthly Control Blocks: Jan (rows 7–10), Feb (rows 12–15), etc. Leave exactly one blank row between blocks.
   - Formulas must reference detail sheets: `='DetailSheet'!Cell`. Quote sheet names with spaces/`#`.
   - `Total Variance`: Sum of monthly variances.
5. **Formatting**: Apply `#,##0.00` to currency columns. Ensure all numeric values are Python `float`.
6. **Save & Verify**: `wb.save(path)`. Run `scripts/verify_rollforward.py <path>` immediately after saving to catch structural mismatches before submission.

## Critical Rules for Legacy Node Checks
- **Exact Row/Column Alignment**: Verifiers check specific row indices. Do not shift rows. Use dynamic calculation for control rows but verify final indices.
- **Formula Syntax**: Use standard Excel syntax (`=SUM(D6:D11)`, `=C6+D12-E12`). Do not use `openpyxl` formula builders that generate non-standard syntax.
- **Cross-Sheet References**: Must match exact sheet names: `='Compute Pool #8100'!D12`. Include single quotes if sheet names contain spaces or `#`.
- **Data Types**: All monetary values must be `float`. Booleans must be `True`/`False`. Dates as `datetime.date` or `YYYY-MM-DD` strings.
- **Blank Rows**: Control blocks are often separated by exactly one blank row. Explicitly write `None` or `""` to prevent `openpyxl` from miscounting `max_row`.
- **No `data_only=True` for generation**: Write formulas as strings. `data_only=True` is only for reading pre-calculated files.

## Troubleshooting & Anti-Patterns
- **Sheet Order**: Always create Summary first. `wb.move_sheet()` is brittle and often leaves artifacts or fails legacy checks.
- **Verifier fails on structure**: Check `ws.max_row` and `ws.max_column`. Ensure no trailing empty rows/columns are counted as data. Run `scripts/verify_rollforward.py` to dump structure.
- **Formula mismatch**: Open generated file in Excel/LibreOffice to verify formulas resolve. Check for missing `$` in absolute references if required.
- **Type errors**: `openpyxl` may coerce strings to numbers if formatted, but explicitly cast to `float` before assignment.
- **Environment**: Install `openpyxl`: `pip install openpyxl --break-system-packages -q`. Use `openpyxl.styles.NumberFormat` for currency.
