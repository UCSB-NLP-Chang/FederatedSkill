# Portable Verification (Python Fallback)

When system tools (`unzip`, `file`) are unavailable, use Python zipfile for verification.

## Check Archive Integrity and Remaining Placeholders

```python
import zipfile
import re

# Check archive integrity
with zipfile.ZipFile('output.hwpx', 'r') as z:
    print('Files:', z.namelist())
    # Check for remaining placeholders
    for name in z.namelist():
        if name.endswith('.xml'):
            content = z.read(name).decode('utf-8')
            if re.search(r'\{\{[^}]+\}\}', content):
                print(f'WARNING: Placeholders remain in {name}')
```

## Environment Note

Minimal environments may lack `unzip` and `file` commands. Python zipfile module is always available and provides equivalent functionality:
- Extract: `zipfile.ZipFile.extractall()`
- Create: `zipfile.ZipFile.write()`
- Verify: `zipfile.ZipFile.testzip()` returns None if valid

(Added from u2's R1 patch - addresses environment tool limitations)