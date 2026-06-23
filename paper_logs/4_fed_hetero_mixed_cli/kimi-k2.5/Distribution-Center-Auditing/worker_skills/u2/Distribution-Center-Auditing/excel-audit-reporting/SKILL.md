---
name: excel-audit-reporting
description: Generates multi-sheet Excel audit workbooks and executive Word briefs from raw receipt, transaction, service desk, or timesheet logs. Use when tasked with transforming tabular data into formatted audit reports, computing exception flags against reference rules, aggregating summaries, and producing executive summaries. Triggered by tasks involving .xlsx audit generation, compliance checks, timesheet policy audits, SLA violation audits, and Word brief creation.
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
   print('Sheets:', wb.sheetnames)
   for sheet in wb.sheetnames:
       ws = wb[sheet]
       print(f'\n=== {sheet} ===')
       print('Rows:', ws.max_row, 'Cols:', ws.max_column)
       headers = [ws.cell(1, c).value for c in range(1, ws.max_column+1)]
       print('Headers:', headers)
       for r in range(2, min(ws.max_row+1, 6)):
           print([ws.cell(r, c).value for c in range(1, ws.max_column+1)])
   EOF
   python3 /tmp/xl_inspect.py
   ```
2. **Identify Reference Data**: If business rules (SLA thresholds, tolerance limits, required flags) live in separate sheets (e.g., `SLA_Rules`), load them as lookup dictionaries keyed by the matching field.
3. **Define Business Rules**: Map exception conditions to boolean/integer flags. For tiered thresholds, lookup the limit from reference data first:
   ```python
   sla_rules = {'P1': {'max_hours': 4, 'escalation_required': 'Y'}, ...}
   max_hours = sla_rules[priority]['max_hours']
   breach = 1 if open_age > max_hours else 0
   ```
4. **Compute & Format**: Iterate through rows, append derived columns. Calculated flag columns must be **integer 0/1** (not boolean).
5. **Aggregate Summary**: Group by relevant keys, sum flags, sort deterministically. **Filter to error rows only** if the task requires showing only groups with exceptions, then append a Grand Total row.
6. **Generate Outputs**:
   - Create new `openpyxl` workbook with `RawData`, `Formatted Data`, and `Summary` sheets.
   - Use `python-docx` to draft an executive brief with rule definitions, aggregate totals, high-impact findings, and actionable recommendations.
7. **Verify**: Run the verification snippet below to confirm sheet names, dimensions, and header values.

## Critical Rules (Must Follow)

### 1. Error Summary Must Use String "None", Not Python None
Error Summary cells for non-error rows must contain the **literal string "None"** (not empty, not NaN, not Python None).

**WRONG**:
```python
error_summary = ", ".join(errors) if errors else None  # Becomes empty cell!
```

**CORRECT**:
```python
error_summary = ", ".join(errors) if errors else "None"  # Literal string
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

When auditing planned items (manifests, orders, shipments) against actual events (scans, dispositions, transactions) from a separate log:

1. **Load both sources**: Manifest/plan data and event log (separate files or sheets).
2. **Filter events by status**: Keep only qualifying statuses (e.g., `LOADED`, `COMPLETED`). Ignore `PENDING`, `VOID`, etc.
3. **Deduplicate by latest**: When multiple events exist per key, select the one with the latest timestamp.
4. **Build lookup dict**: Key by (ID, sub-ID) tuple for O(1) joins.
5. **Compute flags**:
   - **Missing Event** = 1 if no qualifying event exists for the plan line
   - **Mismatch** = 1 if event value differs from planned value (after normalization)

```python
# Build event lookup: (id1, id2) -> (timestamp, value)
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

See `multi-file-join-audit` skill for complete implementation templates.

## Decision Rules & Anti-Patterns

- **Do not** rely on `read_file` for `.xlsx` files; they are binary. Always use `openpyxl`.
- **Do not** use `pandas` for Excel operations. It often isn't installed and lacks formatting control. Stick to `openpyxl`.
- **Do not** use complex Python one-liners in shell commands; they hit quote escaping issues. Write temporary scripts instead.
- **Do not** name temporary scripts after Python standard library modules (e.g., `inspect.py`, `io.py`, `sys.py`, `os.py`, `json.py`, `csv.py`, `datetime.py`). Doing so causes circular import errors. Use task-specific names like `xl_inspect.py`, `check_source.py`, or `audit_script.py`.
- **Do not** hardcode business rule thresholds; always load them from reference sheets if available.
- **Always** compute aggregates from the formatted data, not the raw source.
- **Sort** summary tables deterministically before writing.
- **Filter** summary to error-only rows when the task implies focusing on exceptions (exclude rows where Total Errors = 0).
- Calculated columns must be **integer 0/1** (not boolean True/False). Use `1 if condition else 0`.
- Error Summary cells for non-error rows must contain **literal string "None"** (not empty, not NaN). Use explicit `'None'` string assignment.

## Row Offset Gotcha (openpyxl)
When writing data with `ws.cell(row=r, column=c, value=...)`:
- **Headers go in row 1**. Data rows must start at **row 2**.
- If iterating source rows with `for r in range(2, max_row+1)`, write to `ws.cell(row=r, ...)` — **not** `row=r-1`. Using `r-1` overwrites the header row with the first data row.
- **Safer alternative**: Use `ws.append([...])` which auto-advances the row cursor. Call `ws.append(headers)` once, then `ws.append(row_data)` for each data row.

## Multi-Sheet Reference Data Pattern
When source contains reference sheets (e.g., `SLA_Rules` mapping Priority Tier to thresholds):
```python
wb = openpyxl.load_workbook('source.xlsx')
rules_ws = wb['SLA_Rules']
rules = {}
for row in rules_ws.iter_rows(min_row=2, values_only=True):
    priority, max_hours, escalation_req = row
    rules[priority] = {'max_hours': max_hours, 'escalation_required': escalation_req}

# Use in compute_flags
def compute_flags(row_data, headers):
    priority = row_data[headers.index('Priority Tier')]
    open_age = row_data[headers.index('Open Age Hours')]
    escalation_code = row_data[headers.index('Escalation Code')]
    
    rule = rules.get(priority, {})
    sla_breach = 1 if open_age > rule.get('max_hours', 999) else 0
    missing_esc = 1 if rule.get('escalation_required') == 'Y' and not escalation_code else 0
    return {'SLA Breach': sla_breach, 'Missing Escalation': missing_esc, ...}
```

## Troubleshooting
- **Circular Import Error**: If you see `AttributeError: partially initialized module 'X' has no attribute 'Y'` or similar import errors mentioning "partially initialized module", your script filename conflicts with a Python standard library module. Rename your script to something unambiguous (e.g., change `inspect.py` to `xl_inspect.py` and delete the conflicting file).
- **Header row overwritten**: If the first data row appears as headers, check your row offset — data should start at row 2, not row 1.
- **Column name mismatch**: Check exact column names against task requirements (case-sensitive, no extra spaces).
- **Data type issues**: Confirm integers are integers (not floats like 1.0), strings are strings (not NaN).
- **Sheet names mismatch**: Verify sheet names exactly: "RawData", "Formatted Data", "Summary".
- **Missing reference data**: If business rules seem missing, check for additional sheets beyond the active one (common with SLA audits).
- **pandas shows NaN but Excel is correct**: When verifying Error Summary columns, pandas readback may display NaN for cells that actually contain the string "None". This is a pandas type inference artifact. **Always verify with openpyxl** to see actual cell values. If openpyxl shows "None" strings, the output is correct regardless of what pandas displays.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs:
- **DO NOT**: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`
- **DO**: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

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

### service-queue-sla-audit
- Load SLA Rules from separate sheet as lookup dict keyed by Priority Tier.
- SLA Breach = 1 if Open Age Hours > Max Hours for that priority tier.
- Missing Escalation = 1 if Escalation Required = 'Y' and Escalation Code is blank/None.
- Summary aggregates by (Queue, Region) and filters to groups with Total Errors > 0.
- Include Grand Total row after filtering.

### timesheet-policy-audit
- Load BreakRules from separate sheet as lookup dict keyed by Role with fields: Min Break Minutes, Overtime Threshold.
- Break Deficit = 1 if Break Minutes < Min Break Minutes for that role.
- Approval Missing = 1 if Hours Worked > Overtime Threshold for that role AND (Approval Code is None OR empty string).
- Summary aggregates by (Employee ID, Week Ending) and filters to groups with Total Errors > 0.
- Include Grand Total row after filtering.

### returns-disposition-audit
- Input spans **multiple Excel files**: Plan.xlsx, Event_Log.xlsx, Alias.xlsx
- Build alias map: case-insensitive lookup `{alias.lower(): standard}`
- Filter events to COMPLETED status only; dedupe by selecting latest Event Time per (Return ID, Line ID)
- For each plan row: if key not in event lookup → Missing Final Event=1; else normalize via alias map and compare to Planned Disposition for Mismatch flag
- Aggregate by (Warehouse, Carrier) and filter to error groups only

### manifest-scan-audit
- Join manifest/plan data to scan/event log by (Shipment ID, Carton ID) or equivalent key.
- Filter events to qualifying status only (typically `LOADED` or `COMPLETED`).
- Select latest event per key when multiple events exist (compare timestamps).
- Missing Event flag = 1 if no qualifying event found for manifest line.
- Mismatch flag = 1 if event value (e.g., scanned zone) differs from planned value.
- Summary groups by (Route, Shipment ID) or task-specified keys; filter to Total Errors > 0.
- Preserve any existing sheets (e.g., `Overview`) in the output workbook.

## Script Usage
- Execute `scripts/generate_audit.py` via shell when the task requires generating an audit workbook and executive brief.
- For multi-sheet sources with reference data, adapt the `load_reference_rules()` pattern in the script.
- If modifications are extensive, copy the script pattern into a new task-specific file rather than editing the shared template in place.
