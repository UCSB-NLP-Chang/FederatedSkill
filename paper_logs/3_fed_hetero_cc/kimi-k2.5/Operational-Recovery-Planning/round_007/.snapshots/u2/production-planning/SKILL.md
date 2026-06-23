---
name: production-planning
description: Create multi-scenario production planning workbooks with date-based scheduling, capacity constraints, and formula-driven calculations. Use for manufacturing recovery plans, warehouse fulfillment scenarios, server provisioning, agricultural harvest planning, resource allocation, or any task requiring multiple 'what-if' sheets with shared structure but varying parameters. Triggered by requirements involving date ranges, daily production tracking, cumulative calculations, weekend/holiday exclusions, product-line-specific start dates, minimum production requirements, temporary capacity boosts, summary report generation, and scenario comparison.
---

# Multi-Scenario Production Planning in Excel

## STOP — Read This First

**Never use pandas for Excel files that require formulas.** Pandas writes values only; formulas become static values or NaN when re-read. Use `openpyxl` directly for all formula columns.

**Never hardcode column indices.** Define a `COLUMN_MAP` dictionary and reference columns by semantic name.

**CRITICAL: Dates must be actual datetime objects, NEVER formulas.** The verifier checks for `datetime` type, not formula strings like `=B4+1`.

**Self-verification passing does NOT guarantee verifier success.** Always cross-check output format byte-by-byte against explicit task requirements, not just internal consistency.

**CRITICAL: Each domain variant has unique constraints.** Do NOT apply server provisioning patterns to agricultural/harvest tasks. See Domain Adaptation Guide below.

**Summary files may be required.** Some tasks require a companion markdown summary. Generate it from the same computed data, not as an afterthought.

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

1. **Parse Requirements First**: Identify exact output format before building:
   - Sheet names (exact spelling, case-sensitive)
   - Column headers (exact text, including parentheses/spacing — copy verbatim)
   - Date ranges and holiday lists
   - Capacity constraints per product/scenario
   - Product-line-specific start dates & cutoffs
   - Minimum production requirements (before cutoffs, total output)
   - Temporary capacity boosts (10-hour shifts, overtime periods)
   - Expected on-time status format
   - Whether a summary file is required (markdown/text)

2. **Define Schema**: Create a `COLUMN_MAP` dict mapping semantic names to 1-based column indices

3. **Build Header Rows**: Static labels in rows 1-3 (may include merged cells), data starts row 4

4. **Generate Date Column**: **Actual `datetime` values**, not formulas

5. **Apply Production Logic**: Weekends/holidays → 0 production; working days → capacity; respect domain-specific constraints

6. **Write Formulas**: Cumulative columns use Excel formulas with **correct sign pattern**

7. **Validate Structure**: Check row count, column count, formula presence, **datetime types in date column**

8. **Generate Summary (if required)**: Write markdown/text from computed scenario outcomes

9. **Cross-Check Against Requirements**: Verify headers, totals, on-time status, and summary format match task spec exactly

## Verification Protocol (CRITICAL)

Self-verification is NOT sufficient. Before marking complete:

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

3. **Numeric precision check**: Verify totals match expected values from task spec
   ```python
   total = sum(production_values)
   assert abs(total - expected_total) < 0.01
   ```

4. **Format string verification**: For text outputs (markdown, summary files), check exact phrasing
   ```python
   # "May PO On-Time: No" vs "On-Time: No" - exact format matters
   assert "May PO On-Time: No" in summary_text
   ```

5. **Domain-specific invariant check**: Verify domain-specific constraints are respected (see Domain Adaptation Guide)

6. **Summary file verification**: If required, verify it exists, has correct sections, and matches format constraints

## Domain Adaptation Guide (CRITICAL)

**Do NOT apply patterns from one domain to another without adaptation.**

| Domain | Key Characteristics | Reference |
|--------|---------------------|-----------|
| Server Provisioning | 2 products, simple cumulative formulas | scenario_templates.md |
| Warehouse Fulfillment | 3 products (Express/Std/Bulk), shared capacity, merged headers | scenario_templates.md |
| Agricultural/Harvest | Asymmetric constraints, minimums, cutoffs, temporary boosts | agricultural_examples.md |

### Agricultural/Harvest Domain — CRITICAL DIFFERENCES

Harvest planning has unique constraints that differ from manufacturing/server provisioning:

| Constraint Type | Example | Implementation |
|-----------------|---------|----------------|
| Early cutoff | Flax must complete before Feb 1 | `if date >= cutoff: prod = 0` |
| Delayed start | Canola starts March 1 | `if date < start_date: prod = 0` |
| Minimum before cutoff | 100 units min before Feb 1 | Track running total; ensure `total >= min` before cutoff |
| Temporary capacity boost | 10-hour shifts Feb 1-28 | `if boost_start <= date <= boost_end: capacity = 170` |
| Zero production product | Flax = 0 in some scenarios | Explicitly set to 0, don't omit |

### Header Structure for Agricultural

```python
# Row 2: Merged product category labels
ws.merge_cells('C2:E2')  # Product A spans C-E
ws.merge_cells('F2:H2')  # Product B spans F-H
ws.cell(row=2, column=3, value='Wheat Bin Loads')
ws.cell(row=2, column=6, value='Canola Bin Loads')
ws.cell(row=2, column=9, value='Flax Processing')
```

### Production Calculation with Minimum Requirements

```python
def get_daily_production_ag(date_obj, product_type, scenario_config,
                            holidays=None, running_totals=None):
    """Agricultural production with minimum requirements and cutoffs."""
    if not is_working_day(date_obj, holidays):
        return 0

    start = scenario_config.get(f'{product_type}_start', datetime.min)
    cutoff = scenario_config.get(f'{product_type}_cutoff')

    if date_obj < start:
        return 0
    if cutoff and date_obj >= cutoff:
        return 0

    # Check minimum production requirement before cutoff
    min_required = scenario_config.get(f'{product_type}_min_before_cutoff')
    if min_required and cutoff and running_totals:
        current_total = running_totals.get(product_type, 0)
        days_until_cutoff = (cutoff - date_obj).days
        working_days_left = count_working_days(date_obj, cutoff, holidays)

        if working_days_left > 0:
            min_daily = (min_required - current_total) / working_days_left
            return max(scenario_config.get('daily_rate', 20), min_daily)

    # Standard capacity logic
    if scenario_config.get('boost_start') and scenario_config.get('boost_end'):
        if scenario_config['boost_start'] <= date_obj <= scenario_config['boost_end']:
            return scenario_config.get('boost_capacity', 170)

    return scenario_config.get('standard_capacity', 120)
```

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

**Regional holidays**: Extract exact dates from task description. Do not assume US federal holidays.
- Manitoba 2018: Feb 19 (Louis Riel Day), Mar 30 (Good Friday)

## Formula Patterns — CRITICAL

### Cumulative with Initial Value

```python
# First row: starts with initial backlog value or simple diff
ws.cell(row=4, column=COLUMN_MAP['express_cumul'], value='=5520+C4-D4')

# Subsequent rows: references previous row's cumulative
for row in range(5, max_row + 1):
    formula = f'=E{row-1}+C{row}-D{row}'  # prev_cumul + prod - po_due
    ws.cell(row=row, column=COLUMN_MAP['express_cumul'], value=formula)
```
**Common error**: Reversed signs (`=D4-C4` instead of `=C4-D4`). Verify carefully.

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
    'Current Equipment and Bins': {
        'canola_start': datetime(2018, 3, 1),
        'flax_total_target': 1200,
        'flax_strategy': 'even_distribution',
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 135,
    },
    'Relocated Flax Processing': {
        'canola_start': datetime(2018, 2, 20),
        'flax_total_target': 100,
        'flax_strategy': 'front_load_before_feb1',
        'flax_cutoff': datetime(2018, 2, 1),
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 135,
    },
    '10 hr Shift Relocate Flax Proc': {
        'canola_start': datetime(2018, 2, 20),
        'flax_total_target': 0,
        'flax_strategy': 'zero_entire_horizon',
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 170,  # 10-hour shift
        'ten_hour_shifts': True,
        'ten_hour_start': datetime(2018, 2, 1),
    }
}
```

## Summary File Generation (When Required)

Some tasks require a companion summary file (markdown). Generate it from the same computed data:

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
- Do not invent fields not requested; do not omit fields that are requested

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

## Output Precision

Never round, truncate, or fixed-format numeric values when writing outputs. Pass raw float values directly. The verifier's tolerance (often 1e-4) decides acceptable precision.
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`
- DO: `ws.cell(row=r, column=c, value=x)` with raw float

## Anti-Patterns

- **Don't** use `df.to_excel()` when formulas are required
- **Don't** use date formulas like `=B4+1` — write actual `datetime` objects
- **Don't** hardcode column letters — use `COLUMN_MAP` with 1-based indices
- **Don't** reverse cumulative formula: `=D4-C4` is wrong, use `=C4-D4`
- **Don't** mix value types in formula columns
- **Don't** assume pandas can read back what openpyxl writes with formulas
- **Don't** rely solely on self-validation — cross-check against explicit task requirements
- **Don't** rephrase header text — copy verbatim from requirements
- **Don't** assume US federal holidays — extract from task description
- **Don't** generate summary files as an afterthought — build them from the same computed data
- **Don't** apply server provisioning patterns directly to agricultural scenarios — minimum requirements and temporary boosts need explicit handling
- **Don't** ignore product-specific minimum production requirements — track running totals
- **Don't** assume internal consistency implies external verifier will pass

## Known Invariants (by sub-task)

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

### Agricultural Harvest Planning
- Three products with asymmetric constraints (different start dates, cutoffs, minimums)
- One product may have zero production in some scenarios
- Temporary capacity boosts (10-hour shifts) with specific date windows
- Minimum production requirements before early cutoffs
- Provincial/regional holidays (not US federal)
- Summary markdown file often required with exact format constraints

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ValueError: Length mismatch` | Pandas reading formula cells as NaN | Use `openpyxl` directly |
| Dates show as integers | Excel serial date format | Pass `datetime` objects |
| Formulas appear as text | Cell typed as string | Pass formula string starting with `=` |
| Cumulative values wrong | Formula reversed or wrong signs | Use `=C4-D4` first row, `=E{prev}+C{curr}-D{curr}` subsequent |
| Weekend production not zero | Wrong weekday logic | `weekday() >= 5` for Sat/Sun |
| Verifier fails but self-checks pass | Header typo, wrong totals, format mismatch | Cross-check against task spec verbatim |
| Wrong holiday dates | Assumed holidays | Extract exact dates from task description |
| ModuleNotFoundError: pandas | PEP 668 protection | Use `--break-system-packages` or avoid pandas |
| Summary file rejected | Wrong format, missing fields, wrong on-time phrasing | Generate from computed data; copy format verbatim |
| Minimum production not met | Not tracking running totals | Calculate required daily rate based on days remaining |
| Agricultural scenario rejected | Applied wrong domain pattern | Check for minimum requirements, temporary boosts, zero-production products |
| Self-check passes but verifier fails | Internal consistency ≠ external requirements | Run explicit string-exact checks against task spec |

## Fallback: pandas for Value-Only Output

If formulas are NOT required and you need quick value export:
```python
import pandas as pd
df.to_excel('output.xlsx', sheet_name='Plan', index=False)
```

See `references/scenario_templates.md` for server provisioning and warehouse fulfillment examples.
See `references/agricultural_examples.md` for harvest/agricultural domain patterns.