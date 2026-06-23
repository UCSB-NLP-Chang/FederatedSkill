---
name: excel-capacity-reconciliation
description: Builds Excel workbooks for datacenter/cloud capacity reconciliation, vendor rollforwards, and financial control blocks. Use when tasks require multi-sheet workbooks with beginning balance + adds - amortization rollforwards, monthly control blocks (Totals, Ending Balance, Variance, GL Balance), cross-sheet summary aggregation, and strict legacy node/verifier checks.
---

# Excel Capacity Reconciliation & Rollforward

## Workflow
1. **Parse Inputs**: Extract vendor lists, beginning balances, monthly adds/amortization, and GL ledger balances from source files.
2. **Build Detail Sheets**: One sheet per pool/account.
   - Row 4: Headers (`Vendor`, `Beg Balance`, `Jan Adds`, `Jan Amort`, ..., `Apr Ending`)
   - Rows 6+: Vendor data (store as Python `float`).
   - Control Rows (typically 12–15):
     - `Month Totals`: `=SUM(range)` for adds/amort columns.
     - `Ending Balance`: Rollforward formula `=Beg + Adds - Amort` (chain monthly: `=Prev_Ending + Curr_Adds - Curr_Amort`).
     - `Variance`: `=Ending_Balance - GL_Balance`
     - `GL Balance`: Hardcoded ledger values.
3. **Build Summary Sheet**:
   - Row 6: Pool names (e.g., `Compute Pool #8100`).
   - Monthly Control Blocks: Jan (rows 7–10), Feb (rows 12–15), etc. Leave exactly one blank row between blocks.
   - Formulas must reference detail sheets: `='DetailSheet'!Cell`.
   - `Total Variance`: Sum of monthly variances (e.g., `=B9+B14`).
4. **Formatting**: Apply `#,##0.00` to currency columns. Ensure all numeric values are Python `float`.
5. **Save & Verify**: `wb.save(path)`. Run structural verification before submission.

## Critical Rules for Legacy Node Checks
- **Exact Row/Column Alignment**: Verifiers check specific row indices (e.g., headers at row 4, data starts row 6, control rows at 12–15). Do not shift rows.
- **Formula Syntax**: Use standard Excel syntax (`=SUM(D6:D11)`, `=C6+D12-E12`). Do not use `openpyxl` formula builders that generate non-standard syntax.
- **Cross-Sheet References**: Must match exact sheet names: `='Compute Pool #8100'!D12`. Include single quotes if sheet names contain spaces or `#`.
- **Data Types**: All monetary values must be `float`. Booleans must be `True`/`False`. Dates as `datetime.date` or `YYYY-MM-DD` strings.
- **Blank Rows**: Control blocks are often separated by exactly one blank row. Preserve this spacing.
- **No `data_only=True` for generation**: Write formulas as strings. `data_only=True` is only for reading pre-calculated files.

## Troubleshooting
- **Verifier fails on structure**: Check `ws.max_row` and `ws.max_column`. Ensure no trailing empty rows/columns are counted as data.
- **Formula mismatch**: Open the generated file in Excel/LibreOffice to verify formulas resolve correctly. Check for missing `$` in absolute references if required.
- **Type errors**: `openpyxl` may coerce strings to numbers if formatted, but explicitly cast to `float` before assignment.
- **Sheet order**: Summary sheet must be first. Detail sheets follow.

## Environment
- Install `openpyxl`: `pip install openpyxl --break-system-packages -q` (or use venv).
- Use `openpyxl.styles.NumberFormat` for currency formatting.