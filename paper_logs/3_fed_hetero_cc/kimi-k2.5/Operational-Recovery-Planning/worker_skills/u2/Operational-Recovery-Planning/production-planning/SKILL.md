---
name: production-planning
description: Create multi-scenario production planning workbooks with date-based scheduling, capacity constraints, and formula-driven calculations. Use for manufacturing recovery plans, warehouse fulfillment scenarios, server provisioning, agricultural harvest planning, automotive parts production, resource allocation, or any task requiring multiple 'what-if' sheets with shared structure but varying parameters. Triggered by requirements involving date ranges, daily production tracking, cumulative calculations, weekend/holiday exclusions, product-line-specific start dates, minimum production requirements, temporary capacity boosts, summary report generation, and scenario comparison.
---

# Multi-Scenario Production Planning in Excel

## STOP — Read This First

**Never use pandas for Excel files that require formulas.** Pandas writes values only; formulas become static values or NaN when re-read. Use `openpyxl` directly for all formula columns.

**Never hardcode column indices.** Define a `COLUMN_MAP` dictionary and reference columns by semantic name.

**CRITICAL: Date columns must use `date` objects, NOT `datetime`.** The verifier checks for `date` type (no time component). Writing `datetime(2018, 1, 22)` produces `2018-01-22 00:00:00` in Excel, which fails verifiers expecting `2018-01-22`. Use `date(2018, 1, 22)` instead.

**CRITICAL: Excel sheet names are limited to 31 characters.** Truncation happens silently. Always verify sheet names after creation.

**Self-verification passing does NOT guarantee verifier success.** Always cross-check output format byte-by-byte against explicit task requirements, not just internal consistency. If a verifier reports a type mismatch (e.g., datetime vs date), treat it as a real failure — do not dismiss it as a "verification script issue."

**CRITICAL: Each domain variant has unique constraints.** Do NOT apply server provisioning patterns to agricultural/harvest/automotive tasks. See Domain Adaptation Guide below.

**Summary files may be required.** Some tasks require a companion markdown summary. Generate it from the same computed data, not as an afterthought.

## Quick Start

```python
from openpyxl import Workbook
from datetime import date, timedelta

wb = Workbook()
wb.remove(wb.active)

for scenario_name in ['Scenario A', 'Scenario B']:
    # Truncate to 31 chars if needed
    safe_name = scenario_name[:31]
    ws = wb.create_sheet(safe_name)
    build_scenario(ws, scenario_config)

wb.save('output.xlsx')
```

## Core Workflow

1. **Parse Requirements First**: Identify exact output format before building:
   - Sheet names (exact spelling, case-sensitive, **max 31 characters**)
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

4. **Generate Date Column**: **Actual `date` values** (NOT `datetime`, NOT formulas)

5. **Apply Production Logic**: Weekends/holidays → 0 production; working days → capacity; respect domain-specific constraints

6. **Write Formulas**: Cumulative columns use Excel formulas with **correct sign pattern**

7. **Validate Structure**: Check row count, column count, formula presence, **date types in date column**

8. **Generate Summary (if required)**: Write markdown/text from computed scenario outcomes

9. **Cross-Check Against Requirements**: Verify headers, totals, on-time status, and summary format match task spec exactly

## Verification Protocol (CRITICAL)

Self-verification is NOT sufficient. Before marking complete:

1. **Sheet name length check**: Excel truncates sheet names to 31 characters. Verify after creation:
   ```python
   for sheet in wb.sheetnames:
       assert len(sheet) <= 31, f"Sheet name '{sheet}' exceeds 31 chars"
       # Also verify it matches expected name (may have been truncated)
   ```

2. **String-exact header check**: Read back written headers and compare character-by-character against task spec
   ```python
   expected = ["Date", "Planned Production", "Purchase Orders Due"]
   actual = [ws.cell(row=3, column=c).value for c in range(1, len(expected)+1)]
   assert actual == expected, f"Header mismatch: {actual} vs {expected}"
   ```

3. **Sheet name verification**: Read back sheet names and compare exactly
   ```python
   expected_sheets = ["Scenario 1", "Scenario 2", "Scenario 3"]
   actual_sheets = wb.sheetnames
   # Check for truncation
   for exp, act in zip(expected_sheets, actual_sheets):
       assert exp == act, f"Sheet name mismatch: expected '{exp}', got '{act}'"
   ```

4. **Numeric precision check**: Verify totals match expected values from task spec
   ```python
   total = sum(production_values)
   assert abs(total - expected_total) < 0.01
   ```

5. **Format string verification**: For text outputs (markdown, summary files), check exact phrasing
   ```python
   # "May PO On-Time: No" vs "On-Time: No" - exact format matters
   assert "May PO On-Time: No" in summary_text
   ```

6. **Date type verification**: Verify date columns contain `date` objects (not `datetime`)
   ```python
   first_date = ws.cell(row=4, column=2).value
   assert isinstance(first_date, date) and not hasattr(first_date, 'hour'), \
       f"B4 must be date (not datetime): got {first_date}"
   ```

7. **Domain-specific invariant check**: Verify domain-specific constraints are respected (see Domain Adaptation Guide)

8. **Summary file verification**: If required, verify it exists, has correct sections, and matches format constraints

## Domain Adaptation Guide (CRITICAL)

**Do NOT apply patterns from one domain to another without adaptation.**

| Domain | Key Characteristics | Reference |
|--------|---------------------|-----------|
| Server Provisioning | 2 products, simple cumulative formulas | scenario_templates.md |
| Warehouse Fulfillment | 3 products (Express/Std/Bulk), shared capacity, merged headers | scenario_templates.md |
| Agricultural/Harvest | Asymmetric constraints, minimums, cutoffs, temporary boosts | agricultural_examples.md |
| Automotive Manufacturing | Same structure as agricultural, different terminology | agricultural_examples.md |

### 3-Product Layout Pattern (Agricultural/Automotive)

Both agricultural and automotive tasks use a 3-product layout with merged category headers:

```python
# Row 2: Merged product category labels spanning 3 columns each
ws.merge_cells('C2:E2')  # Product A: Production, PO Due, Cumulative
ws.merge_cells('F2:H2')  # Product B: Production, PO Due, Cumulative
ws.merge_cells('I2:K2')  # Product C: Production, PO Due, Cumulative (or Actual Var)

ws.cell(row=2, column=3, value='Wheat Bin Loads')      # or 'Crew Cab Running Boards'
ws.cell(row=2, column=6, value='Canola Bin Loads')     # or 'Extended Cab Running Boards'
ws.cell(row=2, column=9, value='Flax Processing')      # or 'Grill Guard'

# Row 3: Individual column headers
# C3: Planned Production, D3: Purchase Orders Due, E3: Cumulative Open POs (EOD)
# F3: Planned Production, G3: Purchase Orders Due, H3: Cumulative Open POs (EOD)
# I3: Planned Production, J3: Purchase Orders Due, K3: Actual Var to PO (or Cumulative)
```

**CRITICAL: Column alignment matters.** Product C (Grill Guard/Flax) may use "Actual Var to PO" instead of "Cumulative" for its third column. Read task requirements carefully.

### Asymmetric Constraints Pattern

Both agricultural and automotive domains feature:

| Constraint Type | Agricultural Example | Automotive Example | Implementation |
|-----------------|---------------------|-------------------|----------------|
| Early cutoff | Flax before Feb 1 | Grill Guard before Feb 1 | `if date >= cutoff: prod = 0` |
| Delayed start | Canola starts March 1 | Extended Cab starts March 1 | `if date < start_date: prod = 0` |
| Minimum before cutoff | 100 units min before Feb 1 | 100 Grill Guard before Feb 1 | Track running total; ensure `total >= min` before cutoff |
| Temporary capacity boost | 10-hour shifts Feb 1-28 | 10-hour shifts Feb 1-28 | `if boost_start <= date <= boost_end: capacity = 170` |
| Zero production product | Flax = 0 in some scenarios | Grill Guard = 0 in some scenarios | Explicitly set to 0, don't omit |

### Production Calculation with Minimum Requirements

```python
def get_daily_production(date_obj, product_type, scenario_config,
                         holidays=None, running_totals=None):
    """Production with minimum requirements and cutoffs."""
    if not is_working_day(date_obj, holidays):
        return 0

    start = scenario_config.get(f'{product_type}_start', date.min)
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
# Example: 3 products with 3 columns each (Production, PO Due, Cumulative)
COLUMN_MAP = {
    'date': 2,              # B - MUST be date objects (not datetime)
    'prod_a': 3,            # C - Product A Planned Production
    'po_a': 4,              # D - Product A Purchase Orders Due
    'cumul_a': 5,           # E - Product A Cumulative (FORMULA)
    'prod_b': 6,            # F - Product B Planned Production
    'po_b': 7,              # G - Product B Purchase Orders Due
    'cumul_b': 8,           # H - Product B Cumulative (FORMULA)
    'prod_c': 9,            # I - Product C Planned Production
    'po_c': 10,             # J - Product C Purchase Orders Due
    'cumul_c': 11,          # K - Product C Cumulative/Actual Var (FORMULA or value)
}
```
Access via: `ws.cell(row=r, column=COLUMN_MAP['date'], value=date_obj)`

## Date Handling — CRITICAL

**ALWAYS use `date` objects, NEVER `datetime` or formulas:**
```python
from datetime import date, timedelta

current_date = date(2018, 1, 22)
for row in range(4, 104):  # 100 days
    ws.cell(row=row, column=COLUMN_MAP['date'], value=current_date)
    current_date += timedelta(days=1)
```

**Why `date` not `datetime`:** Excel stores dates as serial numbers. `datetime` objects include a time component (00:00:00) that some verifiers reject. `date` objects serialize cleanly as date-only values.

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
ws.cell(row=4, column=COLUMN_MAP['cumul_a'], value='=5520+C4-D4')

# Subsequent rows: references previous row's cumulative
for row in range(5, max_row + 1):
    formula = f'=E{row-1}+C{row}-D{row}'  # prev_cumul + prod - po_due
    ws.cell(row=row, column=COLUMN_MAP['cumul_a'], value=formula)
```
**Common error**: Reversed signs (`=D4-C4` instead of `=C4-D4`). Verify carefully.

### Total Production Formula

```python
for row in range(4, max_row + 1):
    formula = f'=C{row}+F{row}+I{row}'  # prod_a + prod_b + prod_c
    ws.cell(row=row, column=COLUMN_MAP['total_prod'], value=formula)
```

## Scenario Configuration

Extract scenario-specific parameters into a config dict:
```python
SCENARIOS = {
    'Current Equipment and Bins': {
        'canola_start': date(2018, 3, 1),
        'flax_total_target': 1200,
        'flax_strategy': 'even_distribution',
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 135,
    },
    'Relocated Flax Processing': {
        'canola_start': date(2018, 2, 20),
        'flax_total_target': 100,
        'flax_strategy': 'front_load_before_feb1',
        'flax_cutoff': date(2018, 2, 1),
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 135,
    },
    '10 hr Shift Relocate Flax Proc': {
        'canola_start': date(2018, 2, 20),
        'flax_total_target': 0,
        'flax_strategy': 'zero_entire_horizon',
        'capacity_pre_feb5': 120,
        'capacity_post_feb5': 170,  # 10-hour shift
        'ten_hour_shifts': True,
        'ten_hour_start': date(2018, 2, 1),
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
- Copy on-time status format verbatim from task requirements (e.g., "May PO On-Time: No", "May PO On-Time: Crew Yes, Extended No")
- Include all required fields per scenario (sheet name, actions, product impacts, on-time status)
- Do not invent fields not requested; do not omit fields that are requested
- Mention "30-day notification" if 10-hour shifts are implemented

## Validation Checklist

Run before saving and after loading:
```python
def validate_workbook(filepath, expected_scenarios):
    from openpyxl import load_workbook
    from datetime import date

    wb = load_workbook(filepath, data_only=False)

    # Check sheet names match expected (and weren't truncated)
    for expected in expected_scenarios:
        assert expected in wb.sheetnames, f"Missing sheet: {expected}"
        # Verify no truncation occurred
        assert expected in wb.sheetnames, f"Sheet name may be truncated: looking for '{expected}'"

    for sheet_name in expected_scenarios:
        ws = wb[sheet_name]

        # CRITICAL: Date column contains date objects (not datetime, not formulas)
        first_date = ws.cell(row=4, column=2).value
        assert isinstance(first_date, date) and not hasattr(first_date, 'hour'), \
            f"{sheet_name}: B4 must be date (not datetime)"

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
- **Don't** use `datetime` for date columns — use `date` objects only
- **Don't** use date formulas like `=B4+1` — write actual `date` objects
- **Don't** hardcode column letters — use `COLUMN_MAP` with 1-based indices
- **Don't** reverse cumulative formula: `=D4-C4` is wrong, use `=C4-D4`
- **Don't** mix value types in formula columns
- **Don't** assume pandas can read back what openpyxl writes with formulas
- **Don't** rely solely on self-validation — cross-check against explicit task requirements
- **Don't** dismiss verifier type mismatches (e.g., datetime vs date) as "script issues" — they are real failures
- **Don't** rephrase header text — copy verbatim from requirements
- **Don't** assume US federal holidays — extract from task description
- **Don't** generate summary files as an afterthought — build them from the same computed data
- **Don't** apply server provisioning patterns directly to agricultural/automotive scenarios — minimum requirements and temporary boosts need explicit handling
- **Don't** ignore product-specific minimum production requirements — track running totals
- **Don't** assume internal consistency implies external verifier will pass
- **Don't** assume sheet names are preserved — Excel truncates to 31 characters silently
- **Don't** assume Product C uses the same column headers as Products A and B — "Actual Var to PO" vs "Cumulative Open POs" is a common variation

## Known Invariants (by sub-task)

### Server Provisioning Recovery
- Output must have exactly 3 scenario sheets with exact names from task spec
- Each sheet typically has 103 rows (3 header + 100 data)
- Cumulative columns MUST be formulas, NOT static values
- Date column MUST be date objects (not datetime)

### Fulfillment Recovery (Multi-Product)
- Three product types may share capacity constraints
- Each product may have different start dates per scenario
- Bulk/Network products may have minimum production requirements before certain dates
- 10-hour shift scenarios require counting eligible working days (often 20-24 days)

### Agricultural Harvest Planning / Automotive Manufacturing
- Three products with asymmetric constraints (different start dates, cutoffs, minimums)
- One product may have zero production in some scenarios
- Temporary capacity boosts (10-hour shifts) with specific date windows
- Minimum production requirements before early cutoffs
- Provincial/regional holidays (not US federal)
- Summary markdown file often required with exact format constraints
- Product C may use "Actual Var to PO" instead of "Cumulative Open POs"

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ValueError: Length mismatch` | Pandas reading formula cells as NaN | Use `openpyxl` directly |
| Dates show as `2018-01-22 00:00:00` | Used `datetime` instead of `date` | Use `date(2018, 1, 22)` not `datetime(2018, 1, 22)` |
| Verifier rejects date type | `datetime` has time component | Switch to `date` objects |
| Formulas appear as text | Cell typed as string | Pass formula string starting with `=` |
| Cumulative values wrong | Formula reversed or wrong signs | Use `=C4-D4` first row, `=E{prev}+C{curr}-D{curr}` subsequent |
| Weekend production not zero | Wrong weekday logic | `weekday() >= 5` for Sat/Sun |
| Verifier fails but self-checks pass | Header typo, wrong totals, format mismatch, sheet name truncation, date type | Cross-check against task spec verbatim; check sheet name lengths; check date types |
| Wrong holiday dates | Assumed holidays | Extract exact dates from task description |
| ModuleNotFoundError: pandas | PEP 668 protection | Use `--break-system-packages` or avoid pandas |
| Summary file rejected | Wrong format, missing fields, wrong on-time phrasing | Generate from computed data; copy format verbatim |
| Minimum production not met | Not tracking running totals | Calculate required daily rate based on days remaining |
| Agricultural/automotive scenario rejected | Applied wrong domain pattern | Check for minimum requirements, temporary boosts, zero-production products |
| Self-check passes but verifier fails | Internal consistency ≠ external requirements | Run explicit string-exact checks against task spec |
| Sheet name truncated | Excel 31-char limit | Truncate proactively or use shorter names; verify after creation |
| Column headers misaligned | Product C uses different header pattern | Verify "Actual Var to PO" vs "Cumulative" in requirements |

## Fallback: pandas for Value-Only Output

If formulas are NOT required and you need quick value export:
```python
import pandas as pd
df.to_excel('output.xlsx', sheet_name='Plan', index=False)
```

See `references/scenario_templates.md` for server provisioning and warehouse fulfillment examples.
See `references/agricultural_examples.md` for harvest/agricultural and automotive manufacturing domain patterns.