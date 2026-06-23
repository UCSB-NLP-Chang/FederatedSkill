---
name: excel-audit-reporting
description: Generate multi-sheet Excel audit workbooks with calculated exception columns, summary aggregations, and companion Word briefs. Use when tasks require analyzing tabular data for errors/variance, creating audit trails with raw+formatted+summary views, or producing executive summaries alongside detailed data. Works for logistics, financial, compliance, HR/timesheet, or any domain with rule-based exception detection. Also covers event-log reconciliation patterns where multiple events per entity must be filtered to latest status before comparison.
---

# Excel Audit Reporting

Generate professional audit deliverables: a multi-sheet Excel workbook with raw data, calculated exception columns, and summary aggregations, plus a Word executive brief.

## Workflow

1. **Read source data**: Use Python with `pandas` + `openpyxl`. The `Read` tool cannot process binary `.xlsx` files.
2. **Define exception rules**: Identify boolean conditions for each error type based on task-specific business rules.
3. **Calculate exception metrics**: Add boolean/numeric columns for each error type, a total errors column, and a human-readable error summary.
4. **Create summary aggregation**: Group by key dimensions, sum errors, sort, append Grand Total row.
5. **Build multi-sheet workbook**: RawData, Formatted Data, Summary.
6. **Generate Word brief**: Definitions, totals, high-priority items, recommendations.

## Installation

```bash
pip install pandas openpyxl python-docx --break-system-packages -q
```

## Key Patterns

### Exception Calculation (Configurable)

Replace column names and conditions based on your audit rules:

```python
# Example: Detention audit
df['Detention Overrun'] = (df['Actual Hold Hours'] > df['Allowed Hold Hours']).astype(int)

# Example: Seal compliance (multi-condition)
seal_required = df['Seal Required'] == 'YES'
seal_not_verified = ~df['Seal Status'].isin(['VERIFIED'])
df['Seal Error'] = (seal_required & seal_not_verified).astype(int)

# Totals and summary
df['Total Errors'] = df['Detention Overrun'] + df['Seal Error']

def make_summary(row):
    parts = []
    if row['Detention Overrun']: parts.append('Detention Overrun')
    if row['Seal Error']: parts.append('Seal Error')
    return ', '.join(parts) if parts else 'None'

df['Error Summary'] = df.apply(make_summary, axis=1)
```

### Event-Log Reconciliation (Latest Status Filter)

When auditing against event logs with multiple entries per item (scans, status changes), filter to the latest relevant event before comparison:

```python
# Filter to target status only, then get latest per entity
loaded_scans = scans[scans['Status'] == 'LOADED'].copy()
loaded_scans['Timestamp'] = pd.to_datetime(loaded_scans['Timestamp'])
latest_loaded = (loaded_scans
    .sort_values('Timestamp')
    .groupby(['Shipment ID', 'Carton ID'])
    .last()
    .reset_index())

# Left join to preserve all planned items
merged = manifest.merge(
    latest_loaded[['Shipment ID', 'Carton ID', 'Scanned Zone']],
    on=['Shipment ID', 'Carton ID'],
    how='left'
)

# Calculate exceptions
merged['Missing Load Scan'] = merged['Scanned Zone'].isna().astype(int)
merged['Zone Mismatch'] = (merged['Planned Zone'] != merged['Scanned Zone']).astype(int)
```

**Critical**: Use `how='left'` to ensure unprocessed items appear as errors, not dropped rows.

See `references/exception-patterns.md` for more domain examples including timesheet/HR patterns.

### Reference Table Joins (Threshold Rules)

When exception rules depend on role/category-specific thresholds stored in a separate sheet:

```python
# Load reference table (e.g., BreakRules, RateCards)
rules = pd.read_excel(input_path, sheet_name='BreakRules')

# Merge to bring threshold columns into main data
df = df.merge(rules[['Role', 'Min Break Minutes', 'Overtime Threshold']], 
              on='Role', how='left')

# Calculate exceptions using joined thresholds
df['Break Deficit'] = (df['Break Minutes'] < df['Min Break Minutes']).astype(int)
df['Approval Missing'] = ((df['Hours Worked'] > df['Overtime Threshold']) & 
                          df['Approval Code'].isna()).astype(int)
```

See `references/multi-source-reconciliation.md` for alias normalization patterns.

### Summary Aggregation

```python
summary = df.groupby(['Carrier', 'Yard']).agg({
    'Detention Overrun': 'sum',
    'Seal Error': 'sum', 
    'Total Errors': 'sum'
}).reset_index().sort_values(['Carrier', 'Yard'])

# Append Grand Total
totals = summary[['Detention Overrun', 'Seal Error', 'Total Errors']].sum()
grand_total = pd.DataFrame([{
    'Carrier': 'Grand Total', 'Yard': '-',
    **totals.to_dict()
}])
summary = pd.concat([summary, grand_total], ignore_index=True)
```

## Validation

### Critical: NaN vs "None" String

pandas reads the string `"None"` from Excel as NaN by default. **Always use** `keep_default_na=False` when re-reading:

```python
# WRONG - shows NaN for "None" cells
df = pd.read_excel(path, sheet_name='Formatted Data')

# CORRECT - preserves "None" as string
df = pd.read_excel(path, sheet_name='Formatted Data', keep_default_na=False)
```

To verify actual cell values without pandas interpretation:

```python
from openpyxl import load_workbook
wb = load_workbook(path)
ws = wb['Formatted Data']
values = [ws.cell(row=r, column=col_idx).value for r in range(2, 7)]
```

### Verify Excel Structure

```python
xl = pd.ExcelFile(path)
assert xl.sheet_names == ['RawData', 'Formatted Data', 'Summary']
```

### Verify Word Content

```python
from docx import Document
doc = Document(path)
text = '\n'.join([p.text for p in doc.paragraphs])
```

## Anti-Patterns

| Anti-Pattern | Why It Fails |
|-------------|--------------|
| Use `Read` tool on `.xlsx` | Tool rejects binary files |
| Trust pandas with 'None' values | Converts to NaN on re-read; use `keep_default_na=False` |
| Return empty string for no errors | Empty cells may be ambiguous; use explicit `"None"` string |
| Skip Grand Total row | Auditors expect it for verification |
| Omit RawData sheet | Breaks audit trail integrity |
| Hardcode column names in reusable code | Makes script brittle; pass as parameters |
| Trust pandas for ground-truth verification | pandas interprets data; use openpyxl to verify actual cell values |
| Use inner join for event reconciliation | Drops unprocessed items from audit scope; use left join |
| Take first event instead of latest | May use outdated status; always sort by timestamp and take last |
| Include all event statuses | PENDING/VOID events are not final; filter to target status first |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Install with `--break-system-packages` |
| `externally-managed-environment` | Use `--break-system-packages` or create venv |
| NaN where "None" expected | Use `keep_default_na=False` in `pd.read_excel` |
| Summary totals don't match detail | Check boolean columns cast to `int` before sum |
| Formula cells show as `None` | openpyxl reads formulas as `None` by default; use `data_only=True` if values needed |
| Error Summary shows blank instead of "None" | Ensure summary function returns `"None"` string, not empty string or None value |
| pandas shows NaN but cells look correct | pandas is interpreting; verify with openpyxl `load_workbook().cell().value` |
| Missing events not detected | Check left join used; verify status filter includes only final statuses |
| Duplicate rows in summary | Pre-aggregate events to latest per entity before merging |

## See Also

- `scripts/generate_audit_report.py` - Full working template with configurable columns
- `references/exception-patterns.md` - Domain-specific exception rule examples including timesheet/HR and event-log patterns
- `references/multi-source-reconciliation.md` - Multi-source reconciliation with alias normalization
