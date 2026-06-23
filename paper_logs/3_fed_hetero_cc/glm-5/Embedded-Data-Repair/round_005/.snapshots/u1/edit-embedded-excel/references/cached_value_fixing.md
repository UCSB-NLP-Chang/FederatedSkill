# Fixing Cached Formula Values for Verifier Compatibility

## The Problem

`openpyxl` preserves formulas when saving Excel files but does NOT evaluate them or update the cached `<v>` values in the worksheet XML. When Excel opens the file, it recalculates and displays correctly. However, automated verifiers often read the raw XML `<v>` tags directly, seeing stale or empty values.

This is especially critical for cross-rate matrices with formulas like `=ROUND(1/D8, 4)` where verifiers check the computed result.

## Detection

Check if formula cells have empty or stale cached values:

```python
import zipfile
import re

def detect_cached_values(xlsx_path):
    with zipfile.ZipFile(xlsx_path, 'r') as z:
        for name in z.namelist():
            if name.startswith('xl/worksheets/sheet'):
                xml = z.read(name).decode('utf-8')
                # Find formula cells
                matches = re.findall(r'<c r="([A-Z]+\d+)"[^>]*>.*?<f>([^<]+)</f>.*?<v>([^<]*)</v>.*?</c>', xml, re.DOTALL)
                for cell, formula, value in matches:
                    print(f"{cell}: formula={formula}, cached_v={value!r}")

detect_cached_values('/tmp/embedded.xlsx')
```

## Automated Fix

Use the provided script:

```python
import subprocess

# Auto-detect ROUND formulas and fix cached values (recommended)
subprocess.run([
    'python3', 'scripts/fix_cached_values.py',
    '/tmp/embedded.xlsx',
    '/tmp/embedded_fixed.xlsx',
    '--auto'
])

# Or fix specific cells with computed values
subprocess.run([
    'python3', 'scripts/fix_cached_values.py',
    '/tmp/embedded.xlsx',
    '/tmp/embedded_fixed.xlsx',
    'F6=1.5625',   # formula cell = expected computed value
    'E5=0.9091'    # another cell if needed
])
```

## Manual Fix (If Script Unavailable)

```python
import zipfile
import re
import io

def patch_cached_value(xlsx_bytes, cell_ref, computed_value):
    """Patch cached <v> value for a formula cell in xlsx bytes."""
    with zipfile.ZipFile(io.BytesIO(xlsx_bytes), 'r') as zin:
        entries = {name: zin.read(name) for name in zin.namelist()}

    for sheet_name in [n for n in entries if n.startswith('xl/worksheets/sheet')]:
        xml = entries[sheet_name].decode('utf-8')
        # Pattern: <c r="G4"><f>...</f><v>OLD</v></c>
        pattern = rf'(<c r="{cell_ref}"[^>]*>.*?<f>[^<]*</f><v[^>]*>)[^<]*(</v>.*?</c>)'
        if re.search(pattern, xml, re.DOTALL):
            xml = re.sub(pattern, rf'\g<1>{computed_value}\g<2>', xml, flags=re.DOTALL)
            entries[sheet_name] = xml.encode('utf-8')
            print(f"Patched {cell_ref} -> {computed_value}")

    # Rebuild xlsx
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, data in entries.items():
            zout.writestr(name, data)
    return out.getvalue()

# Usage
with open('/tmp/embedded.xlsx', 'rb') as f:
    xlsx_bytes = f.read()

# For =ROUND(1/D8, 4) with D8=0.64, computed = 1.5625
fixed = patch_cached_value(xlsx_bytes, 'F6', '1.5625')

with open('/tmp/embedded_fixed.xlsx', 'wb') as f:
    f.write(fixed)
```

## Computing Expected Values

For reciprocal formulas `=ROUND(1/X, N)`:

```python
def compute_rounded_reciprocal(source_value, decimals=4):
    """Compute what Excel's =ROUND(1/X, N) will produce."""
    return round(1.0 / source_value, decimals)

# Example: D8 = 0.64
computed = compute_rounded_reciprocal(0.64, 4)  # 1.5625
```

## Verification After Fixing

```python
import zipfile
import re

def verify_cached_value(xlsx_path, cell_ref, expected_value):
    with zipfile.ZipFile(xlsx_path, 'r') as z:
        for name in z.namelist():
            if name.startswith('xl/worksheets/sheet'):
                xml = z.read(name).decode('utf-8')
                match = re.search(rf'<c r="{cell_ref}"[^>]*>.*?<f>[^<]*</f><v>([^<]+)</v>', xml, re.DOTALL)
                if match:
                    actual = match.group(1)
                    assert actual == str(expected_value), f"Expected {expected_value}, got {actual}"
                    print(f"✓ {cell_ref} cached value = {actual}")
                    return True
    raise ValueError(f"Cell {cell_ref} not found")

verify_cached_value('/tmp/embedded_fixed.xlsx', 'F6', '1.5625')
```

## When to Apply

| Scenario | Action |
|----------|--------|
| Human opens in Excel | Not needed - Excel recalculates |
| Automated verifier reads XML | **Required** - fix cached values |
| Formula cell in verification path | **Required** - pre-compute and patch |
| Simple value cells only | Not needed |
| Cross-rate matrix with `=ROUND(1/X, N)` | **Always fix** both source and formula cells |