#!/usr/bin/env python3
"""Fill placeholders in HWPX template with values from JSON.

Usage:
    python3 hwpx_fill_template.py <template.hwpx> <values.json> <output.hwpx>
"""
import zipfile
import json
import re
import sys

def fill_hwpx_template(template_path: str, json_path: str, output_path: str) -> None:
    """Replace {{placeholder}} values in HWPX template and remove stale layout caches."""
    
    # Load values from JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        values = json.load(f)
    
    # Read template
    with zipfile.ZipFile(template_path, 'r') as zf:
        files = {name: zf.read(name) for name in zf.namelist()}
    
    # Process section0.xml (main content)
    section_xml = files['Contents/section0.xml'].decode('utf-8')
    
    # Replace each placeholder
    for key, value in values.items():
        placeholder = '{{' + key + '}}'
        section_xml = section_xml.replace(placeholder, str(value))
    
    # Remove stale <hp:linesegarray> from paragraphs that had placeholders replaced
    # Pattern: find paragraphs containing </hp:t></hp:run> followed by <hp:linesegarray>
    # and remove the linesegarray element
    lineseg_pattern = r'(<hp:p[^>]*><hp:run[^>]*><hp:t>[^<]*</hp:t></hp:run>)<hp:linesegarray>.*?</hp:linesegarray>'
    section_xml = re.sub(lineseg_pattern, r'\1', section_xml, flags=re.DOTALL)
    
    files['Contents/section0.xml'] = section_xml.encode('utf-8')
    
    # Write output
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    
    print(f"Created: {output_path}")
    
    # Verify no placeholders remain
    if '{{' in section_xml and '}}' in section_xml:
        remaining = re.findall(r'\{\{[^}]+\}\}', section_xml)
        print(f"Warning: Unfilled placeholders remain: {remaining}")
    else:
        print("✓ All placeholders filled")

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python3 hwpx_fill_template.py <template.hwpx> <values.json> <output.hwpx>")
        sys.exit(1)
    fill_hwpx_template(sys.argv[1], sys.argv[2], sys.argv[3])