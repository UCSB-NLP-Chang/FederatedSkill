---
name: excel-processing
description: Read, process, and write Excel files using Python pandas. Use when tasks require extracting data from .xlsx files, performing calculations on tabular data, or generating Excel outputs. Essential for data transformation, queue planning, capacity modeling, and any workflow involving structured spreadsheet data.
---

# Excel Data Processing with Pandas

## Quick Start

```python
import pandas as pd

# Read specific sheet
df = pd.read_excel('file.xlsx', sheet_name='SheetName')

# Write to Excel with specific sheet name
df.to_excel('output.xlsx', sheet_name='Plan', index=False)
```

## Environment Setup (PEP 668 Systems)

Modern Debian/Ubuntu systems block direct pip installs. Use the override flag:

```bash
pip install pandas openpyxl --break-system-packages -q
```

**Required packages:**
- `pandas` - Data manipulation
- `openpyxl` - Excel read/write engine

## Common Patterns

### Reading Wide/Horizontal Data
Excel files often store time-series data horizontally (weeks as columns). Use `iloc` for row-based extraction:

```python
# Row 0: headers, Row 1: week numbers, Row 2: values
weeks = df.iloc[0, 1:].values  # Skip first column (label)
values = df.iloc[2, 1:].values
```

### Writing Multi-Column Output
Maintain explicit column ordering and clear headers:

```python
output_df = pd.DataFrame({
    'Week': range(1, 41),
    'Metric_A': calc_a,
    'Metric_B': calc_b
})
output_df.to_excel('output.xlsx', sheet_name='Plan', index=False)
```

## Validation Checklist

- [ ] Verify pandas/openpyxl import successfully
- [ ] Confirm sheet names match exactly (case-sensitive)
- [ ] Check `df.shape` matches expected dimensions
- [ ] Inspect `df.columns` for unexpected unnamed columns
- [ ] Validate output file opens without errors
- [ ] Spot-check calculated values against manual computation

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ModuleNotFoundError: No module named 'pandas'` | Package not installed | Run pip install with `--break-system-packages` |
| `externally-managed-environment` error | PEP 668 protection | Use `--break-system-packages` flag |
| `Unnamed: N` columns | Empty Excel cells interpreted as headers | Specify `header=None` or clean source file |
| Sheet not found | Wrong sheet name | List sheets: `pd.ExcelFile('file.xlsx').sheet_names` |
| Data appears transposed | Wrong orientation | Check if data is row-major vs column-major |

## Anti-Patterns

- **Don't** assume default sheet name 'Sheet1' - always verify or specify
- **Don't** use `pip install` without `--break-system-packages` on modern Debian/Ubuntu
- **Don't** ignore `Unnamed:` columns - they indicate header misalignment
- **Don't** write to Excel without `index=False` unless row indices are meaningful

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Fallback: Alternative Tools

If pandas fails or is unavailable:
1. Try `openpyxl` directly for simple read/write
2. Convert to CSV intermediate: `libreoffice --headless --convert-to csv`
3. Use `xlrd` for older .xls files (separate install)