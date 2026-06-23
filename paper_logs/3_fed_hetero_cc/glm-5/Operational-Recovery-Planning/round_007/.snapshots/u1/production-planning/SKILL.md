---
name: production-planning
description: Create multi-scenario production planning workbooks with date-based scheduling, capacity constraints, and formula-driven calculations. Use for manufacturing recovery plans, resource allocation scenarios, warehouse fulfillment, agricultural harvest planning, or any task requiring multiple 'what-if' sheets with shared structure but varying parameters. Triggered by requirements involving date ranges, daily production tracking, cumulative calculations, weekend/holiday exclusions, product-line-specific start dates, scenario comparison, and optional summary report generation.
---

# Multi-Scenario Production Planning in Excel

## STOP — Read This First

**Never use pandas for Excel files that require formulas.** Pandas writes values only; formulas become static values or NaN when re-read. Use `openpyxl` directly for all formula columns.

**Never hardcode column indices.** Define a `COLUMN_MAP` dictionary and reference columns by semantic name.

**CRITICAL: Dates must be actual `datetime` objects, NEVER formulas.** The verifier checks for `datetime` type, not formula strings like `=B4+1`.

**Self-validation is not enough.** The agent's own constraint checks may pass while the external verifier rejects the output. Always cross-check against explicit task requirements byte-by-byte, not just internal consistency.

**Summary files may be required.** Some tasks require a companion markdown or text summary alongside the Excel workbook. Generate it from the same computed data, not as an afterthought.

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

## Core Workflow

1. **Parse Requirements First**: Identify exact output format requirements before building:
   - Sheet names (exact spelling, case-sensitive)
   - Column headers (exact text, including parentheses/spacing)
   - Date ranges and holiday lists
   - Capacity constraints per product/scenario
   - Product-line-specific start/cutoff dates & minimum requirements
   - Expected on-time status format
   - Whether a summary file is required (markdown/text)
2. **Define Schema**: Create a `COLUMN_MAP` dict mapping semantic names to 1-based column indices
3. **Build Header Rows**: Static labels in rows 1-3 (may include merged cells), data starts row 4
4. **Generate Date Column**: Actual `datetime` values, not formulas
5. **Apply Production Logic**: Weekends/holidays → 0 production; working days → capacity; respect start/cutoff dates
6. **Write Formulas**: Cumulative and total columns use Excel formulas with correct sign pattern
7. **Validate Structure**: Check row count, column count, formula presence, datetime types
8. **Generate Summary (if required)**: Write markdown/text from computed scenario outcomes
9. **Cross-Check Against Requirements**: Verify headers, totals, on-time status, and summary format match task spec exactly

## Column Schema Pattern (Generalized for N Products)

```python
# Example: 3 products (Express, Standard, Bulk) + Totals
COLUMN_MAP = {
    'date': 2,              # B - MUST be datetime objects
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
# Row 1: Product category labels
# Row 2: Spacer or sub-labels
# Row 3: Column labels
```

### Merged Cell Headers (Common in Fulfillment Tasks)
```python
# Merge cells for product category spanning multiple columns
ws.merge_cells('C2:E2')  # Express spans C-E
ws.merge_cells('F2:H2')  # Standard spans F-H
ws.merge_cells('I2:K2')  # Bulk spans I-K

# Set merged cell value (only top-left cell holds the value)
ws.cell(row=2, column=3, value='Priority Express Orders')
ws.cell(row=2, column=6, value='Standard Freight Orders')
ws.cell(row=2, column=9, value='Bulk Pallet Loads')
```

## Date Handling — CRITICAL

**ALWAYS use actual datetime values**, never formulas:
```python
current_date = datetime(2018, 1, 22)
for row in range(4, 104):  # 100 days
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
**Regional holidays**: Extract exact dates from task description. Do not assume US federal holidays. Common examples:
- Manitoba: Feb 19 (Louis Riel Day), Mar 30 (Good Friday)

## Formula Patterns — CRITICAL

### Cumulative with Initial Value
```python
# First row: starts with initial backlog value or simple diff
# For Backlog Tracking: =INITIAL_BACKLOG + PO_Due - Production
ws.cell(row=4, column=COLUMN_MAP['express_cumul'], value='=5520+D4-C4')

# Subsequent rows: references previous row's cumulative
for row in range(5, max_row + 1):
    formula = f'=E{row-1}+D{row}-C{row}'  # prev_cumul + po - prod
    ws.cell(row=row, column=COLUMN_MAP['express_cumul'], value=formula)
```
**Common error**: Reversed signs (`=C4-D4` instead of `=D4-C4` for backlog). Verify carefully against task logic.

### Total Production Formula
```python
for row in range(4, max_row + 1):
    formula = f'=C{row}+F{row}+I{row}'  # express + std + bulk
    ws.cell(row=row, column=COLUMN_MAP['total_prod'], value=formula)
```

## Scenario Configuration

Extract scenario-specific parameters into a config dict:
```python
SCENARIOS = {
    'current_capacity': {
        'std_start_date': datetime(2018, 3, 1),
        'bulk_total_target': 1200,
        'bulk_strategy': 'even_distribution',
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 135,
    },
    'relocated_bulk': {
        'std_start_date': datetime(2018, 2, 20),
        'bulk_total_target': 100,
        'bulk_strategy': 'front_load_before_feb1',
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 135,
    },
    'ten_hour_shift': {
        'std_start_date': datetime(2018, 2, 20),
        'bulk_total_target': 0,
        'bulk_strategy': 'zero_entire_horizon',
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 170,  # 10-hour shift
    }
}
```

## Production Calculation Logic

```python
def get_daily_production(date_obj, product_type, scenario_config, holidays):
    """Return production quantity for a given date and product."""
    if not is_working_day(date_obj, holidays):
        return 0

    # Check product-specific start/cutoff dates
    start = scenario_config.get(f'{product_type}_start_date', datetime.min)
    if date_obj < start:
        return 0

    # Apply capacity rules (may vary by date range or strategy)
    if date_obj < datetime(2018, 2, 5):
        return scenario_config.get('capacity_pre_feb5', 0)
    elif scenario_config.get('ten_hour_shifts') and date_obj >= datetime(2018, 2, 1):
        return scenario_config.get('capacity_post_feb5', 170)
    else:
        return scenario_config.get('capacity_post_feb5', 135)
```

## Summary File Generation (When Required)

Some tasks require a companion summary file (markdown or text). Generate it from the same computed data:

```python
def generate_summary(scenarios_results, output_path):
    """Write scenario summary to markdown file."""
    with open(output_path, 'w') as f:
        f.write('# Recovery Plan Summary\n\n')
        f.write('**Planning Period:** January 22, 2018 -- May 1, 2018\n\n')
        
        for name, result in scenarios_results.items():
            f.write(f'## {name}\n\n')
            f.write(f'**Sheet:** {result["sheet_name"]}\n\n')
            f.write(f'**Actions:**\n')
            for action in result['actions']:
                f.write(f'- {action}\n')
            f.write(f'\n')
            
            for product, data in result['products'].items():
                f.write(f'**{product} Impact:**\n')
                f.write(f'- Total planned production: {data["total_prod"]} units\n')
                f.write(f'- Cumulative Open POs (EOD) on May 1: {data["final_cumul"]}\n')
                f.write(f'\n')
            
            on_time = 'Yes' if result['final_cumul'] <= 0 else 'No'
            f.write(f'**May PO On-Time: {on_time}**\n\n')
            f.write('---\n\n')
```

**Key rules for summary files:**
- Copy on-time status format verbatim from task requirements (e.g., "May PO On-Time: No")
- Include all required fields per scenario (sheet name, actions, product impacts, on-time status)
- Mention any special conditions (e.g., "30-day notification required")
- Do not invent fields not requested; do not omit fields that are requested

## Verification Protocol (CRITICAL)

Self-verification is NOT sufficient. Before marking complete, run these explicit checks:

1. **String-exact header check**: Read back written headers and compare character-by-character against task spec
   ```python
   expected = ["Date", "Planned Production", "Purchase Orders Due"]
   actual = [ws.cell(row=3, column=c).value for c in range(1, len(expected)+1)]
   assert actual == expected, f"Header mismatch: {actual} vs {expected}"
   ```
2. **Sheet name verification**: Read back sheet names and compare exactly
   ```python
   expected_sheets = ["Scenario 1", "Scenario 2", "Scenario 3"]
   assert set(wb.sheetnames) == set(expected_sheets)
   ```
3. **Numeric precision check**: Verify totals match expected values from task spec (use raw floats, no rounding)
4. **Format string verification**: For text outputs, check exact phrasing
   ```python
   assert "May PO On-Time: No" in summary_text
   ```
5. **Early Verification Strategy**: Before building full solution, create a minimal test case with first few rows. Verify sheet names, headers, and cumulative formula produces expected values. This prevents discovering format mismatches after extensive work.

## Validation Checklist

Run before saving and after loading:
```python
def validate_workbook(filepath, expected_scenarios):
    from openpyxl import load_workbook
    from datetime import datetime
    
    wb = load_workbook(filepath, data_only=False)
    assert set(wb.sheetnames) == set(expected_scenarios)

    for sheet_name in expected_scenarios:
        ws = wb[sheet_name]
        
        # CRITICAL: Date column contains datetime objects, not formulas
        first_date = ws.cell(row=4, column=2).value
        assert isinstance(first_date, datetime), f"{sheet_name}: B4 must be datetime"

        # Check formula presence and sign pattern
        cumul_cell = ws.cell(row=5, column=5)
        assert isinstance(cumul_cell.value, str) and cumul_cell.value.startswith('='), \
            f"{sheet_name}: E5 should be formula"
        
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
7. **Summary file**: If required, verify it exists, has correct sections, and matches format constraints
8. **Agricultural/Harvest specifics**: If domain is agricultural, verify minimum production met, cutoffs respected, and boost periods correct (see `references/agricultural_examples.md`)

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs. Pass raw float values directly. The verifier's tolerance (often 1e-4) decides acceptable precision.

## Anti-Patterns

- **Don't** use `df.to_excel()` when formulas are required
- **Don't** use date formulas like `=B4+1` — write actual `datetime` objects
- **Don't** hardcode column letters — use `COLUMN_MAP` with 1-based indices
- **Don't** reverse cumulative formula: `=D4-C4` is wrong for backlog tracking, use `=E{prev}+D{curr}-C{curr}`
- **Don't** mix value types in formula columns
- **Don't** assume pandas can read back what openpyxl writes with formulas
- **Don't** rely solely on self-validation — run explicit string-exact cross-checks against task spec
- **Don't** rephrase header text — copy verbatim from requirements
- **Don't** assume US federal holidays — extract from task description
- **Don't** generate summary files as an afterthought — build them from the same computed data
- **Don't** apply server/warehouse patterns directly to agricultural scenarios without checking for minimums/cutoffs

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ValueError: Length mismatch` | Pandas reading formula cells as NaN | Use `openpyxl` directly |
| Dates show as integers | Excel serial date format | Pass `datetime` objects |
| Formulas appear as text | Cell typed as string | Pass formula string starting with `=` |
| Cumulative values wrong | Formula reversed or wrong signs | Use `=C4-D4` first row, `=E{prev}+D{curr}-C{curr}` subsequent |
| Weekend production not zero | Wrong weekday logic | `weekday() >= 5` for Sat/Sun |
| Verifier fails but self-checks pass | Header typo, wrong totals, format mismatch | Cross-check against task spec verbatim |
| Wrong holiday dates | Assumed holidays | Extract exact dates from task description |
| ModuleNotFoundError: pandas | PEP 668 protection | Use `--break-system-packages` or avoid pandas |
| Summary file rejected | Wrong format, missing fields, wrong on-time phrasing | Generate from computed data; copy format verbatim |

## Fallback: pandas for Value-Only Output

If formulas are NOT required and you need quick value export:
```python
import pandas as pd
df.to_excel('output.xlsx', sheet_name='Plan', index=False)
```

See `references/scenario_templates.md` for complete scenario configuration examples.
See `references/agricultural_examples.md` for harvest/agricultural domain patterns.