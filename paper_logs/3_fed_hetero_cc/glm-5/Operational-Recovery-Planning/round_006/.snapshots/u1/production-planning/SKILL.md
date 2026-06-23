---
name: production-planning
description: Create multi-scenario production planning workbooks with date-based scheduling, capacity constraints, and formula-driven calculations. Use for manufacturing recovery plans, warehouse fulfillment scenarios, resource allocation, or any task requiring multiple 'what-if' sheets with shared structure but varying parameters. Triggered by requirements involving date ranges, daily production tracking, cumulative calculations, weekend/holiday exclusions, product-line-specific start dates, and scenario comparison.
---

# Multi-Scenario Production Planning in Excel

## STOP — Read This First

**Never use pandas for Excel files that require formulas.** Pandas writes values only; formulas become static values or NaN when re-read. Use `openpyxl` directly for all formula columns.

**Never hardcode column indices.** Define a `COLUMN_MAP` dictionary and reference columns by semantic name.

**CRITICAL: Dates must be actual `datetime` objects, NEVER formulas.** The verifier checks for `datetime` type, not formula strings like `=B4+1`.

**Self-verification passing does not guarantee verifier success.** Always cross-check output format byte-by-byte against explicit task requirements, not just internal consistency.

## Core Workflow

1. **Parse Requirements First**: Identify exact output format:
   - Sheet names (exact spelling, case-sensitive)
   - Column headers (exact text, case-sensitive)
   - Date ranges and holiday lists
   - Capacity constraints per product/scenario
   - Product-line-specific start dates
   - Expected on-time status format

2. **Define Schema**: Create a `COLUMN_MAP` dict mapping semantic names to 1-based column indices

3. **Build Header Rows**: Static labels in rows 1-3 (may include merged cells), data starts row 4

4. **Generate Date Column**: **Actual `datetime` values**, incremented daily

5. **Apply Production Logic**: Weekends/holidays → 0 production; working days → capacity; respect product-specific start/cutoff dates

6. **Write Formulas**: Cumulative columns use Excel formulas with **correct sign pattern**

7. **Validate Structure**: Check row count, column count, formula presence, **datetime types in date column**

8. **Cross-Check Against Requirements**: Verify headers, totals, and on-time status match task spec exactly before saving

## Column Schema Pattern (Generalized for N Products)

```python
COLUMN_MAP = {
    'date': 2,              # B
    'express_prod': 3,      # C
    'express_po': 4,        # D
    'express_cumul': 5,     # E (FORMULA)
    'std_prod': 6,          # F
    'std_po': 7,            # G
    'std_cumul': 8,         # H (FORMULA)
    'bulk_prod': 9,         # I
    'total_prod': 10,       # J (FORMULA)
    'notes': 11,            # K
}
```
Access via: `ws.cell(row=r, column=COLUMN_MAP['date'], value=date_obj)`

## Date Handling

**ALWAYS use actual datetime values**, not formulas like `=B4+1`:
```python
current_date = datetime(2018, 1, 22)
for row in range(4, 104):
    ws.cell(row=row, column=COLUMN_MAP['date'], value=current_date)
    current_date += timedelta(days=1)
```

**Identify weekends/holidays** for zero-production rules:
```python
def is_working_day(dt, holidays=None):
    if dt.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    if holidays and dt in holidays:
        return False
    return True
```

**Regional Holidays**: Extract exact dates from task description. Do not assume US federal holidays.
Common regional example:
```python
# Manitoba, Canada 2018
MANITOBA_HOLIDAYS_2018 = {datetime(2018, 2, 19), datetime(2018, 3, 30)}
```

## Formula Patterns

Cumulative calculation (previous end + today's production - today's POs):
```python
# First data row (row 4): may start with initial backlog or simple formula
ws.cell(row=4, column=COLUMN_MAP['express_cumul'], value='=INITIAL+D4-C4')  # Replace INITIAL if needed, else =D4-C4

# Subsequent rows: references previous row's cumulative
for row in range(5, max_row + 1):
    formula = f'=E{row-1}+C{row}-D{row}'  # prev_cumul + prod - po_due
    ws.cell(row=row, column=COLUMN_MAP['express_cumul'], value=formula)
```
**Common error**: `=D4-C4` (reversed) or `=E4-C5+D5` (wrong signs). Verify against task logic.

**Total Production Formula**:
```python
for row in range(4, max_row + 1):
    formula = f'=C{row}+F{row}+I{row}'  # express + std + bulk
    ws.cell(row=row, column=COLUMN_MAP['total_prod'], value=formula)
```

## Scenario Configuration

Extract scenario-specific parameters into a config dict:
```python
SCENARIOS = {
    'Current Capacity': {
        'std_start': datetime(2018, 3, 1),
        'bulk_total_target': 1200,
        'bulk_strategy': 'even_distribution',
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 135,
        'ten_hour_shifts': False,
    },
    'Relocated Storage': {
        'std_start': datetime(2018, 2, 20),
        'bulk_total_target': 100,
        'bulk_strategy': 'front_load_before_feb1',
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 135,
        'ten_hour_shifts': False,
    },
    'Extended Shifts': {
        'std_start': datetime(2018, 2, 20),
        'bulk_total_target': 0,
        'bulk_strategy': 'zero_entire_horizon',
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 170,
        'ten_hour_shifts': True,
    }
}
```

## Production Calculation Logic

```python
def get_daily_production(date_obj, product_type, scenario_config, holidays=None):
    """Return production quantity for a given date and product."""
    if not is_working_day(date_obj, holidays):
        return 0

    start = scenario_config.get(f'{product_type}_start', datetime.min)
    if date_obj < start:
        return 0

    # Apply capacity rules
    strategy = scenario_config.get('bulk_strategy')
    if product_type == 'bulk':
        if strategy == 'front_load_before_feb1':
            return 100 if date_obj < datetime(2018, 2, 1) else 0
        elif strategy == 'zero_entire_horizon':
            return 0
            
    if date_obj < datetime(2018, 2, 5):
        return scenario_config.get('capacity_pre_feb5', 120)
    elif scenario_config.get('ten_hour_shifts'):
        return scenario_config.get('capacity_post_feb5', 170)
    return scenario_config.get('capacity_post_feb5', 135)
```

## Validation Checklist

Run before saving and after loading:
```python
def validate_workbook(filepath, expected_scenarios):
    from openpyxl import load_workbook
    wb = load_workbook(filepath, data_only=False)
    assert set(wb.sheetnames) == set(expected_scenarios)

    for sheet_name in expected_scenarios:
        ws = wb[sheet_name]
        assert ws.max_row == 103, f"{sheet_name}: expected 103 rows, got {ws.max_row}"

        first_date = ws.cell(row=4, column=2).value
        assert isinstance(first_date, datetime), f"{sheet_name}: B4 must be datetime"

        cumul_cell = ws.cell(row=5, column=5)
        assert isinstance(cumul_cell.value, str) and cumul_cell.value.startswith('='), \
            f"{sheet_name}: E5 should be formula, got {cumul_cell.value}"
    return True
```

## External Verifier Cross-Check

**Critical**: Self-validation passing does not guarantee verifier success. Before marking complete:
1. **Header text**: Copy verbatim from task requirements; do not rephrase
2. **On-time status format**: Exact phrasing matters (e.g., "May PO On-Time: No" vs "On-Time: No")
3. **Total calculations**: Verify sums match expected values from task spec
4. **Shift day counts**: If task specifies a range, verify count falls within range
5. **Holiday dates**: Confirm against task description, not assumptions
6. **Formula structure**: Verify cumulative formulas reference correct columns and previous rows

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs. Pass raw float values directly.
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`
- DO: `ws.cell(row=r, column=c, value=x)` with raw float

## Anti-Patterns

- **Don't** use `df.to_excel()` when formulas are required
- **Don't** use date formulas like `=B4+1` — write actual `datetime` objects
- **Don't** hardcode column letters — use `COLUMN_MAP` with 1-based indices
- **Don't** assume pandas can read back what openpyxl writes with formulas
- **Don't** mix value types in formula columns
- **Don't** assume US federal holidays — extract from task description
- **Don't** reverse cumulative formula: `=D4-C4` is wrong, use `=C4-D4`
- **Don't** ignore product-specific start/cutoff dates in multi-product scenarios

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ValueError: Length mismatch` | Pandas reading formula cells as NaN | Use `openpyxl` directly, not pandas |
| Dates show as integers | Excel serial date format | Pass `datetime` objects, not strings |
| Formulas appear as text | Cell typed as string | Pass formula string starting with `=` |
| Formulas evaluate to 0 on re-read | Pandas `data_only=True` default | Use `load_workbook(data_only=False)` |
| Weekend production not zero | Wrong weekday logic | `weekday() >= 5` for Sat/Sun |
| Cumulative wrong after row 1 | Formula references off-by-one or reversed signs | Use `=E{row-1}+C{row}-D{row}` |
| Verifier rejects despite self-validation passing | Header typo, wrong totals, missing sections | Cross-check against task spec verbatim |
| Wrong holiday dates | Assumed US holidays | Extract exact dates from task description |
| Sheet name rejected | Typo or wrong case | Copy sheet names verbatim from task requirements |
| `ModuleNotFoundError: pandas` | PEP 668 protection | Use `--break-system-packages` or avoid pandas |

## Fallback: pandas for Value-Only Output

If formulas are NOT required and you need quick value export:
```python
import pandas as pd
df.to_excel('output.xlsx', sheet_name='Plan', index=False)
```

See `references/scenario_templates.md` for complete scenario configuration examples.