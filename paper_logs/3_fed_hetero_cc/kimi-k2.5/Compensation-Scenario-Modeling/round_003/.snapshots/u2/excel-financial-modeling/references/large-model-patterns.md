# Large Excel Model Optimization

For workbooks exceeding 500 rows or 10 sheets, standard patterns cause memory and performance issues.

## Write-Only Mode

```python
from openpyxl import Workbook

# Fastest generation, no read capability
wb = Workbook(write_only=True)
ws = wb.create_sheet('Data')

# Must use append(), cannot use cell addressing
ws.append(['Header1', 'Header2'])
for row in data:
    ws.append(row)
```

Limitations:
- Cannot read back formulas for verification
- Cannot use named ranges (must add post-creation if needed)
- Cell styling must be applied per-row during creation

## Streaming Read for Validation

```python
from openpyxl import load_workbook

# Read without loading full sheet into memory
wb = load_workbook('large.xlsx', read_only=True)
for row in wb['Data'].iter_rows(values_only=False):
    # Process row-by-row
    pass
```

## Named Range Post-Addition

When using write_only mode, add named ranges to existing file:

```python
from openpyxl import load_workbook

wb = load_workbook('generated.xlsx')  # Now in normal mode
wb.define_name('Summary_Total', 'Summary!$H$34')
wb.save('final.xlsx')
```

## Formula Externalization

For very complex tiered calculations, generate formula strings programmatically:

```python
def build_tier_formula(base_cell, tier_ranges, tier_rates):
    """Build nested IF for progressive tax/seniority tiers."""
    conditions = []
    for (low, high), rate in zip(tier_ranges, tier_rates):
        if high is None:  # Top tier
            conditions.append(f'({base_cell}>{low})*{rate}*{base_cell}')
        else:
            conditions.append(
                f'MIN(MAX({base_cell}-{low},0),{high-low})*{rate}'
            )
    return '+'.join(conditions)

# Usage
formula = build_tier_formula(
    'K2',
    [(0, 160200), (160200, 200000), (200000, None)],
    [0.1465, 0.0765, 0.0145]
)
ws['L2'] = formula  # Payroll tax calculation
```