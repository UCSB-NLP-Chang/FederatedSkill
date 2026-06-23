---
name: fill-hwpx-forms
description: Fill HWPX template files with JSON data by replacing placeholders in XML content, or directly edit existing text values in HWPX files. Use when given an .hwpx file and either a JSON/dict of placeholder values to populate, or a set of old→new text replacements. Handles layout cache invalidation automatically. Supports preprocessing for derived values like normalized budgets, date calculations, and appended durations.
---

# HWPX Template Filling and Direct Editing

**MANDATORY: Always use `scripts/fill_hwpx.py` for placeholder filling or `scripts/edit_hwpx.py` for direct text editing.** Do not write inline Python for extraction, replacement, or repacking. The scripts handle all fragile operations deterministically.

## Decision Tree

1. **Inspect template**: Use Python `zipfile` to list contents. Confirm `Contents/section*.xml` exist.
2. **Identify the pattern**:
   - If the XML contains `{{key}}` placeholders → use **Placeholder Filling** (below)
   - If the XML contains literal text to replace (e.g., "Northwind Retail" → "Asteron Commerce") → use **Direct Content Editing** (below)
3. **Prepare data**: Flatten nested JSON for placeholders, or build a replacement dict for direct editing.
4. **Run the appropriate script**.
5. **Verify**: Scan output for remaining placeholders or unreplaced text, and confirm ZIP integrity.

---

## Workflow A: Placeholder Filling

Run: `python3 scripts/fill_hwpx.py <template.hwpx> <data.json> <output.hwpx>`

The fill script performs **literal `{{key}}` → `value` replacement only**. Your JSON keys must exactly match the placeholder names in the XML.

### Data Preparation

**Flatten nested JSON** before filling:
```python
import json

with open('input.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

flat = {}
for section, values in data.items():
    if isinstance(values, dict):
        flat.update(values)
    elif isinstance(values, list):
        for i, item in enumerate(values, 1):
            flat[f'{section}{i}'] = item
    else:
        flat[section] = values

with open('flat.json', 'w', encoding='utf-8') as f:
    json.dump(flat, f, ensure_ascii=False, indent=2)
```

### Common transformations
- **Unit stripping**: `"32명"` → `"32"`
- **Rating reformatting**: `"4.5/5.0"` → `"4.5점 (5.0점 만점)"`
- **Text appending**: `"original"` → `"original 후속 검토 요망."`
- **Currency normalization**: `"₩450,000,000"` → `"₩450000000"`
- **Date reformatting**: `"2026-06-18"` → `"2026.06.18"`
- **Conditional mapping**: `"High"` → `"High - 즉시조치"`

### Pre-fill verification
Before running the fill script, verify all placeholders have matching keys:
```python
import re, zipfile, json

with zipfile.ZipFile('template.hwpx', 'r') as z:
    placeholders = set()
    for name in z.namelist():
        if name.startswith('Contents/section') and name.endswith('.xml'):
            content = z.read(name).decode('utf-8')
            placeholders.update(re.findall(r'\{\{(.*?)\}\}', content))

with open('data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

missing = placeholders - set(data.keys())
if missing:
    print(f"Missing keys: {missing}")
else:
    print("All placeholders covered.")
```

### Preprocessing
Run `python3 scripts/preprocess_hwpx_data.py <input.json> <output.json>` for currency normalization, date duration calculations, or phase field processing. For task-specific logic (unit stripping, custom formatting, nested flattening), write a short inline preprocessor.

---

## Workflow B: Direct Content Editing

Use when the HWPX contains **existing text values** that need to be replaced (not `{{placeholder}}` patterns).

Run: `python3 scripts/edit_hwpx.py <input.hwpx> <replacements.json> <output.hwpx>`

Where `replacements.json` is a dict of `{"old_text": "new_text", ...}`.

### How it works
The script reads all `Contents/section*.xml` files, performs exact string replacement for each old→new pair, removes `<hp:linesegarray>` elements from any modified paragraph, and repackages the archive.

### Building replacements from mixed sources
When updates come from JSON and CSV files:
```python
import json, csv

# Load JSON updates
with open('updates.json', 'r', encoding='utf-8') as f:
    json_data = json.load(f)

# Load CSV follow-ups
replacements = dict(json_data)
with open('followups.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        seq = row['sequence']
        item = row['item']
        # Map to old text pattern like "1. old follow-up alpha"
        replacements[f"{seq}. old follow-up"] = f"{seq}. {item}"

with open('replacements.json', 'w', encoding='utf-8') as f:
    json.dump(replacements, f, ensure_ascii=False, indent=2)
```

### Verification after editing
```python
import zipfile, json

with open('replacements.json', 'r', encoding='utf-8') as f:
    replacements = json.load(f)

with zipfile.ZipFile('output.hwpx', 'r') as z:
    for name in z.namelist():
        if name.startswith('Contents/section') and name.endswith('.xml'):
            content = z.read(name).decode('utf-8')
            for old_text in replacements:
                if old_text in content:
                    print(f"WARNING: Unreplaced text in {name}: {old_text}")
```

---

## How HWPX Works

HWPX files are ZIP archives containing XML. Content lives in `Contents/section*.xml`. Text is stored inside `<hp:t>` tags within `<hp:run>` elements inside `<hp:p>` paragraphs. Modifying text requires removing `<hp:linesegarray>` elements from affected paragraphs to prevent rendering overlaps. Both scripts handle this automatically.

## Verification Checklist

After any modification, verify:
1. **No unresolved placeholders** (for Workflow A): Scan XML content for remaining `{{...}}`
2. **No unreplaced text** (for Workflow B): Confirm all old_text values are gone
3. **All sections processed**: Confirm `section0.xml`, `section1.xml`, etc. were modified if they contained targets
4. **Static content preserved**: Titles, labels, and non-target text must remain unchanged
5. **ZIP integrity**: `python3 -c "import zipfile; zipfile.ZipFile('output.hwpx')"` should not raise

## Anti-patterns & Pitfalls

- **Do not write inline fill/edit logic**: Extraction, replacement, cache removal, and repacking are error-prone when done manually. Always use the scripts.
- **Do not use `xml.etree.ElementTree` or `lxml` for HWPX editing**: These struggle with HWPX namespaces (`http://www.hancom.co.kr/hwpml/2010/HWPML`) and can corrupt the document structure. String/regex replacement is faster and more reliable.
- **Do not skip preprocessing**: If values need transformation, do it before filling. The fill script does literal replacement only.
- **Do not assume flat JSON**: Input data is often nested or contains arrays. Flatten and transform before filling.
- **Do not use shell `unzip`/`zip`**: Often unavailable in constrained environments. Use Python `zipfile`.
- **Do not skip `linesegarray` removal**: Causes overlapping/garbled text in viewers.
- **Do not modify static text**: Only replace exact matches (placeholders for Workflow A, specified old_text for Workflow B).
- **Check all sections**: Process `section0.xml`, `section1.xml`, etc. The scripts do this automatically.
- **Verify coverage before running**: Missing keys or unmatched old_text cause silent failures. Run the verification steps above.
- **Always start from the original file**: If an edit attempt partially succeeds, discard the output and restart from the original. Partial modifications corrupt state.