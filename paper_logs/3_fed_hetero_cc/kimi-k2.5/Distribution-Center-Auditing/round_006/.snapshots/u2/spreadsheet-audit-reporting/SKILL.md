---
name: spreadsheet-audit-reporting
description: Use when tasked with reading tabular data from Excel, computing derived metrics (variances, flags, error counts), and producing a multi-sheet audit workbook alongside an executive Word brief. Covers openpyxl and python-docx workflows. Trigger phrases include 'audit', 'exception report', 'compliance check', 'promotional register', 'detention', 'receiving', 'returns disposition', 'SLA', 'service queue', 'threshold violation', 'timesheet', 'break deficit', 'overtime approval', 'policy compliance'.
---

# Spreadsheet Audit & Report Generation

## Workflow
1. **Install dependencies**: `pip install openpyxl python-docx` (use `--break-system-packages` if externally-managed environment error occurs)
2. **Inspect source data**: Load the source `.xlsx`, print sheet names, headers, and 3-5 sample rows to confirm column names and data types.
3. **Load reference rules (if present)**: Many audits include a separate rules sheet (e.g., `SLA_Rules`, `Thresholds`, `BreakRules`, `Disposition_Alias`). Load this into a lookup dict keyed by the grouping field (e.g., `Priority Tier`, `Role`, alias mapping).
4. **Compute derived metrics**:
   - Calculate variances (e.g., `Expected - Received`).
   - Flag categorical errors (e.g., `Temp Status != 'OK'`).
   - Date range errors (e.g., `Sale Date < Promo Start Date` or `Sale Date > Promo End Date`).
   - Threshold breaches: Compare value against rules lookup (e.g., `Open Age Hours > sla_rules[Priority Tier]['Max Open Hours']`).
   - Missing required fields: Check if escalation-required tiers lack escalation codes.
   - Role-based compliance: Check break minimums and overtime thresholds per role (e.g., `Break Minutes < break_rules[Role]['Min Break']` when `Hours Worked > break_rules[Role]['OT Threshold']`).
   - **Disposition matching**: Normalize aliases (case-insensitive) when comparing planned vs actual disposition. See `references/computed-column-examples.md` for alias normalization pattern.
   - **Missing event detection**: For composite keys (Return ID + Line ID), check absence of COMPLETED status in event log.
   - Aggregate totals per grouping key (e.g., Item Code + Supplier, SKU + Store ID, Queue + Region, Employee ID + Week Ending, Warehouse + Carrier).
5. **Generate audit workbook**:
   - Create `RawData` sheet: exact copy of source rows.
   - Create `Formatted Data` sheet: source columns + computed columns.
   - Create `Summary` sheet: aggregated counts/totals + Grand Total row.
   - **CRITICAL**: `openpyxl.Workbook()` initializes with a default `'Sheet'`. Delete it immediately: `del wb['Sheet']` before saving.
6. **Generate executive brief**: Use `python-docx` to write definitions, totals, high-priority items, and recommendations.
7. **Verify outputs**: Reload both files. Confirm sheet names, row counts (header + data), column headers, and that summary totals match row-level sums. Run a quick inline Python verification script before finalizing.

## Anti-Patterns & Troubleshooting

### None vs "None" String (Critical)
Python `None` writes as an empty Excel cell, not the text "None":

**Wrong**:
```python
df['Error Summary'] = None  # Results in empty cell
```

**Correct**:
```python
df['Error Summary'] = "None"  # Explicit string for literal "None" text
```

- Pandas displays string "None" as NaN; verify with openpyxl `values_only=True` to see actual cell values.
- When the task requires literal "None" text in output, always use the string `"None"`.
- **Note**: openpyxl converts empty strings `''` to `None` on save/load. This is expected behavior; do not attempt to force empty string persistence.

### python-docx Style Type Mismatch (Critical)
When adding styled runs to paragraphs, do not use paragraph styles for character runs:

**Wrong**:
```python
run = paragraph.add_run("text", style="Heading 1")  # Heading 1 is PARAGRAPH type
```

**Correct**:
```python
run = paragraph.add_run("text")
run.bold = True  # Set character formatting directly
# OR use a character style if available
run = paragraph.add_run("text", style="Emphasis")  # CHARACTER type only
```

Error message to recognize: `ValueError: assigned style is type PARAGRAPH (1), need type CHARACTER (2)`

### Extra Default Sheet
Always remove or rename the default sheet created by `openpyxl.Workbook()`. Failing to do so leaves an empty `'Sheet'` in the output.

### Multi-key Aggregation & Sorting
- Group rows using composite keys: `groups[(row['Carrier'], row['Yard'])] += 1` or `groups[(row['SKU'], row['Store ID'])] += 1` or `groups[(row['Queue'], row['Region'])] += 1` or `groups[(row['Employee ID'], row['Week Ending'])] += 1` or `groups[(row['Warehouse'], row['Carrier'])] += 1`
- Sort summary rows explicitly before writing: `sorted(groups.items(), key=lambda x: (x[0][0], x[0][1]))`
- Always append a "Grand Total" row at the end that sums all detail rows.
- For promo audits: filter Summary to rows with `Total Errors > 0` before writing.
- For timesheet audits: include all employee-week groups with errors, sorted by Employee ID then Week Ending.

### Mismatched Totals
Always cross-check `Summary` grand totals against the sum of detail rows. If they differ, check for off-by-one errors in aggregation loops or missing `else` branches in flag logic.

### Aggregation Type Mismatch & Indexing
When aggregating error counts or totals, ensure you are summing numeric columns, not adjacent string columns (e.g., `Error Summary`). Off-by-one indexing in loops or `ws.cell()` calls frequently triggers `TypeError: unsupported operand type(s) for +=: 'int' and 'str'`.
- **Fix**: Explicitly map column names to indices once at the start: `col_idx = {name: i+1 for i, name in enumerate(headers)}`.
- **Verify**: Print types of the first row's aggregation targets before entering the loop.

### Header Drift
When copying source data, explicitly map columns by header name rather than index to avoid silent misalignment if source layout changes.

### Column Name Whitespace (Critical for Detention Audits)
Excel headers may contain leading/trailing whitespace (e.g., `' Yard'` instead of `'Yard'`). Strip immediately after loading:

```python
df.columns = [col.strip() for col in df.columns]  # Do this before ANY column access
```

Failure to strip causes `KeyError` in groupby operations.

### Rules Sheet Lookup Errors
When thresholds come from a separate rules sheet:
- Verify all keys in the data exist in the rules dict before lookup.
- Handle case sensitivity: normalize keys (e.g., `tier.strip().upper()`, `role.strip().title()`).
- Default safely if a rule is missing, or flag as data quality issue.
- For timesheet audits: roles may be mixed case; normalize to match rules sheet keys.
- For disposition audits: load alias mappings and normalize both planned and actual dispositions to canonical values before comparison.

### Word Formatting
Use `python-docx` paragraph and run styling directly. Avoid converting Markdown/HTML to DOCX unless explicitly required; direct API usage yields cleaner, more predictable results.

### Package Installation in Managed Environments
If `pip install` fails with "externally-managed-environment", retry with `--break-system-packages` flag.

## Output Precision
Never round or truncate numeric values in outputs. Pass raw floats to Excel cells. The verifier's tolerance decides acceptable precision; give it full precision.

## References

- `references/computed-column-examples.md`: Detention Overrun, Seal Error, Price Error, Window Error, SLA Breach, Missing Escalation, Break Deficit, Approval Missing, Disposition Mismatch, Missing Final Event patterns, and aggregation examples.

## Known Invariants (by Sub-task)

### harbor-receiving-exception-audit
- 3 sheets: `RawData`, `Formatted Data`, `Summary`. No extra `'Sheet'`.
- Error Summary uses literal `"None"` string for clean rows.
- Grand Total uses `'-'` placeholder for secondary grouping key.

### harbor-trailer-detention-audit
- Strip column names before any operations (headers may have whitespace).
- Seal Error: check `pd.isna(Seal Status)` when Seal Required='NO'.
- Summary grouped by (Carrier, Yard), Grand Total uses `'-'` for Yard.

### harbor-returns-disposition-audit
- 3 sheets: `RawData`, `Formatted Data`, `Summary`. No extra `'Sheet'`.
- Load `Disposition_Alias` sheet into normalized mapping (lowercase input → uppercase canonical).
- Missing Final Event: No COMPLETED event exists for (Return ID, Line ID) composite key.
- Disposition Mismatch: Normalized planned disposition != normalized actual disposition.
- Summary grouped by (Warehouse, Carrier), include all groups with errors.
- Grand Total uses `'-'` for Carrier column.
- Error Summary: comma-separated error names or `"None"` string.

### promo-register-audit
- 3 sheets: `RawData`, `Formatted Data`, `Summary`. No extra `'Sheet'`.
- Price Error: `Register Price != Promo Price` (1 if error, 0 if match).
- Window Error: `Sale Date < Promo Start Date` or `Sale Date > Promo End Date`.
- Summary grouped by (SKU, Store ID), filtered to `Total Errors > 0`, sorted by SKU then Store ID.
- Grand Total uses `'-'` for Store ID column.
- Error Summary: comma-separated error names or `"None"` string.
- Executive brief: include plain-language definitions, totals, top 2 SKUs by exception count, and actionable recommendations.

### service-queue-sla-audit
- 3 sheets: `RawData`, `Formatted Data`, `Summary`. No extra `'Sheet'`.
- Load `SLA_Rules` sheet into dict keyed by `Priority Tier` with `Max Open Hours` and `Escalation Required`.
- SLA Breach: `Open Age Hours > sla_rules[Priority Tier]['Max Open Hours']`.
- Missing Escalation: `sla_rules[Priority Tier]['Escalation Required'] == 'Y'` AND (`Escalation Code` is None/empty).
- Summary grouped by (Queue, Region), include all groups with errors, Grand Total uses `'-'` for Region.
- Error Summary: comma-separated error names or `"None"` string.

### timesheet-policy-audit
- 3 sheets: `RawData`, `Formatted Data`, `Summary`. No extra `'Sheet'`.
- Load `BreakRules` sheet into dict keyed by `Role` with `Min Break Minutes` and `OT Threshold Hours`.
- Break Deficit: `Break Minutes < break_rules[Role]['Min Break Minutes']` AND `Hours Worked > break_rules[Role]['OT Threshold Hours']`.
- Approval Missing: `Hours Worked > break_rules[Role]['OT Threshold Hours']` AND (`Approval Code` is None/empty).
- Summary grouped by (Employee ID, Week Ending), include all groups with errors, sorted by Employee ID then Week Ending.
- Grand Total uses `'-'` for Week Ending column.
- Error Summary: comma-separated error names (`'Break Deficit'`, `'Approval Missing'`) or `"None"` string.
- Executive brief: include plain-language definitions of compliance checks, totals, top employees by exception count, and actionable recommendations.

## Validation Checklist
- [ ] Source headers match expected names (after stripping whitespace).
- [ ] Rules sheet (if present) loads without KeyError; all priority tiers/roles/aliases mapped.
- [ ] Output workbook contains exactly the required sheets (no default `'Sheet'`).
- [ ] `Formatted Data` row count matches `RawData`.
- [ ] `Summary` grand total equals sum of detail rows.
- [ ] Word brief contains all required sections (definitions, totals, top items, recommendations).
