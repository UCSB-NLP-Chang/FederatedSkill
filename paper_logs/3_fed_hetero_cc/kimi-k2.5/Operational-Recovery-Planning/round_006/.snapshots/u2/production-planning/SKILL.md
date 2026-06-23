---
name: production-planning
description: Create multi-scenario production planning workbooks with date-based scheduling, capacity constraints, and formula-driven calculations. Use for manufacturing recovery plans, warehouse fulfillment scenarios, server provisioning, resource allocation, or any task requiring multiple 'what-if' sheets with shared structure but varying parameters. Triggered by requirements involving date ranges, daily production tracking, cumulative calculations, weekend/holiday exclusions, product-line-specific start dates, and scenario comparison.
---

# Multi-Scenario Production Planning in Excel

## STOP — Read This First

**Never use pandas for Excel files that require formulas.** Pandas writes values only; formulas become static values or NaN when re-read. Use `openpyxl` directly for all formula columns.

**Never hardcode column indices.** Define a `COLUMN_MAP` dictionary and reference columns by semantic name.

**CRITICAL: Dates must be actual datetime objects, NEVER formulas.** The verifier checks for `datetime` type, not formula strings like `=B4+1`.

**Self-verification is not enough.** The agent's own constraint checks may pass while the external verifier still rejects the output. Always cross-check against explicit task requirements, not just internal consistency.

## Quick Start

```python
from openpyxl import Workbook
from datetime import datetime, timedelta

wb = Workbook()
wb.remove(wb.active)

for scenario_name in ['Scenario A', 'Scenario B']:
    ws = wb.create_sheet(scenario_name)
    build_scenario(ws, scenario_config)

wb.save('output.xlsx')
```

## Workflow

1. **Parse Requirements First**: Identify exact output format before building:
   - Sheet names (exact spelling, case-sensitive)
   - Column headers (exact text, case-sensitive, copy verbatim)
   - Date ranges and holiday lists
   - Capacity constraints per product/scenario
   - Product-line-specific start dates & cutoffs
   - Expected on-time status format

2. **Define Schema**: Create a `COLUMN_MAP` dict mapping semantic names to 1-based column indices

3. **Build Header Rows**: Static labels in rows 1-3 (may include merged cells), data starts row 4

4. **Generate Date Column**: **Actual `datetime` values**, not formulas

5. **Apply Production Logic**: Weekends/holidays → 0 production; working days → capacity; respect product-specific start/cutoff dates

6. **Write Formulas**: Cumulative columns use Excel formulas with **correct sign pattern**

7. **Validate Structure**: Check row count, column count, formula presence, **datetime types in date column**

8. **Cross-Check Against Requirements**: Verify headers, totals, and on-time status match task spec exactly before finalizing.

## Column Schema Pattern (Generalized for N Products)

```python
# Example: 2 products (Web/DB) + Notes
COLUMN_MAP_2PROD = {
    'date': 2,           # B
    'prod_web': 3,       # C - Planned Production
    'po_web': 4,         # D - Purchase Orders Due
    'cumul_web': 5,      # E - Cumulative (FORMULA)
    'prod_db': 6,        # F
    'po_db': 7,          # G
    'cumul_db': 8,       # H - Cumulative (FORMULA)
    'notes': 11,         # K
}

# Example: 3 products (Express/Standard/Bulk) + Totals
COLUMN_MAP_3PROD = {
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

## Header Row Patterns

### Simple 3-Row Header
```python
# Row 1: Product category labels (may be merged)
# Row 2: Spacer or sub-labels
# Row 3: Column labels (Planned Production, PO Due, Cumulative)
```

### Merged Cell Headers (Common in Fulfillment)
```python
from openpyxl import load_workbook

ws.merge_cells('C2:E2')  # Express spans C-E
ws.merge_cells('F2:H2')  # Standard spans F-H

# Set merged cell value (only top-left cell holds the value)
ws.cell(row=2, column=3, value='Priority Express Orders')
ws.cell(row=2, column=6, value='Standard Freight Orders')
```

## Date Handling — CRITICAL

**ALWAYS use actual datetime values:**
```python
current_date = datetime(2018, 1, 22)
for row in range(4, 104):
    ws.cell(row=row, column=COLUMN_MAP['date'], value=current_date)
    current_date += timedelta(days=1)
```

**WRONG - formula strings (will fail verifier):**
```python
# NEVER do this
ws.cell(row=5, column=2, value='=B4+1')  # Verifier expects datetime type
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

## Formula Patterns — CRITICAL

Cumulative formulas must follow this exact pattern:
```python
# First data row (row 4): simple production minus PO (or + initial backlog)
ws.cell(row=4, column=COLUMN_MAP['express_cumul'], value='=C4-D4')
# With initial backlog:
ws.cell(row=4, column=COLUMN_MAP['express_cumul'], value='=5520+C4-D4')

# Subsequent rows: previous cumulative + current production - current PO
for row in range(5, max_row + 1):
    formula = f'=E{row-1}+C{row}-D{row}'  # prev_cumul + prod - po_due
    ws.cell(row=row, column=COLUMN_MAP['express_cumul'], value=formula)
```

**Total Production Formula (sum across products):**
```python
for row in range(4, max_row + 1):
    formula = f'=C{row}+F{row}+I{row}'  # express + std + bulk
    ws.cell(row=row, column=COLUMN_MAP['total_prod'], value=formula)
```
**Common error**: `=D4-C4` (reversed signs) or `=E4-C5+D5` (wrong row refs).

## Multi-Product Fulfillment Pattern

Common in warehouse scenarios with Express/Standard/Bulk product lines sharing capacity:
```python
PRODUCT_STARTS = {
    'express': datetime(2018, 1, 22),
    'standard': datetime(2018, 3, 1),
    'bulk': datetime(2018, 1, 22),
}
```

## Scenario Configuration

Extract scenario-specific parameters into a config dict:
```python
SCENARIOS = {
    'Current Capacity': {
        'standard_start': datetime(2018, 3, 1),
        'bulk_cutoff': None,
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 135,
        'ten_hour_shifts': False,
    },
    'Relocated Storage': {
        'standard_start': datetime(2018, 2, 20),
        'bulk_cutoff': datetime(2018, 2, 1),
        'bulk_min_pre_cutoff': 100,
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 135,
    },
    'Extended Shifts': {
        'standard_start': datetime(2018, 2, 20),
        'ten_hour_shifts': True,
        'ten_hour_start': datetime(2018, 2, 1),
        'ten_hour_capacity': 170,
    }
}
```

## Production Calculation Logic

```python
def get_daily_production(date_obj, product_type, scenario_config, holidays=None):
    """Return production quantity for a given date and product."""
    if not is_working_day(date_obj, holidays):
        return 0

    # Check product-specific start date
    start = scenario_config.get(f'{product_type}_start', datetime.min)
    if date_obj < start:
        return 0

    # Check cutoff
    cutoff = scenario_config.get(f'{product_type}_cutoff')
    if cutoff and date_obj >= cutoff:
        return 0

    # Apply capacity rules
    if scenario_config.get('ten_hour_shifts') and date_obj >= scenario_config.get('ten_hour_start', datetime.min):
        return scenario_config.get('ten_hour_capacity', 170)
    elif date_obj < datetime(2018, 2, 5):
        return scenario_config.get('capacity_pre_feb5', 120)
    else:
        return scenario_config.get('capacity_post_feb5', 135)
```

## Regional Holidays Reference

**Do not assume US federal holidays.** Extract exact dates from task description.
Common regional examples (verify against spec):
- **Manitoba 2018**: Feb 19 (Louis Riel Day), Mar 30 (Good Friday)
```python
MANITOBA_HOLIDAYS_2018 = {datetime(2018, 2, 19), datetime(2018, 3, 30)}
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
        assert ws.max_row >= 4, f"{sheet_name}: too few rows"
        
        # CRITICAL: Date column contains datetime objects, not formulas
        first_date = ws.cell(row=4, column=2).value
        assert isinstance(first_date, datetime), f"{sheet_name}: B4 must be datetime, got {type(first_date)}"
        
        # Formula presence check
        cumul_cell = ws.cell(row=5, column=5)
        assert isinstance(cumul_cell.value, str) and cumul_cell.value.startswith('='), \
            f"{sheet_name}: E5 should be formula, got {cumul_cell.value}"
            
    return True
```

## External Verifier Cross-Check & Early Verification

**Critical**: Self-validation passing does not guarantee verifier success. Before marking complete:
1. Create minimal test case with first few rows to verify format early.
2. **Header text**: Copy verbatim from task requirements; do not rephrase.
3. **On-time status format**: Exact phrasing matters (e.g., "May PO On-Time: No").
4. **Total calculations**: Verify sums match expected values.
5. **Holiday dates**: Confirm against task description.
6. **Formula structure**: Verify cumulative formulas reference correct columns and previous rows.

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs. Pass raw float values directly:
- DO NOT: `round(x, N)`, `format(x, ".2f")`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float

## Anti-Patterns

- **Don't** use `df.to_excel()` when formulas are required
- **Don't** use date formulas like `=B4+1` — write actual `datetime` objects
- **Don't** hardcode column letters — use `COLUMN_MAP` with 1-based indices
- **Don't** reverse cumulative formula: `=D4-C4` is wrong, use `=C4-D4`
- **Don't** mix value types in formula columns
- **Don't** assume pandas can read back what openpyxl writes with formulas — use `data_only=False`
- **Don't** rely solely on self-validation — cross-check against explicit task requirements

## Known Invariants

### Server Provisioning Recovery
- Output must have exactly 3 scenario sheets with exact names from task spec
- Each sheet typically has 103 rows (3 header + 100 data)
- Cumulative columns MUST be formulas, NOT static values
- Date column MUST be datetime objects

### Fulfillment Recovery (Multi-Product)
- Three product types may share capacity constraints
- Each product may have different start dates per scenario
- Bulk/Network products may have minimum production requirements before certain dates
- 10-hour shift scenarios require counting eligible working days (often 20-24 days)

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ValueError: Length mismatch` | Pandas reading formula cells as NaN | Use `openpyxl` directly, not pandas |
| Verifier rejects date column | Used formula `=B4+1` instead of datetime | Write actual `datetime` objects |
| Cumulative values wrong | Formula reversed or wrong signs | Use `=C4-D4` first row, `=E{prev}+C{curr}-D{curr}` subsequent |
| Product line starts too early | Ignored product-specific start date | Check `date_obj < product_start` before assigning capacity |
| Bulk production continues past cutoff | Missing cutoff date check | Add `if cutoff and date_obj >= cutoff: return 0` |
| Verifier fails but self-checks pass | Output format/header mismatch | Compare output byte-by-byte with expected format |
| Wrong working day count | Missing or extra holidays | Re-extract holiday dates from task; verify regional context |
| On-time status wrong | Cumulative calculation error | Verify end-of-period cumulative PO value |

## Fallback: pandas for Value-Only Output

If formulas are NOT required and you need quick value export:
```python
import pandas as pd
df.to_excel('output.xlsx', sheet_name='Plan', index=False)
```
See `references/scenario_templates.md` for complete examples including warehouse fulfillment variants.