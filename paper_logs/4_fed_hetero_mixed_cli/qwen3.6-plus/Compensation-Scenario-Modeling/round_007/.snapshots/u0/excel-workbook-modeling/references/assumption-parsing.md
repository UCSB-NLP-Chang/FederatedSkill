# Robust Assumption Parsing Patterns

When extracting parameters from source Excel files, avoid brittle hardcoded row ranges. Source files often contain section headers, blank rows, or parameters at unexpected positions.

## The Problem: Brittle Row Ranges

```python
# WRONG: Hardcoded range misses parameters outside the range
for r in range(7, 33):  # Misses row 36 where 'Grwth' lives
    label = ws.cell(r, 2).value
    # ...
```

This fails when:
- Section headers (e.g., `--- Tax Parameters ---`) occupy rows
- Parameters appear after blank rows
- Source file layout changes between tasks

## Solution 1: Label-Based Regex Extraction (Recommended)

Parse ALL rows and extract keys from the label pattern `"Description (Key)"`:

```python
import re

assumptions = {}
for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
    label = row[1].value  # Column B (adjust as needed)
    if label and isinstance(label, str):
        # Extract key from pattern like "Annual Base Salary (BaseSal)"
        match = re.search(r'\(([A-Za-z0-9_]+)\)\s*$', label)
        if match:
            key = match.group(1)
            assumptions[key] = {
                'yr1': row[2].value,  # Column C
                'yr2': row[3].value,  # Column D
                'yr3': row[4].value,  # Column E
            }
```

This handles:
- Section headers (no key pattern → skipped)
- Blank rows (label is None → skipped)
- Parameters at any row position
- Gaps between parameter groups

## Solution 2: Explicit Key List with Fallback

If the label format is inconsistent, use an explicit key list:

```python
expected_keys = ['BaseSal', 'FPP', 'PerDiem', 'PDCap', 'PDThresh',
                 'HotelStip', 'UnifAll', 'Loy1Rate', 'Loy2Rate', 'Loy3Rate',
                 'Loy4Rate', 'Loy5Rate', 'SafeIncn', 'HlthIns', 'RetRate',
                 'WHLim', 'SSRate', 'MedRate', 'Sr5to9', 'Sr10to14',
                 'Sr15to19', 'Sr20to24', 'Sr25up', 'Grwth']

assumptions = {k: None for k in expected_keys}

for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
    label = row[1].value
    if not label or not isinstance(label, str):
        continue
    for key in expected_keys:
        if f'({key})' in label:
            assumptions[key] = {
                'yr1': row[2].value,
                'yr2': row[3].value,
                'yr3': row[4].value,
            }
            break

# Verify all keys found
missing = [k for k, v in assumptions.items() if v is None]
if missing:
    print(f"WARNING: Missing assumptions: {missing}")
```

## Validation Checklist

After parsing:
- [ ] All expected keys are present
- [ ] No None values in year columns
- [ ] Numeric values are actually numeric (not strings)
- [ ] Section headers were not accidentally parsed as parameters

## Common Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Hardcoded row range | `KeyError: 'Grwth'` | Use label-based extraction |
| Section header parsed as param | Invalid key like `'Tax Parameters'` | Check for key pattern `(Key)` |
| Blank row causes crash | `AttributeError` on None label | Check `if label and isinstance(label, str)` |
| Wrong column index | All values are None | Verify column letters match source file |