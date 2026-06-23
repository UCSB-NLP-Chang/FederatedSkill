#!/usr/bin/env python3
"""
Fill HWPX template by replacing {{placeholders}} with JSON values.
Removes layout cache (<hp:linesegarray>) from modified paragraphs to prevent rendering artifacts.
"""
import zipfile
import xml.etree.ElementTree as ET
import re
import json
import sys
import os
import tempfile

def fill_hwpx_template(template_path: str, output_path: str, data: dict) -> int:
    """
    Replace placeholders in HWPX template.
    
    Args:
        template_path: Path to input .hwpx file
        output_path: Path to write output .hwpx file  
        data: Dict mapping placeholder keys to replacement values
        
    Returns:
        Number of placeholders replaced
    """
    namespaces = {
        'hp': 'http://www.hancom.co.kr/hwpml/2010/HWPML',
        'opf': 'http://www.idpf.org/2007/opf'
    }
    
    # Preserve namespaces in output
    for prefix, uri in namespaces.items():
        ET.register_namespace(prefix, uri)
    
    placeholder_re = re.compile(r'\{\{([^}]+)\}\}')
    modified_count = 0
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract HWPX (ZIP)
        with zipfile.ZipFile(template_path, 'r') as zf:
            zf.extractall(tmpdir)
        
        section_path = os.path.join(tmpdir, 'Contents', 'section0.xml')
        if not os.path.exists(section_path):
            raise FileNotFoundError(f"Contents/section0.xml not found in {template_path}")
        
        tree = ET.parse(section_path)
        root = tree.getroot()
        
        # Process each paragraph
        for para in root.findall('.//hp:p', namespaces):
            text_elem = para.find('.//hp:t', namespaces)
            if text_elem is not None and text_elem.text:
                matches = list(placeholder_re.finditer(text_elem.text))
                if not matches:
                    continue
                    
                # Replace placeholders
                new_text = text_elem.text
                for match in matches:
                    key = match.group(1)
                    if key in data:
                        new_text = new_text.replace(match.group(0), str(data[key]))
                    else:
                        print(f"Warning: Key '{key}' not found in data", file=sys.stderr)
                
                if new_text != text_elem.text:
                    text_elem.text = new_text
                    modified_count += 1
                    
                    # CRITICAL: Remove linesegarray to prevent overlapping chars
                    linesegarray = para.find('hp:linesegarray', namespaces)
                    if linesegarray is not None:
                        para.remove(linesegarray)
        
        # Write modified XML
        tree.write(section_path, encoding='UTF-8', xml_declaration=True)
        
        # Repackage HWPX
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root_dir, dirs, files in os.walk(tmpdir):
                for file in files:
                    file_path = os.path.join(root_dir, file)
                    arcname = os.path.relpath(file_path, tmpdir)
                    zf.write(file_path, arcname)
    
    return modified_count

def verify_no_placeholders(hwpx_path: str) -> bool:
    """Check that no {{...}} placeholders remain."""
    with zipfile.ZipFile(hwpx_path, 'r') as zf:
        xml_content = zf.read('Contents/section0.xml').decode('utf-8')
        return '{{' not in xml_content

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: fill_hwpx.py <template.hwpx> <output.hwpx> <data.json>", file=sys.stderr)
        sys.exit(1)
    
    template, output, data_file = sys.argv[1:4]
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    count = fill_hwpx_template(template, output, data)
    print(f"Replaced placeholders in {count} paragraphs")
    
    if verify_no_placeholders(output):
        print("Verification passed: No placeholders remain")
    else:
        print("ERROR: Unreplaced placeholders detected", file=sys.stderr)
        sys.exit(1)
