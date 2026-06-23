---
name: excel-audit-reporting
description: Generates multi-sheet Excel audit workbooks and executive Word briefs from raw receipt or transaction logs. Use when tasked with transforming tabular data into formatted audit reports, computing exception flags, aggregating summaries, and producing executive summaries.
---

# Excel Audit Reporting & Executive Brief Generation

## Environment Prerequisites
Before starting, ensure dependencies are available:
```bash
pip install --break-system-packages openpyxl python-docx -q
```
Modern systems (PEP 668) require the `--break-system-packages` flag for system-wide installs. If that fails, create a venv and use its python binary.

## Workflow

1. **Inspect Source**: Do not use `read_file` on .xlsx (binary). Instead write a temporary inspection script:
   ```bash
   cat > /tmp/check_xlsx.py << 'EOF'
   import openpyxl
   wb = openpyxl.load_workbook('source.xlsx')
   print('Sheets:', wb.sheetnames)
   for name in wb.sheetnames:
       ws = wb[name]
       print(f'\n=== {name} ===')
       for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row+1, 6), values_only=True):
           print(row)
   EOF
   python3 /tmp/check_xlsx.py
   ```
   Identify key columns (IDs, quantities, status flags, categories). **Check for auxiliary sheets** (e.g., `SLA_Rules`, `Config`, `Lookup`) that define thresholds, mappings, or business logic. Load these into a dict/list before processing the main data sheet.

2. **Define Business Rules**: Map exception conditions to integer 0/1 flags (e.g., `Qty Variance = 1 if received != expected`, `Cold Chain Error = 1 if temp-sensitive and status != OK`). If rules are defined in a separate sheet, build a lookup dict (e.g., `{'P1': {'max_hours': 4, 'esc_required': True}}`) and apply it row-by-row.

3. **Compute & Format**: Iterate through rows, append derived columns. Calculated flag columns must be **integer 0/1** (not boolean). Use `1 if condition else 0`.

4. **Aggregate Summary**: Group by relevant keys (e.g., Item Code + Supplier), sum flags, sort deterministically, and append a Grand Total row.

5. **Generate Outputs**:
   - Create a new `openpyxl` workbook with `RawData`, `Formatted Data`, and `Summary` sheets.
   - Use `python-docx` to draft an executive brief containing rule definitions, aggregate totals, high-impact findings, and actionable recommendations.

6. **Verify**: Run the verification snippet below to confirm sheet names, dimensions, and header values.

## Decision Rules & Anti-Patterns

- **Do not** rely on `read_file` for `.xlsx` files; they are binary. Always use `openpyxl`.
- **Do not** use `pandas` for Excel operations. It often isn't installed and lacks formatting control. Stick to `openpyxl`.
- **Do not** use complex Python one-liners in shell commands; they hit quote escaping issues. Write temporary scripts instead.
- **Always** compute aggregates from the formatted data, not the raw source, to ensure consistency.
- **Sort** summary tables deterministically (e.g., by primary key, then secondary key) before writing.
- Calculated columns must be **integer 0/1** (not boolean True/False). Use `1 if condition else 0`.
- Error Summary cells for non-error rows must contain **literal string "None"** (not empty, not NaN). Use explicit `'None'` string assignment: `", ".join(...) or "None"`.
- **Handle openpyxl `None` values explicitly**: When reading cells, `openpyxl` returns Python `None` for empty cells. Use `val is None` or `str(val).strip()` before comparisons to avoid `TypeError` or silent mismatches during rule evaluation.

## openpyxl Row Offset Gotcha
When writing data with `ws.cell(row=r, column=c, value=...)`:
- **Headers go in row 1**. Data rows must start at **row 2**.
- If iterating source rows with `for r in range(2, max_row+1)`, write to `ws.cell(row=r, ...)` — **not** `row=r-1`. Using `r-1` overwrites the header row with the first data row.
- **Safer alternative**: Use `ws.append([...])` which auto-advances the row cursor. Call `ws.append(headers)` once, then `ws.append(row_data)` for each data row.

## Script Naming Warning
**Never name temporary Python scripts `inspect.py`** in `/tmp/` or the working directory. Python's standard library includes an `inspect` module, and naming a script `inspect.py` causes a circular import error when `openpyxl` (or many other packages) tries to `import inspect`. Use names like `check_xlsx.py`, `audit_gen.py`, or `verify.py` instead.

## Output Precision
Never round, truncate, or fixed-format numeric values when writing outputs:
- **DO NOT**: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`
- **DO**: `ws.cell(row=r, column=c, value=x)` with x as a raw float
The verifier's tolerance (often 1e-4) decides acceptable precision; provide full precision.

## Verification Snippet
After generation, verify the workbook structure:
```python
import openpyxl
wb = openpyxl.load_workbook('output.xlsx')
print('Sheets:', wb.sheetnames)
for name in wb.sheetnames:
    ws = wb[name]
    print(f'{name}: {ws.max_row} rows, {ws.max_column} cols')
    headers = [ws.cell(1, c).value for c in range(1, ws.max_column+1)]
    print('  Headers:', headers)
```
For Word documents, reload with `python-docx` to confirm paragraph counts and key content presence.

## Known Invariants (by sub-task)

### multi-sheet-audit-report
- Calculated error flags must be **integer 0/1**, not boolean True/False. Use `int()` conversion.
- Error Summary cells without errors must contain the **literal string "None"** (not empty, not NaN, not Python None). Assign explicitly: `or "None"` pattern or conditional assignment.
- Summary sheet row counts and totals must match detail sheet aggregates.
- Verify Excel outputs with **openpyxl**, not pandas, to confirm actual cell values (pandas may mask NaN/None issues).

## Troubleshooting

When local verification passes but verifier fails:

1. **Column name mismatch**: Check exact column names against task requirements (case-sensitive, no extra spaces, exact spelling)
2. **Summary sheet structure**: Verify grouping columns, error count columns, and total column names match expected format
3. **Word document sections**: Ensure all required sections are present (definitions, totals, recommendations)
4. **Data type issues**: Confirm integers are integers (not floats like 1.0), strings are strings (not NaN)
5. **Grand Total format**: Check if Grand Total row uses `-` or empty string for non-numeric columns
6. **Sheet names**: Verify sheet names match exactly ("RawData" vs "Raw Data")
7. **Formatted Data header overwritten**: If the first data row appears as headers, check your row offset — data should start at row 2, not row 1.
8. **Circular import on `import openpyxl`**: If you see `AttributeError: partially initialized module 'openpyxl' has no attribute 'load_workbook'`, check for a file named `inspect.py` in `/tmp/` or the working directory. Remove it and rename your script.

If verifier output is unavailable, re-read task requirements and compare against generated output byte-by-byte.

## Script Usage
Execute `scripts/generate_audit.py` via shell when the task requires generating an audit workbook and executive brief. Adapt column names and grouping keys to match specific task requirements.
