---
name: pptx-caption-csv-standardization
description: Standardize floating captions in PowerPoint presentations using CSV mapping files. Use when tasks require mapping reported site names to normalized canonical names, handling partial/fuzzy matching for caption identification, applying consistent formatting (Arial 14pt, #6B7280 gray, bottom-center), and updating inspection index slides with auto-numbered lists. Critical for storm damage surveys, facility inspections, or any domain with canonical name normalization requirements.
---

# PPTX Caption CSV Standardization

Standardize site captions in PowerPoint using external CSV name mappings with strict formatting compliance.

## Required Inputs

- `*.pptx` file with caption text boxes to standardize
- `*.csv` file with columns: `reported_name`, `normalized_site`, `record_status`

## CSV Format Requirements

```csv
reported_name,normalized_site,record_status,crew
Pier 4 East Face,Pier 4 - East Face,active,Team 1
North Seawall Joint,North Seawall - Expansion Joint,active,Team 4
```

**Filter rules:** Skip rows where `reported_name` is empty, `normalized_site` is empty, or `record_status` is `ignore`/`retired`.

## Core Workflow

### 1. Load and Filter Mappings

```python
import csv

def load_caption_mappings(csv_path):
    """Load active mappings, filtering out invalid rows."""
    mappings = {}
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            if not row.get('reported_name') or not row.get('normalized_site'):
                continue
            if row.get('record_status') in ('ignore', 'retired'):
                continue
            mappings[row['reported_name'].strip()] = row['normalized_site'].strip()
    return mappings
```

### 2. Identify Caption Shapes

**CRITICAL:** Captions appear as text boxes (`<p:sp>` with `<p:cNvPr name="...">` containing patterns like "Caption" or domain-specific terms).

Match captions using **both** exact and partial strategies:
- Exact: `reported_name` matches caption text exactly
- Partial: Caption text contains key substring from `reported_name` (e.g., "Joint" matches "North Seawall Joint")

```python
def find_site_caption(shape_xml, mappings):
    """Find if shape contains a mappable site caption."""
    texts = re.findall(r'<a:t[^>]*>([^<]*)</a:t>', shape_xml)
    full_text = ''.join(texts).strip()
    
    # Exact match
    if full_text in mappings:
        return mappings[full_text]
    
    # Partial match: caption contains unique keyword
    for reported, normalized in mappings.items():
        # Extract distinctive words (avoid generic terms)
        keywords = [w for w in reported.split() if len(w) > 3]
        for kw in keywords:
            if kw in full_text and len(full_text) < len(reported) + 10:
                return normalized
    
    return None
```

### 3. Apply Strict Formatting

**MANDATORY formatting values** (errors in these cause verifier failure):

| Property | Value | XML Pattern |
|----------|-------|-------------|
| Font | Arial | `<a:latin typeface="Arial"/>` + `<a:ea typeface="Arial"/>` + `<a:cs typeface="Arial"/>` |
| Size | 14pt | `sz="1400"` (hundredths of point) |
| Color | **#6B7280** (gray-500) | `val="6B7280"` |
| Bold | Off | Omit `b="1"` entirely |
| Position | Bottom-center | `x = (12192000 - width) // 2`, `y = 5898000` |

**CRITICAL COLOR CHECK:** The color must be `6B7280`, NOT `5B6776` or similar. This is a common verifier failure point.

```python
def apply_caption_formatting(shape_xml, new_text, width_emu):
    """Apply standard formatting to caption shape."""
    SLIDE_WIDTH = 12192000
    SLIDE_HEIGHT = 6858000
    HEIGHT = 360000
    BOTTOM_MARGIN = 914400  # 1 inch
    
    # Calculate bottom-center position
    x = (SLIDE_WIDTH - width_emu) // 2
    y = SLIDE_HEIGHT - BOTTOM_MARGIN - HEIGHT  # ~5898000
    
    # Update position
    shape_xml = re.sub(
        r'<a:off x="\d+" y="\d+"',
        f'<a:off x="{x}" y="{y}"',
        shape_xml
    )
    shape_xml = re.sub(
        r'<a:ext cx="\d+" cy="\d+"',
        f'<a:ext cx="{width_emu}" cy="{HEIGHT}"',
        shape_xml
    )
    
    # Replace text content
    shape_xml = re.sub(r'<a:t>[^<]*</a:t>', f'<a:t>{new_text}</a:t>', shape_xml)
    
    # Build complete rPr element - CRITICAL: color must be 6B7280
    new_rpr = (
        '<a:rPr lang="en-US" sz="1400">'
        '<a:solidFill><a:srgbClr val="6B7280"/></a:solidFill>'
        '<a:latin typeface="Arial"/>'
        '<a:ea typeface="Arial"/>'
        '<a:cs typeface="Arial"/>'
        '</a:rPr>'
    )
    
    # Replace or insert rPr
    if re.search(r'<a:rPr[^/]*/>', shape_xml):
        shape_xml = re.sub(r'<a:rPr[^/]*/>', new_rpr, shape_xml)
    else:
        shape_xml = re.sub(r'(<a:r>)', r'\1' + new_rpr, shape_xml)
    
    # Center alignment
    if '<a:pPr' in shape_xml:
        shape_xml = re.sub(r'<a:pPr[^>]*/>', '<a:pPr algn="ctr"/>', shape_xml)
    else:
        shape_xml = re.sub(r'(<a:p>)', r'\1<a:pPr algn="ctr"/>', shape_xml)
    
    return shape_xml, x, y
```

### 4. Update Inspection Index Slide

Replace bullet list with auto-numbered captions in first-appearance order:

```python
def update_index_slide(slide_content, ordered_captions):
    """Replace index slide content with numbered list."""
    # Build numbered paragraphs
    paras_xml = []
    for caption in ordered_captions:
        para = (
            f'<a:p>'
            f'<a:pPr><a:buAutoNum type="arabicPeriod"/></a:pPr>'
            f'<a:r>'
            f'<a:rPr lang="en-US" sz="1400">'
            f'<a:solidFill><a:srgbClr val="6B7280"/></a:solidFill>'
            f'<a:latin typeface="Arial"/><a:ea typeface="Arial"/><a:cs typeface="Arial"/>'
            f'</a:rPr>'
            f'<a:t>{caption}</a:t>'
            f'</a:r>'
            f'</a:p>'
        )
        paras_xml.append(para)
    
    # Replace <a:p> elements within body placeholder
    # Find txBody and replace inner content
    return slide_content  # with paras_xml inserted
```

### 5. Verification Checklist (Run Before Declaring Done)

| Check | Command | Expected Result |
|-------|---------|---------------|
| Color correct | `grep -o 'val="6B7280"' slide*.xml \| wc -l` | Count matches caption count |
| Not 5B6776 | `grep 'val="5B6776"'` | No matches |
| Font correct | `grep 'typeface="Arial"'\` | All three typefaces present |
| Size correct | `grep 'sz="1400"'` | Present in all captions |
| Bold off | `grep 'b="1"'` | No matches in caption shapes |
| Auto-numbering | `grep 'buAutoNum type="arabicPeriod"'` | Present in index slide |

### 6. Quick Verification Script

```python
#!/usr/bin/env python3
import zipfile
import re
import sys

def verify_captions(pptx_path, expected_mappings):
    """Verify all captions match required format."""
    issues = []
    
    with zipfile.ZipFile(pptx_path) as zf:
        for name in zf.namelist():
            if not name.startswith('ppt/slides/slide') or not name.endswith('.xml'):
                continue
                
            content = zf.read(name).decode('utf-8')
            shapes = re.findall(r'<p:sp>.*?</p:sp>', content, re.DOTALL)
            
            for shape in shapes:
                texts = re.findall(r'<a:t[^>]*>([^<]*)</a:t>', shape)
                full_text = ''.join(texts).strip()
                
                # Check if this is a standardized caption
                if any(full_text == norm for norm in expected_mappings.values()):
                    # Verify formatting
                    if 'val="6B7280"' not in shape:
                        issues.append(f"{name}: '{full_text}' - wrong color (not 6B7280)")
                    if 'sz="1400"' not in shape:
                        issues.append(f"{name}: '{full_text}' - wrong size")
                    if 'typeface="Arial"' not in shape:
                        issues.append(f"{name}: '{full_text}' - wrong font")
                    if 'b="1"' in shape:
                        issues.append(f"{name}: '{full_text}' - bold should be off")
    
    if issues:
        print("VERIFICATION FAILED:")
        for i in issues:
            print(f"  {i}")
        sys.exit(1)
    print("VERIFICATION PASSED")

if __name__ == '__main__':
    verify_captions(sys.argv[1], {...})  # your expected mappings
```

## Anti-Patterns

- **DON'T** use color `5B6776` — it looks similar but fails verification. Use `6B7280`.
- **DON'T** use `unzip` command — may not be available. Use `zipfile` module.
- **DON'T** assume perfect caption name matches — implement partial matching for abbreviations.
- **DON'T** place tool names with leading spaces — `' Bash'` fails, `'Bash'` works.
- **DON'T** verify by visual inspection only — always grep for exact color/font values.
- **DON'T** forget to update all three typeface attributes: `latin`, `ea`, `cs`.

## Common Failures and Fixes

| Failure | Cause | Fix |
|---------|-------|-----|
| Color mismatch in pytest | Used `5B6776` instead of `6B7280` | Search/replace all color values |
| Missing auto-numbering | `buAutoNum` not in paragraph properties | Insert into `<a:pPr>` not `<a:rPr>` |
| Bold still on | `b="1"` attribute present | Remove attribute entirely, don't set `b="0"` |
| Caption not found | Partial name matching too strict | Expand partial matching logic |
| Tool call fails | Leading space in function name | Use exact names: `Bash`, `Read`, `Write` |

## References

- Base PPTX manipulation: `../pptx-xml-manipulation/SKILL.md`
- Caption formatting details: `../pptx-caption-standardization/SKILL.md`
