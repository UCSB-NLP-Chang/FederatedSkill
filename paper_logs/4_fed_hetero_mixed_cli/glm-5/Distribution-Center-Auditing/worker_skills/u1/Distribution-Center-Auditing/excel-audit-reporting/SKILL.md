---
name: excel-audit-reporting
description: Generates multi-sheet Excel audit workbooks and executive Word briefs from raw receipt, transaction, or timesheet logs. Use when tasked with transforming tabular data into formatted audit reports, computing exception flags against reference rules, aggregating summaries, and producing executive summaries.
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
   Identify key columns (IDs, quantities, status flags, categories). **Check for auxiliary sheets** (e.g., `SLA_Rules`, `BreakRules`, `Config`, `Lookup`) that define thresholds, mappings, or business logic. Load these into a dict/list before processing the main data sheet.

2. **Define Business Rules**: Map exception conditions to integer 0/1 flags (e.g., `Qty Variance = 1 if received != expected`, `Cold Chain Error = 1 if temp-sensitive and status != OK`). If rules are defined in a separate sheet, build a lookup dict (e.g., `{'P1': {'max_hours': 4, 'esc_required': True}}`) and apply it row-by-row.

3. **Compute & Format**: Iterate through rows, append derived columns. Calculated flag columns must be **integer 0/1** (not boolean). Use `1 if condition else 0`.

4. **Aggregate Summary**: Group by relevant keys (e.g., Item Code + Supplier), sum flags, sort deterministically, and append a Grand Total row.

5. **Generate Outputs**:
   - Create a new `openpyxl` workbook with `RawData`, `Formatted Data`, and `Summary` sheets.
   - Use `python-docx` to draft an executive brief containing rule definitions, aggregate totals, high-impact findings, and actionable recommendations.

6. **Verify**: Run the verification snippet below to confirm sheet names, dimensions, and header values.

## Critical Rules (Must Follow)

### 1. Error Summary Must Use String "None", Not Python None
Error Summary cells for non-error rows must contain the **literal string "None"** (not empty, not NaN, not Python None).

**WRONG**:
```python
error_summary = ', '.join(errors) if errors else None  # Becomes empty cell!
```

**CORRECT**:
```python
error_summary = ', '.join(errors) if errors else 'None'  # Literal string
```

### 2. Always Verify With openpyxl, Never pandas
**pandas displays NaN for cells containing the string "None"** due to type inference. This causes false verification failures.

**WRONG**:
```python
import pandas as pd
df = pd.read_excel('output.xlsx')
print(df['Error Summary'])  # Shows NaN for "None" strings!
```

**CORRECT**:
```python
from openpyxl import load_workbook
wb = load_workbook('output.xlsx')
ws = wb['Formatted Data']
for row in ws.iter_rows(min_row=2, max_row=5, values_only=True):
    print(repr(row[-1]))  # Shows actual 'None' string
```

### 3. Calculated Flags Are Integers, Not Booleans
Use `1 if condition else 0`, not `condition` directly.

### 4. Column Names Must Match Exactly
Task requirements specify exact column names. Verify character-by-character including spaces, capitalization, and punctuation.

### 5. Summary Must Be Sorted Deterministically
Sort summary rows by grouping keys (e.g., Route, then Shipment ID) in ascending order before appending Grand Total. Unsorted summaries cause verification failures.

```python
sorted_keys = sorted(error_agg.keys())  # Sorts tuple keys lexicographically
summary_rows = [[*k, *v] for k, v in sorted_keys]
```

## Preserving Existing Sheets

When the source workbook contains sheets that must be preserved in the output (e.g., `Overview`, `Instructions`):

1. **Copy before processing**: Load source, copy preserved sheets to output workbook first.
2. **Do not modify preserved content**: Read and copy cells exactly as-is.

```python
src_wb = openpyxl.load_workbook('source.xlsx')
out_wb = openpyxl.Workbook()
out_wb.remove(out_wb.active)  # Remove default sheet

# Copy preserved sheets first
for sheet_name in ['Overview']:  # Add any sheets to preserve
    if sheet_name in src_wb.sheetnames:
        src_ws = src_wb[sheet_name]
        out_ws = out_wb.create_sheet(sheet_name)
        for row in src_ws.iter_rows(values_only=True):
            out_ws.append(row)

# Then add RawData, Formatted Data, Summary sheets
```

## Event Log Reconciliation Pattern

When auditing planned items against actual events (scans, dispositions, transactions) from a separate log:

1. **Load both sources**: Manifest/plan data and event log (separate files or sheets).
2. **Filter events by status**: Keep only qualifying statuses (e.g., `LOADED`, `COMPLETED`, `FINAL`). Ignore `PENDING`, `VOID`, `PRELIMINARY`, etc.
3. **Deduplicate by latest**: When multiple events exist per key, select the one with the latest timestamp.
4. **Build lookup dict**: Key by (ID, sub-ID) tuple for O(1) joins.
5. **Compute flags**:
   - **Missing Event** = 1 if no qualifying event exists for the plan line
   - **Mismatch** = 1 if event value differs from planned value (after normalization)

```python
# Build event lookup: (shipment_id, carton_id) -> (timestamp, scanned_value)
event_lookup = {}
for row in event_rows:
    key = (str(row[0]).strip(), str(row[1]).strip())
    status = str(row[status_col]).strip().upper()
    if status != 'LOADED':
        continue
    ts = row[ts_col]
    if key not in event_lookup or ts > event_lookup[key][0]:
        event_lookup[key] = (ts, str(row[value_col]).strip())

# Compute flags for each manifest row
for row in manifest_rows:
    key = (str(row[0]).strip(), str(row[1]).strip())
    if key not in event_lookup:
        missing = 1
        mismatch = 0
    else:
        missing = 0
        planned = str(row[planned_col]).strip()
        actual = event_lookup[key][1]
        mismatch = 0 if planned.upper() == actual.upper() else 1
```

See `returns-disposition-audit` skill for a complete implementation template.

## Decision Rules & Anti-Patterns

- **Do not** rely on `read_file` for `.xlsx` files; they are binary. Always use `openpyxl`.
- **Do not** use `pandas` for Excel operations. It often isn't installed and lacks formatting control. Stick to `openpyxl`.
- **Do not** use complex Python one-liners in shell commands; they hit quote escaping issues. Write temporary scripts instead.
- **Always** compute aggregates from the formatted data, not the raw source, to ensure consistency.
- **Sort** summary tables deterministically (e.g., by primary key, then secondary key) before writing.
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

## Pre-Submission Verification Checklist
Before submitting, verify ALL of the following with openpyxl:

```python
from openpyxl import load_workbook

wb = load_workbook('output.xlsx')

# 1. Sheet names match exactly
print('Sheets:', wb.sheetnames)  # Should be ['RawData', 'Formatted Data', 'Summary']

# 2. Column headers match task requirements exactly
for name in wb.sheetnames:
    ws = wb[name]
    headers = [ws.cell(1, c).value for c in range(1, ws.max_column+1)]
    print(f'{name} headers: {headers}')

# 3. Error Summary contains string "None", not empty/NaN
ws = wb['Formatted Data']
error_col = None
for c in range(1, ws.max_column+1):
    if ws.cell(1, c).value == 'Error Summary':
        error_col = c
        break
if error_col:
    for r in range(2, min(ws.max_row+1, 5)):
        val = ws.cell(r, error_col).value
        print(f'Row {r} Error Summary: {repr(val)} (type: {type(val).__name__})')
        assert val is not None, f'Row {r} has None/empty Error Summary'
        assert val == 'None' or val != '', f'Row {r} has invalid Error Summary: {repr(val)}'

# 4. Flag columns are integers, not floats or booleans
ws = wb['Formatted Data']
for col_name in ['Total Errors']:  # Add other flag columns as needed
    for c in range(1, ws.max_column+1):
        if ws.cell(1, c).value == col_name:
            for r in range(2, min(ws.max_row+1, 5)):
                val = ws.cell(r, c).value
                assert isinstance(val, int), f'{col_name} at row {r} is {type(val).__name__}, not int'
            break

# 5. Summary Grand Total row exists and sums correctly
ws = wb['Summary']
last_row = [ws.cell(ws.max_row, c).value for c in range(1, ws.max_column+1)]
print(f'Last Summary row: {last_row}')
assert last_row[0] == 'Grand Total', 'Summary missing Grand Total row'

# 6. Summary is sorted correctly (grouping keys in ascending order)
ws = wb['Summary']
group_cols = []  # Indices of grouping columns (0-indexed from header)
for c in range(1, ws.max_column+1):
    header = ws.cell(1, c).value
    if header in ['Route', 'Shipment ID', 'Warehouse', 'Carrier', 'Facility', 'Session ID']:  # Add grouping keys as needed
        group_cols.append(c - 1)
if group_cols:
    rows = list(ws.iter_rows(min_row=2, max_row=ws.max_row-1, values_only=True))  # Exclude Grand Total
    for i in range(len(rows) - 1):
        curr = tuple(rows[i][c] for c in group_cols)
        next_ = tuple(rows[i+1][c] for c in group_cols)
        assert curr <= next_, f'Summary not sorted: {curr} should come before {next_}'
```

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

### timesheet-policy-audit
- Load BreakRules from separate sheet as lookup dict keyed by Role with fields: Min Break Minutes, Overtime Threshold.
- Break Deficit = 1 if Break Minutes < Min Break Minutes for that role.
- Approval Missing = 1 if Hours Worked > Overtime Threshold for that role AND (Approval Code is None OR empty string).
- Summary aggregates by (Employee ID, Week Ending) and filters to groups with Total Errors > 0.
- Include Grand Total row after filtering.

### manifest-scan-audit
- Join manifest/plan data to scan/event log by (Shipment ID, Carton ID) or equivalent key.
- Filter events to qualifying status only (typically `LOADED` or `COMPLETED`).
- Select latest event per key when multiple events exist (compare timestamps).
- Missing Event flag = 1 if no qualifying event found for manifest line.
- Mismatch flag = 1 if event value (e.g., scanned zone) differs from planned value.
- Summary groups by (Route, Shipment ID) or task-specified keys; filter to Total Errors > 0.
- Preserve any existing sheets (e.g., `Overview`) in the output workbook.

### cycle-count-variance-audit
- Join plan lines to count event log by (Facility, Session ID, Bin ID).
- Filter events to `FINAL` status only; ignore `PRELIMINARY`, `VOID`.
- Select latest FINAL event per key when multiple exist.
- **Missing Final Count** = 1 if no FINAL event exists OR FINAL event has NaN/null Count Qty.
- **Approval Gap** = 1 if Approval Needed = 'YES' AND valid count exists AND |Expected - Count| > Allowed Variance.
- If Missing Final Count = 1, then Approval Gap = 0 (cannot have approval gap without valid count).
- Error Summary uses string `"None"`, not Python None.
- Summary groups by (Facility, Session ID); filter to Total Errors > 0.
- Preserve template sheets (e.g., `Overview`) in output workbook.
- See `references/cycle-count-variance-audit.md` for detailed implementation.

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
9. **pandas shows NaN but Excel is correct**: When verifying Error Summary columns, pandas readback may display `NaN` for cells that actually contain the string `"None"`. This is a pandas type inference artifact. **Always verify with openpyxl** to see actual cell values. If openpyxl shows `"None"` strings, the output is correct regardless of what pandas displays.
10. **Summary not sorted correctly**: Verify summary rows are sorted by grouping keys in ascending order before Grand Total. Use `sorted(keys)` on tuple keys for lexicographic ordering.
11. **Headers showing as None**: If verification shows `None` for headers, check that `ws.append(headers)` is called before any data rows, and that headers is a list of strings (not a single string or None).
12. **Error Summary shows empty cells**: You used Python `None` instead of string `"None"`. Fix: `error_summary = ', '.join(errors) if errors else 'None'`.

If verifier output is unavailable, re-read task requirements and compare against generated output byte-by-byte.

## Script Usage
Execute `scripts/generate_audit.py` via shell when the task requires generating an audit workbook and executive brief. Adapt column names and grouping keys to match specific task requirements.

## References
- `references/nan-none-handling.md`: Detailed patterns for handling NaN vs "None" string distinction
- `references/row-offset-handling.md`: Detailed guidance on openpyxl row numbering
- `references/event-log-reconciliation.md`: General pattern for joining plan data to event logs
- `references/cycle-count-variance-audit.md`: Specific pattern for cycle count variance audits with Missing Final Count and Approval Gap flags