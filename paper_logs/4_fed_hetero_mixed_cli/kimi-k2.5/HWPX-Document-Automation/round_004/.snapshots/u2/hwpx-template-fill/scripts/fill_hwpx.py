#!/usr/bin/env python3
"""
Fill HWPX template by replacing {{placeholders}} with JSON values.
Removes layout cache (<hp:linesegarray>) from modified paragraphs to prevent rendering artifacts.
Handles multiple section files (section0.xml, section1.xml, etc.).
"""
import zipfile
import xml.etree.ElementTree as ET
import re
import json
import sys
import os
import tempfile
import glob

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
        
        # Find all section files (section0.xml, section1.xml, etc.)
        contents_dir = os.path.join(tmpdir, 'Contents')
        section_files = sorted(glob.glob(os.path.join(contents_dir, 'section*.xml')))
        
        if not section_files:
            raise FileNotFoundError(f"No section*.xml files found in Contents/ of {template_path}")
        
        for section_path in section_files:
            tree = ET.parse(section_path)
            root = tree.getroot()
            section_modified = False
            
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
                        section_modified = True
                        
                        # CRITICAL: Remove linesegarray to prevent overlapping chars
                        linesegarray = para.find('hp:linesegarray', namespaces)
                        if linesegarray is not None:
                            para.remove(linesegarray)
            
            # Write modified XML if changed
            if section_modified:
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
    """Check that no {{...}} placeholders remain in any section file."""
    with zipfile.ZipFile(hwpx_path, 'r') as zf:
        for name in zf.namelist():
            if name.startswith('Contents/section') and name.endswith('.xml'):
                xml_content = zf.read(name).decode('utf-8')
                if '{{' in xml_content:
                    return False
    return True

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
