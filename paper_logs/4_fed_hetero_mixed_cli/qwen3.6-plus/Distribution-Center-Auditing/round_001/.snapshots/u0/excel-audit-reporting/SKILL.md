---
name: excel-audit-reporting
description: Generates multi-sheet Excel audit workbooks and executive Word briefs from raw receipt or transaction logs. Use when tasked with transforming tabular data into formatted audit reports, computing exception flags, aggregating summaries, and producing executive summaries.
---

# Excel Audit Reporting & Executive Brief Generation

## Workflow
1. **Inspect Source**: Use `openpyxl` via `run_shell_command` to load the source workbook. Read headers and all data rows. Identify key columns (IDs, quantities, status flags, categories).
2. **Define Business Rules**: Map exception conditions to boolean/integer flags (e.g., `Qty Variance = 1 if received != expected`, `Cold Chain Error = 1 if temp-sensitive and status != OK`).
3. **Compute & Format**: Iterate through rows, append derived columns, and build an in-memory list of formatted rows.
4. **Aggregate Summary**: Group by relevant keys (e.g., Item Code + Supplier), sum flags, sort deterministically, and append a Grand Total row.
5. **Generate Outputs**:
   - Create a new `openpyxl` workbook with `RawData`, `Formatted Data`, and `Summary` sheets.
   - Use `python-docx` to draft an executive brief containing rule definitions, aggregate totals, high-impact findings, and actionable recommendations.
6. **Verify**: Programmatically reload outputs to confirm sheet names, column counts, row counts, and header values before declaring completion.

## Decision Rules & Anti-Patterns
- **Do not** rely on `read_file` for `.xlsx` files; they are binary. Always use `openpyxl` via `run_shell_command`.
- **Always** compute aggregates from the formatted data, not the raw source, to ensure consistency.
- **Sort** summary tables deterministically (e.g., by primary key, then secondary key) before writing.
- **Verify** outputs immediately after generation. Check `max_row`, `max_column`, and header values programmatically.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### multi-sheet-audit-report
- Calculated error flags must be **integer 0/1**, not boolean True/False. Use `.astype(int)` or `int()` conversion.
- Error Summary cells without errors must contain the **literal string "None"** (not empty, not NaN, not Python None). Assign explicitly: `or "None"` pattern or `df.loc[~mask, 'Error Summary'] = 'None'`.
- Summary sheet row counts and totals must match detail sheet aggregates.
- Verify Excel outputs with **openpyxl**, not pandas, to confirm actual cell values (pandas may mask NaN/None issues).

## Script Usage
- Execute `scripts/generate_audit.py` via `run_shell_command` when the task requires generating an audit workbook and executive brief. Adapt the `compute_flags` function and column mappings to match the specific task requirements.