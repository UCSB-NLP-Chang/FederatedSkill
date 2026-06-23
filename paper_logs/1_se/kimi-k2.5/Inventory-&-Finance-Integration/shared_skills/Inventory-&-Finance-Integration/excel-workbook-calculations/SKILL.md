---
name: excel-workbook-calculations
description: Build calculated Excel workbooks with pandas/openpyxl. Use when generating output workbooks with derived columns, multiple sheets, metadata headers, date calculations, staffing/resource planning calculations, parts/inventory resupply planning, round-up pallet/crate logic, financial/capacity reconciliations, OR media rights/intangible asset rollforwards with multi-program aggregation (e.g., Film + Music rights). Covers Harbor-style single-program reconciliations, Transit-style multi-program reconciliations (Bus+Rail), and Media Rights rollforwards (Film+Music) with formula-linked detail and summary sheets.
---

# Excel Workbook Calculations

Build calculated Excel workbooks with pandas and openpyxl.

## When to Use

- Generating output workbooks with derived columns (DOH, OOS projections, pallet/crate calculations, staffing calculations)
- Creating multiple sheets with filtered views of calculated data
- Writing metadata headers (AsOfDate, PlanningHorizonEnd, etc.) before data
- Calculating date-based business metrics with round-up logic
- Resource planning: coverage projections, demand calculations, shift/inventory planning
- **Parts/inventory resupply planning**: stockout projections, inbound delivery filtering, crate-based rounding
- **Reconciliation workbooks**: Detail sheets with Month Totals/Ending Balance/Variance/GL Balance control rows, summary sheets with cross-sheet formula links, capacity/financial reconciliations
- **Transit subsidy rollforwards**: Multi-program reconciliation (Bus + Rail) with GL balance aggregation across programs
- **Media rights/intangible asset rollforwards**: Multi-program reconciliation (Film + Music rights, or similar asset pairs) following identical pattern to transit subsidy

## Workflow

1. **Install dependencies**: `pip install pandas openpyxl --break-system-packages` (if externally-managed environment)
2. **Read source data**: Use `pd.read_excel(path, sheet_name=..., skiprows=..., nrows=...)` for non-standard layouts
3. **Extract metadata**: Read header rows separately with explicit column indexing; use direct cell access or regex for date strings
4. **Calculate derived fields**: Vectorized pandas operations, `np.ceil()` for round-up logic
5. **Write output**: Use `ExcelWriter` with `openpyxl` engine; write metadata rows first, then data; **convert numpy/pandas scalars to native Python types explicitly**

## Critical Patterns

### Reading Non-Standard Excel Layouts

Common layout: Row 0 has metadata, row 1 is empty, row 2 has headers, data starts row 3.

```python
# Read just the header/metadata section
header_rows = pd.read_excel(source_file, sheet_name='Sheet1', nrows=2, header=None)
asof_date = header_rows.iloc[0, 1]  # Extract from known cell position

# Read actual data with skiprows, using row 2 as headers
df = pd.read_excel(source_file, sheet_name='Sheet1', skiprows=2)
```

### Date Extraction (Strings vs Datetimes)

Dates often read as strings in irregular layouts. Parse explicitly:

```python
from datetime import datetime

# If already datetime/Timestamp
if hasattr(asof_date, 'date'):
    asof_date = asof_date.date()
else:
    # Parse from string: "2025-08-05" or "2025-08-05 00:00:00"
    asof_date = datetime.strptime(str(asof_date)[:10], '%Y-%m-%d').date()
```

### Staffing/Resource Planning Calculations

See `references/staffing-calculations.md` for detailed formulas.

```python
import numpy as np
from datetime import timedelta

# Coverage projections
coverage_days = current_hours / daily_required
projected_understaff_date = asof_date + timedelta(days=int(coverage_days))

# Demand calculation
remaining_days = (planning_horizon_end - asof_date).days
remaining_demand = daily_required * remaining_days
additional_needed = max(0, remaining_demand - current_hours - incoming_hours)

# Shift blocks with round-up
shift_blocks = int(np.ceil(additional_needed / hours_per_block))
```

### Parts/Inventory Resupply Calculations

See `references/parts-resupply-calculations.md` for detailed formulas.

```python
import numpy as np
from datetime import timedelta

# Days on hand / coverage
current_doh = current_units / daily_consumption
projected_stockout = asof_date + timedelta(days=int(current_doh))

# Filter inbound deliveries within planning horizon
inbound_by_horizon = df_deliveries[
    (df_deliveries['Part_Code'] == part_code) &
    (df_deliveries['Delivery Date'] <= planning_horizon_end)
]
inbound_units = inbound_by_horizon['Units'].sum()
earliest_scheduled = inbound_by_horizon['Delivery Date'].min() if len(inbound_by_horizon) > 0 else None

# Remaining period demand
remaining_days = (planning_horizon_end - asof_date).days
remaining_demand = daily_consumption * remaining_days

# Additional units needed after current stock + inbound
additional_units = max(0, remaining_demand - current_units - inbound_units)

# Crate-based rounding (use np.ceil for round-up)
crates_required = int(np.ceil(additional_units / units_per_crate))

# Delivery timing analysis
required_delivery_date = projected_stockout
earlier_delivery_required = (
    earliest_scheduled > required_delivery_date 
    if earliest_scheduled and required_delivery_date 
    else False
)
```

### Reconciliation Workbooks with Linked Formulas

See `references/reconciliation-workbooks.md` for Harbor (single-program) pattern.

**Control Row Structure** (place below data):
```python
# Row 13: Month Totals
ws['B13'] = '=SUM(B7:B12)'
# Row 14: Ending Balance (links to totals)
ws['B14'] = '=B13'
# Row 15: Variance (Ending Balance - GL Balance)
ws['B15'] = '=B14-B16'
# Row 16: GL Balance (static from source data)
ws['B16'] = 108621.55  # From JSON/verified source
```

**Cross-Sheet Summary References**:
```python
# Reference detail sheet control row in summary
ws['B7'] = "='Compute Pool #8100'!O13"   # Month Totals
ws['B9'] = "='Compute Pool #8100'!O15"   # Variance
# Combined total aggregates variances
ws['B16'] = '=B9+B14'
```

**Verification**: Load with `data_only=False` to check formulas exist; `data_only=True` returns cached values (often None before Excel calculates).

### Multi-Program Reconciliation (Transit Subsidy OR Media Rights)

See `references/transit-subsidy-rollforward.md` for complete pattern. **Same structure applies to Film+Music rights, Harbor+Storage, or any paired asset reconciliation.**

**Key differences from single-program**:
- Summary GL Balance row links to detail sheets via formulas (not static values)
- Month Totals aggregates across programs: `=B7+B8`
- Total Ending formula: `=B9+B14` (month totals + GL balance)

```python
# GL Balance references detail sheets
ws_summary['B14'] = "='Bus Program #4310'!B16+'Rail Program #4320'!B16"  # Jan
ws_summary['E14'] = "='Bus Program #4310'!E16+'Rail Program #4320'!E16"  # Feb
# ... etc for each month
```

### Writing Metadata + Data with Proper Boolean Handling

**Critical**: `dataframe_to_rows` produces numpy types; convert explicitly.

```python
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows

wb = Workbook()
ws = wb.active
ws.title = 'Results'

# Write metadata rows
ws['A1'] = 'Field'
ws['B1'] = 'Value'
ws['A2'] = 'AsOfDate'
ws['B2'] = asof_date.isoformat()

# Write data starting at row 6
for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), 6):
    for c_idx, value in enumerate(row, 1):
        # CRITICAL: Convert numpy/pandas types to native Python
        if hasattr(value, 'item'):  # numpy scalar
            value = value.item()
        elif isinstance(value, pd.Timestamp):
            value = value.date().isoformat()
        # Explicit bool conversion prevents integer coercion
        elif isinstance(value, (np.bool_, pd.BooleanDtype)):
            value = bool(value)
        ws.cell(row=r_idx, column=c_idx, value=value)
```

### Filtering to Secondary Sheets

```python
# Create filtered view sheet - only items needing resupply
mask = df['Crates_Required_Rounded_Up'] > 0
df_filtered = df[mask][['Part_Code', 'Required_Delivery_Date', 'Crates_Required_Rounded_Up']]
```

## Anti-Patterns to Avoid

- **Don't** pass `sheets` param to Read tool (not supported)
- **Don't** use `pd.to_datetime()` on cells containing text like "Today's Date" - parse explicitly
- **Don't** assume `python` exists; use `python3` in shell commands
- **Don't** rely on automatic date parsing when source has mixed types (strings + datetimes)
- **Don't** install packages without `--break-system-packages` in Debian/Ubuntu containers
- **Don't** write booleans directly from DataFrames - they become 0/1 integers. Use explicit `bool()` conversion.
- **Don't** use `skiprows=3` when headers are in row 2; use `skiprows=2` to make row 2 the header
- **Don't** forget to filter inbound deliveries to only those within the planning horizon before summing
- **Don't** use `min()` on an empty series for earliest scheduled delivery; check `len()` first
- **Don't** calculate reconciliation variances in Python; use Excel formulas for auditability
- **Don't** verify formulas with `data_only=True`; it returns None for uncalculated formulas
- **Don't** place GL balances as static values in multi-program summaries; link to detail sheets
- **Don't** forget quotes around sheet names with spaces/hashes in cross-sheet references
- **Don't** hardcode control row positions without checking data row count; calculate dynamically: `control_start = 7 + len(df) + 1`

## Validation Steps

1. Verify sheet names match requirements
2. Check metadata values extract correctly before calculations
3. Confirm date outputs are ISO format strings or native Excel dates
4. **Verify boolean columns use native Excel booleans (True/False), not integers (0/1)**
5. Round-up calculations use `np.ceil()` or integer math, not round()
6. Check filtered secondary sheets contain expected rows
7. Verify None/NaN handling in date columns (write as None, not "NaT" or "nan")
8. **For parts resupply**: Verify inbound filtering excludes deliveries after planning horizon
9. **For parts resupply**: Check that `earlier_delivery_required` correctly handles `None` earliest scheduled dates
10. **For reconciliation workbooks**: Verify formulas are strings starting with `=`, not calculated values
11. **For reconciliation workbooks**: Load with `data_only=False` and print `.value` to confirm formulas exist
12. **For multi-program reconciliations**: Verify summary GL balances link to detail sheets, not static values
13. **For multi-program reconciliations**: Verify control row positions match expected verifier layout (calculate dynamically from data length)

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `DateParseError: Unknown datetime string format` | Parsing text headers as dates | Extract with regex or index into cell position |
| `ModuleNotFoundError: No module named 'pandas'` | Package not installed | `pip install pandas openpyxl --break-system-packages` |
| `externally-managed-environment` | PEP 668 restriction | Use `--break-system-packages` or create venv |
| `PlanningHorizonEnd` shows wrong date | Parsing text description cell | Read raw header rows, extract from column index, not regex on wrong cell |
| Empty calculated columns | Formula references wrong DataFrame | Verify column names after skiprows read |
| Booleans appear as 0/1 in Excel | NumPy boolean types coerced | Explicit `bool(value)` before writing to cell |
| `TypeError: unsupported operand type(s) for -: 'str' and 'str'` | Dates read as strings, not dates | Parse with `datetime.strptime()` or check `hasattr(value, 'date')` |
| `TypeError: '>' not supported between instances of 'str' and 'int'` | Header row included in data | Check `skiprows` matches actual header position |
| `ValueError: cannot convert float NaN to integer` | NaN passed to `int()` | Check `pd.notna()` before conversion or use `0 if pd.isna(x) else int(x)` |
| Parts show negative additional units | Logic error in max(0, ...) | Ensure `max(0, remaining - current - inbound)` pattern |
| Formulas show as None when read back | Used `data_only=True` | Load with `data_only=False` to verify formula strings |
| `#REF!` in Excel cells | Sheet name changed or wrong in formula | Verify sheet names match exactly, quote if contains spaces |
| Multi-program summary shows wrong GL totals | Static values instead of linked formulas | Link summary GL row to detail sheets: `='Sheet'!B16+'Sheet2'!B16` |
| Control rows at wrong position | Hardcoded row numbers | Calculate: `control_start = first_data_row + len(df) + 1` |

## See Also

- `references/date-handling.md` - Detailed date extraction patterns
- `references/staffing-calculations.md` - Coverage projection and shift planning formulas
- `references/parts-resupply-calculations.md` - Parts inventory, DOH, crate rounding, delivery timing
- `references/reconciliation-workbooks.md` - Formula-linked detail/summary sheets, control rows
- `references/transit-subsidy-rollforward.md` - Multi-program reconciliation (Bus + Rail, Film + Music, etc.)
- `scripts/pallet_calculations.py` - Reusable round-up pallet/crate logic
- `scripts/excel_writer.py` - Template for multi-sheet output with metadata
- `scripts/reconciliation_template.py` - Template for reconciliation workbooks with linked formulas
