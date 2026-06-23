---
name: excel-openpyxl-processing
description: Read, transform, and write Excel workbooks using Python and openpyxl. Use for inventory calculations, data consolidation, and reporting when Excel automation is required. Essential when encountering PEP 668 externally-managed Python environments or missing openpyxl installations.
---

# Excel Processing with Python (openpyxl)

## Environment Setup Decision Rule

**If** `import openpyxl` fails **OR** `pip install` returns `externally-managed-environment`:

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install openpyxl -q
```

**Then** prefix all subsequent Python commands with venv activation:
```bash
source .venv/bin/activate && python3 script.py
```

**Never** use `--break-system-packages` or system pip on Debian/Ubuntu systems.

## Core Workflow

1. **Inspect**: Load workbook, print `wb.sheetnames`, sample first 5 rows of each sheet to locate headers and data offsets
2. **Extract**: Read data using `ws.iter_rows(values_only=True)`, normalizing dates and manually evaluating formula cells
3. **Calculate**: Perform all business logic in Python; do not write formulas to output cells unless explicitly required
4. **Output**: Create `openpyxl.Workbook()`, populate sheets, save with distinct filename
5. **Cleanup**: Remove `.venv` and temporary scripts after task completion

## Critical Implementation Patterns

### Mixed Date Types
Dates may be `datetime` objects or strings. Normalize immediately:
```python
if isinstance(date_val, str):
    date_val = datetime.strptime(date_val, '%Y-%m-%d').date()
elif isinstance(date_val, datetime):
    date_val = date_val.date()
```

### Formula Evaluation
Cells with formulas (e.g., `=80*C2`) return `None` when read with default settings. Either:
- Use `data_only=True` (reads cached values only if workbook was saved with values)
- **Preferred**: Manually calculate using constants from Ratio/Reference sheets found in the workbook

### Header Row Location
Do not assume headers are in row 1. Inventory sheets often have metadata in rows 1-2. Inspect first:
```python
for i, row in enumerate(ws.iter_rows(max_row=5, values_only=True), 1):
    print(f"Row {i}: {row}")
```

## Validation Checklist

- [ ] Output file exists and size > 0
- [ ] Spot-check calculations: manually verify one row's math
- [ ] Date formats are consistent (date objects, not integers or mixed strings)
- [ ] All expected SKU rows present (no accidental truncation)

## Anti-Patterns

- Do not modify input files in-place; always write to new file
- Do not assume `values_only=True` returns calculated formula results; verify for None
- Do not install packages system-wide when PEP 668 is enforced

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| `ModuleNotFoundError: No module named 'openpyxl'` | Create venv and install as shown above |
| `externally-managed-environment` | Use venv approach immediately |
| Formula cells return `None` | Calculate manually using constants from workbook |
| Dates appear as integers or strings | Normalize using `datetime.strptime` or `date()` conversion |

## References

See `references/code-patterns.md` for copy-paste templates including complete processing scripts and date utilities.
