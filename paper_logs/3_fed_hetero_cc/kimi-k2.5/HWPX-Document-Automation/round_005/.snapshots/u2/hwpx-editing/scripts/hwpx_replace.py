#!/usr/bin/env python3
"""
Replace placeholders in HWPX files with JSON values.

Usage:
    python3 hwpx_replace.py input.hwpx data.json output.hwpx

The JSON should map placeholder names (without braces) to values:
    {"회사명": "ABC Corp", "담당자": "Kim"}

Placeholders in the document should use {{name}} format.
"""

import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path


def extract_hwpx(hwpx_path: str, work_dir: Path) -> None:
    """Extract HWPX archive to working directory."""
    with zipfile.ZipFile(hwpx_path, 'r') as zf:
        zf.extractall(work_dir)


def load_replacements(json_path: str) -> dict:
    """Load placeholder mappings from JSON."""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def replace_in_xml(xml_path: Path, replacements: dict) -> tuple[bool, list[str]]:
    """
    Replace placeholders in XML file.

    Returns: (was_modified, list_of_replacements_made)
    """
    with open(xml_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    made = []

    # Find all {{placeholder}} patterns
    pattern = re.compile(r'\{\{([^}]+)\}\}')

    def replacer(match):
        key = match.group(1)
        if key in replacements:
            value = replacements[key]
            made.append(f"  {{{{{key}}}}} -> {value}")
            return value
        return match.group(0)  # keep unchanged if no mapping

    content = pattern.sub(replacer, content)

    # If any changes were made, remove ALL <hp:linesegarray> elements from this section file.
    # This is simpler and more reliable than tracking modified paragraphs.
    # Hancom Office will recalculate layout cache on next open.
    if made:
        content = re.sub(r'<hp:linesegarray>.*?</hp:linesegarray>', '', content, flags=re.DOTALL)

    if content != original:
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, made

    return False, []


def repackage_hwpx(work_dir: Path, output_path: str) -> None:
    """Create HWPX archive from working directory."""
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in work_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(work_dir)
                zf.write(file_path, arcname)


def verify_no_placeholders(hwpx_path: str) -> bool:
    """Verify no {{...}} placeholders remain in the document."""
    with zipfile.ZipFile(hwpx_path, 'r') as zf:
        for name in zf.namelist():
            if name.endswith('.xml'):
                content = zf.read(name).decode('utf-8')
                if re.search(r'\{\{[^}]+\}\}', content):
                    return False
    return True


def main():
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} input.hwpx data.json output.hwpx", file=sys.stderr)
        sys.exit(1)
    
    input_path = sys.argv[1]
    json_path = sys.argv[2]
    output_path = sys.argv[3]
    
    # Load replacements
    replacements = load_replacements(json_path)
    
    # Work in temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        work_dir = Path(tmpdir) / 'hwpx'
        
        # Extract
        extract_hwpx(input_path, work_dir)
        
        # Process all XML files in Contents/
        contents_dir = work_dir / 'Contents'
        all_made = []
        
        for xml_file in contents_dir.glob('*.xml'):
            modified, made = replace_in_xml(xml_file, replacements)
            if made:
                all_made.extend(made)
        
        # Report
        if all_made:
            print("Replacements made:")
            for m in all_made:
                print(m)
            print("\nLayout cache elements removed from modified paragraphs")
        else:
            print("No replacements made (no matching placeholders found)")
        
        # Repackage
        repackage_hwpx(work_dir, output_path)
        
        # Verify
        if verify_no_placeholders(output_path):
            print(f"\nOutput saved to: {output_path}")
            print("Verification passed: No placeholders remain in the document")
        else:
            print(f"\nOutput saved to: {output_path}")
            print("WARNING: Some placeholders may remain in the document")
            sys.exit(1)


if __name__ == '__main__':
    main()
