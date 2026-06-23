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
   cat > /tmp/inspect.py << 'EOF'
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
   python3 /tmp/inspect.py
   ```
2. **Define Business Rules**: Map exception conditions to boolean/integer flags (e.g., `Qty Variance = 1 if received != expected`, `Cold Chain Error = 1 if temp-sensitive and status != OK`).
3. **Compute & Format**: Iterate through rows, append derived columns. Calculated flag columns must be **integer 0/1** (not boolean).
4. **Aggregate Summary**: Group by relevant keys, sum flags, sort deterministically, and append a Grand Total row.
5. **Generate Outputs**:
   - Create new `openpyxl` workbook with `RawData`, `Formatted Data`, and `Summary` sheets.
   - Use `python-docx` to draft an executive brief with rule definitions, aggregate totals, high-impact findings, and actionable recommendations.
6. **Verify**: Run the verification snippet below to confirm sheet names, dimensions, and header values.

## Key Patterns

### Multi-Sheet Excel Creation
```python
from openpyxl import Workbook
wb = Workbook()
ws_raw = wb.active
ws_raw.title = "RawData"
ws_formatted = wb.create_sheet("Formatted Data")
ws_summary = wb.create_sheet("Summary")
```

### Handling None/NaN in Excel Output
- Pandas NaN displays as NaN; convert to desired string before writing
- Use `df.fillna('None')` or conditional logic for clean Excel output
- Verify with openpyxl directly: `ws.cell(row, col).value`
- Error Summary cells for non-error rows must contain **literal string "None"** (not empty, not NaN, not Python None)

### Word Document Creation
```python
from docx import Document
doc = Document()
doc.add_heading('Title', level=1)
doc.add_paragraph('Content...')
doc.save(path)
```

## Summary Sheet Column Naming

Summary sheet column names should follow the task's explicit requirements. Common patterns:
- Grouping columns first (e.g., `Item Code`, `Supplier`, `Carrier`, `Yard`)
- Error count columns: `{Error Type} Errors` or `{Error Type}` depending on task specification
- Total column: `Total Errors`
- Grand Total row with `-` for non-numeric grouping columns

**Always check task requirements for exact column names** - they may differ from defaults.

## Decision Rules & Anti-Patterns
- **Do not** rely on `read_file` for `.xlsx` files; they are binary. Always use `openpyxl`.
- **Do not** use `pandas` for Excel operations. It often isn't installed and lacks formatting control. Stick to `openpyxl`.
- **Do not** use complex Python one-liners in shell commands; they hit quote escaping issues. Write temporary scripts instead.
- **Always** compute aggregates from the formatted data, not the raw source.
- **Sort** summary tables deterministically before writing.
- Calculated columns must be **integer 0/1** (not boolean True/False). Use `1 if condition else 0`.
- Error Summary cells for non-error rows must contain **literal string "None"** (not empty, not NaN). Use explicit `'None'` string assignment.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs:
- **DO NOT**: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`
- **DO**: `ws.cell(row=r, column=c, value=x)` with x as a raw float
The verifier's tolerance decides acceptable precision; provide full precision.

## Known invariants (by sub-task)

### distribution-center-receipt-audit
- Calculated error flags must be **integer 0/1** (not boolean True/False). Use `1 if condition else 0`.
- Error Summary cells for non-error rows must contain **literal string "None"** (not empty, not NaN). Use explicit `'None'` string assignment.
- Summary sheet filters to error rows only and includes Grand Total row
- Column headers match expected names exactly: "Qty Variance", "Cold Chain Error", "Total Errors", "Error Summary"
- Verify Excel outputs with **openpyxl**, not pandas, to confirm actual cell values (pandas may mask NaN/None issues).

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

## Troubleshooting

When local verification passes but verifier fails:

1. **Column name mismatch**: Check exact column names against task requirements (case-sensitive, no extra spaces, exact spelling)
2. **Summary sheet structure**: Verify grouping columns, error count columns, and total column names match expected format
3. **Word document sections**: Ensure all required sections are present (definitions, totals, recommendations)
4. **Data type issues**: Confirm integers are integers (not floats like 1.0), strings are strings (not NaN)
5. **Grand Total format**: Check if Grand Total row uses `-` or empty string for non-numeric columns
6. **Sheet names**: Verify sheet names match exactly ("RawData" vs "Raw Data")

If verifier output is unavailable, re-read task requirements and compare against generated output byte-by-byte.

## Script Usage
- Execute `scripts/create_audit_report.py` via shell when the task requires generating an audit workbook and executive brief.
- Adapt column names and grouping keys to match specific task requirements.

## References

- `references/nan-none-handling.md` — Critical patterns for NaN vs string "None" in Excel output
