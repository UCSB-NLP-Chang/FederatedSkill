#!/usr/bin/env python3
"""Directly edit existing text values in HWPX files via string replacement.

Use when the HWPX contains literal text to replace (not {{placeholder}} patterns).

Usage: python3 edit_hwpx.py <input.hwpx> <replacements.json> <output.hwpx>

replacements.json format:
{
  "old text value": "new text value",
  "another old value": "another new value"
}

The script performs exact string replacement on all Contents/section*.xml files,
removes <hp:linesegarray> elements from modified paragraphs, and repackages.
"""
import sys
import zipfile
import json
import re


def edit_hwpx(input_path, replacements_path, output_path):
    with open(replacements_path, 'r', encoding='utf-8') as f:
        replacements = json.load(f)

    with zipfile.ZipFile(input_path, 'r') as zin:
        namelist = zin.namelist()
        section_files = [n for n in namelist if n.startswith('Contents/section') and n.endswith('.xml')]

        modified_xmls = {}
        for sec_file in section_files:
            xml_content = zin.read(sec_file).decode('utf-8')
            original = xml_content

            for old_text, new_text in replacements.items():
                xml_content = xml_content.replace(old_text, new_text)

            if xml_content != original:
                # Remove layout cache from modified paragraphs
                xml_content = re.sub(r'<hp:linesegarray>.*?</hp:linesegarray>', '', xml_content, flags=re.DOTALL)
                modified_xmls[sec_file] = xml_content

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name in namelist:
            if name in modified_xmls:
                zout.writestr(name, modified_xmls[name])
            else:
                zout.writestr(name, zin.read(name))

    # Verify no old_text values remain
    with zipfile.ZipFile(output_path, 'r') as zout:
        for sec_file in section_files:
            content = zout.read(sec_file).decode('utf-8')
            for old_text in replacements:
                if old_text in content:
                    print(f"Warning: Unreplaced text remains in {sec_file}: {old_text}")
                    return False

    print(f"HWPX edited successfully. Modified {len(modified_xmls)} section(s).")
    return True


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: edit_hwpx.py <input.hwpx> <replacements.json> <output.hwpx>")
        sys.exit(1)
    success = edit_hwpx(sys.argv[1], sys.argv[2], sys.argv[3])
    sys.exit(0 if success else 1)
