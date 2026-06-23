---
name: production-planning
description: Create multi-scenario production planning workbooks with date-based scheduling, capacity constraints, and formula-driven calculations. Use for manufacturing recovery plans, resource allocation scenarios, or any task requiring multiple 'what-if' sheets with shared structure but varying parameters. Triggered by requirements involving date ranges, daily production tracking, cumulative calculations, weekend/holiday exclusions, and scenario comparison.
---

# Multi-Scenario Production Planning in Excel

## STOP — Read This First

**Never use pandas for Excel files that require formulas.** Pandas writes values only; formulas become static values or NaN when re-read. Use `openpyxl` directly for all formula columns.

**Never hardcode column indices.** Define a `COLUMN_MAP` dictionary and reference columns by semantic name.

## Quick Start

```python
from openpyxl import Workbook
from datetime import datetime, timedelta

wb = Workbook()

# Remove default sheet, create scenario sheets
wb.remove(wb.active)
for scenario_name in ['Scenario A', 'Scenario B']:
    ws = wb.create_sheet(scenario_name)
    build_scenario(ws, scenario_config)

wb.save('output.xlsx')
```

## Workflow

1. **Parse Requirements First**: Identify exact output format requirements before building:
   - Sheet names (exact spelling)
   - Column headers (exact text, case-sensitive)
   - Date ranges and holiday lists
   - Capacity constraints per product/scenario
   - Expected on-time status format

2. **Define Schema**: Create a `COLUMN_MAP` dict mapping semantic names to 1-based column indices

3. **Build Header Rows**: Static labels in rows 1-3, data starts row 4

4. **Generate Date Column**: Actual `datetime` values, not formulas

5. **Apply Production Logic**: Weekends/holidays → 0 production; working days → capacity

6. **Write Formulas**: Cumulative columns use Excel formulas (e.g., `=E4+C5-D5`)

7. **Validate Structure**: Check row count, column count, formula presence

8. **Verify Against Expected Output**: Before finalizing, cross-check against explicit task requirements to prevent self-verification false positives.

## Column Schema Pattern

```python
COLUMN_MAP = {
    'date': 2,           # B
    'prod_web': 3,       # C - Planned Production
    'po_web': 4,         # D - Purchase Orders Due
    'cumul_web': 5,      # E - Cumulative (FORMULA)
    'prod_db': 6,        # F
    'po_db': 7,          # G
    'cumul_db': 8,       # H - Cumulative (FORMULA)
    'notes': 11,         # K
}
```

Access via: `ws.cell(row=r, column=COLUMN_MAP['date'], value=date_obj)`

## Date Handling

**Always use actual datetime values**, not formulas like `=B4+1`:

```python
current_date = datetime(2018, 1, 22)
for row in range(4, 104):  # 100 days
    ws.cell(row=row, column=COLUMN_MAP['date'], value=current_date)
    current_date += timedelta(days=1)
```

**Identify weekends/holidays** for zero-production rules:

```python
import calendar

def is_working_day(dt):
    return dt.weekday() < 5  # Mon=0, Fri=4, Sat=5, Sun=6
    # Add holiday exclusion if needed
```

## Formula Patterns

Cumulative calculation (previous end + today's production - today's POs):

```python
# Row 4 (first data row): starts with initial value or simple formula
ws.cell(row=4, column=COLUMN_MAP['cumul_web'], value='=C4-D4')

# Row 5+: references previous row's cumulative
for row in range(5, max_row + 1):
    formula = f'=E{row-1}+C{row}-D{row}'  # prev_cumul + prod - po_due
    ws.cell(row=row, column=COLUMN_MAP['cumul_web'], value=formula)
```

## Scenario Configuration

Extract scenario-specific parameters into a config dict:

```python
SCENARIOS = {
    'current_capacity': {
        'db_start_date': datetime(2018, 3, 1),
        'network_min_total': 1200,
        'network_before_feb1': None,  # No special constraint
    },
    'relocated_network': {
        'db_start_date': datetime(2018, 2, 20),
        'network_min_total': 100,
        'network_before_feb1': 100,   # Must produce 100 before Feb 1
        'network_after_feb1': 0,      # Zero after Feb 1
    }
}
```

## Production Calculation Logic

```python
def get_daily_production(date_obj, product_type, scenario_config):
    """Return production quantity for a given date and product."""
    if not is_working_day(date_obj):
        return 0

    # Check product-specific start dates
    if date_obj < scenario_config.get(f'{product_type}_start_date', datetime.min):
        return 0

    # Apply capacity rules (may vary by date range)
    if date_obj < datetime(2018, 2, 5):
        return 120
    elif scenario_config.get('ten_hour_shifts') and date_obj >= datetime(2018, 2, 1):
        return 170  # 10-hour shift capacity
    else:
        return 135
```

## Validation Checklist

Run before saving and after loading:

```python
def validate_workbook(filepath, expected_scenarios):
    from openpyxl import load_workbook
    wb = load_workbook(filepath, data_only=False)  # Keep formulas

    assert set(wb.sheetnames) == set(expected_scenarios)

    for sheet_name in expected_scenarios:
        ws = wb[sheet_name]
        assert ws.max_row == 103, f"{sheet_name}: expected 103 rows, got {ws.max_row}"

        # Check first and last dates
        first_date = ws.cell(row=4, column=2).value
        last_date = ws.cell(row=103, column=2).value
        assert isinstance(first_date, datetime), f"{sheet_name}: B4 should be datetime"

        # Check formula presence (not evaluated value)
        cumul_cell = ws.cell(row=5, column=5)  # E5
        assert isinstance(cumul_cell.value, str) and cumul_cell.value.startswith('='), \
            f"{sheet_name}: E5 should be formula, got {cumul_cell.value}"

    return True
```

## Anti-Patterns

- **Don't** use `df.to_excel()` when formulas are required
- **Don't** use date formulas like `=B4+1` — write actual datetime values
- **Don't** hardcode column letters (B, C, D) — use `COLUMN_MAP` with 1-based indices
- **Don't** assume pandas can read back what openpyxl writes with formulas — use `data_only=False` for validation
- **Don't** mix value types in formula columns — entire column must be formulas or values, not mixed
- **Don't** assume self-verification passes mean format is correct — cross-check against explicit task requirements first

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### server-provisioning-recovery
- Output must have 3 scenario sheets with exact names from task
- Headers must be in rows 1-3, data starts row 4
- Date column must contain actual datetime objects, not formulas
- Cumulative columns must be Excel formulas (e.g., `=E4+C5-D5`)
- Weekend/holiday dates must have production = 0
- Verify formula presence by checking cell value starts with `=`

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ValueError: Length mismatch` | Pandas reading formula cells as NaN | Use `openpyxl` directly, not pandas |
| Dates show as integers | Excel serial date format | Pass `datetime` objects, not strings |
| Formulas appear as text | Cell typed as string | Pass formula string starting with `=` |
| Formulas evaluate to 0 on re-read | Pandas `data_only=True` default | Use `load_workbook(data_only=False)` |
| Weekend production not zero | Wrong weekday logic | `weekday() < 5` for Mon-Fri |
| Cumulative wrong after row 1 | Formula references off-by-one | Check `row-1` indexing in formulas |
| Self-checks pass but verifier fails | Output format mismatch | Compare output byte-by-byte with expected format |
| Header text rejected | Typo or wrong phrasing | Copy headers verbatim from task requirements |
| On-time status wrong | Cumulative calculation error | Verify end-of-period cumulative PO value |

## Fallback: pandas for Value-Only Output

If formulas are NOT required and you need quick value export:

```python
import pandas as pd
# Only for static value output, not formula preservation
df.to_excel('output.xlsx', sheet_name='Plan', index=False)
```

See `references/scenario_templates.md` for complete scenario configuration examples.