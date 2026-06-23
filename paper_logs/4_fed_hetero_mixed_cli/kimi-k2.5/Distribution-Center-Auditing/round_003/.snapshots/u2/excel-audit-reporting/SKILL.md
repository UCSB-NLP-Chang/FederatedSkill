---
name: excel-audit-reporting
description: Generates multi-sheet Excel audit workbooks and executive Word briefs from raw receipt or transaction logs. Use when tasked with transforming tabular data into formatted audit reports, computing exception flags, aggregating summaries, and producing executive summaries. Triggered by tasks involving .xlsx audit generation, compliance checks, and Word brief creation.
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
   cat > /tmp/xl_inspect.py << 'EOF'
   import openpyxl
   wb = openpyxl.load_workbook('source.xlsx')
   ws = wb.active
   print('Sheet:', ws.title)
   print('Rows:', ws.max_row, 'Cols:', ws.max_column)
   headers = [ws.cell(1, c).value for c in range(1, ws.max_column+1)]
   print('Headers:', headers)
   for r in range(2, min(ws.max_row+1, 6)):
       print([ws.cell(r, c).value for c in range(1, ws.max_column+1)])
   EOF
   python3 /tmp/xl_inspect.py
   ```
2. **Define Business Rules**: Map exception conditions to boolean/integer flags (e.g., `Qty Variance = 1 if received != expected`, `Cold Chain Error = 1 if temp-sensitive and status != OK`).
3. **Compute & Format**: Iterate through rows, append derived columns. Calculated flag columns must be **integer 0/1** (not boolean).
4. **Aggregate Summary**: Group by relevant keys, sum flags, sort deterministically, and append a Grand Total row.
5. **Generate Outputs**:
   - Create new `openpyxl` workbook with `RawData`, `Formatted Data`, and `Summary` sheets.
   - Use `python-docx` to draft an executive brief with rule definitions, aggregate totals, high-impact findings, and actionable recommendations.
6. **Verify**: Run the verification snippet below to confirm sheet names, dimensions, and header values.

## Decision Rules & Anti-Patterns
- **Do not** rely on `read_file` for `.xlsx` files; they are binary. Always use `openpyxl`.
- **Do not** use `pandas` for Excel operations. It often isn't installed and lacks formatting control. Stick to `openpyxl`.
- **Do not** use complex Python one-liners in shell commands; they hit quote escaping issues. Write temporary scripts instead.
- **Do not** name temporary scripts after Python standard library modules (e.g., `inspect.py`, `io.py`, `sys.py`, `os.py`, `json.py`, `csv.py`, `datetime.py`). Doing so causes circular import errors. Use task-specific names like `xl_inspect.py`, `check_source.py`, or `audit_script.py`.
- **Always** compute aggregates from the formatted data, not the raw source.
- **Sort** summary tables deterministically before writing.
- Calculated columns must be **integer 0/1** (not boolean True/False). Use `1 if condition else 0`.
- Error Summary cells for non-error rows must contain **literal string "None"** (not empty, not NaN). Use explicit `'None'` string assignment.

## Row Offset Gotcha (openpyxl)
When writing data with `ws.cell(row=r, column=c, value=...)`:
- **Headers go in row 1**. Data rows must start at **row 2**.
- If iterating source rows with `for r in range(2, max_row+1)`, write to `ws.cell(row=r, ...)` — **not** `row=r-1`. Using `r-1` overwrites the header row with the first data row.
- **Safer alternative**: Use `ws.append([...])` which auto-advances the row cursor. Call `ws.append(headers)` once, then `ws.append(row_data)` for each data row.

## Troubleshooting
- **Circular Import Error**: If you see `AttributeError: partially initialized module 'X' has no attribute 'Y'` or similar import errors mentioning "partially initialized module", your script filename conflicts with a Python standard library module. Rename your script to something unambiguous (e.g., change `inspect.py` to `xl_inspect.py` and delete the conflicting file).
- **Header row overwritten**: If the first data row appears as headers, check your row offset — data should start at row 2, not row 1.
- **Column name mismatch**: Check exact column names against task requirements (case-sensitive, no extra spaces).
- **Data type issues**: Confirm integers are integers (not floats like 1.0), strings are strings (not NaN).
- **Sheet names mismatch**: Verify sheet names exactly: "RawData", "Formatted Data", "Summary".

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs:
- **DO NOT**: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`
- **DO**: `ws.cell(row=r, column=c, value=x)` with x as a raw float
The verifier's tolerance decides acceptable precision; provide full precision.

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
    # Check specific data rows if needed
```
For Word documents, reload with `python-docx` to confirm paragraph counts and key content presence.

## Known Invariants (by sub-task)

### distribution-center-receipt-audit
- Calculated error flags must be **integer 0/1** (not boolean True/False). Use `1 if condition else 0`.
- Error Summary cells for non-error rows must contain **literal string "None"** (not empty, not NaN).
- Summary sheet filters to error rows only and includes Grand Total row.
- Column headers match expected names exactly: "Qty Variance", "Cold Chain Error", "Total Errors", "Error Summary".
- Verify Excel outputs with **openpyxl**, not pandas, to confirm actual cell values.

## Script Usage
- Execute `scripts/generate_audit.py` via `run_shell_command` when the task requires generating an audit workbook and executive brief.
- Adapt the `compute_flags` function and column mappings to match the specific task requirements.
- If modifications are extensive, copy the script pattern into a new task-specific file rather than editing the shared template in place.
