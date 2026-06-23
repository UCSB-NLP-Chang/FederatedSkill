#!/usr/bin/env python3
"""
Safe extraction and repacking of PPTX files preserving structure.
Includes utilities for adding new slides with proper content type registration.
"""

import zipfile
import os
import shutil
import tempfile
import xml.etree.ElementTree as ET

def extract_pptx(pptx_path, extract_dir=None):
    """Extract pptx to directory, return extraction path."""
    if extract_dir is None:
        extract_dir = tempfile.mkdtemp(prefix='pptx_extract_')
    
    with zipfile.ZipFile(pptx_path, 'r') as zf:
        zf.extractall(extract_dir)
    
    return extract_dir

def repack_pptx(extract_dir, output_path):
    """Repack directory into pptx with proper compression."""
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, extract_dir)
                zf.write(file_path, arcname)

def modify_slide_xml(extract_dir, slide_num, modifier_func):
    """Modify a specific slide's XML using callback function.
    
    modifier_func receives XML string, returns modified XML string.
    """
    slide_path = os.path.join(extract_dir, f'ppt/slides/slide{slide_num}.xml')
    
    with open(slide_path, 'r', encoding='utf-8') as f:
        xml = f.read()
    
    modified = modifier_func(xml)
    
    with open(slide_path, 'w', encoding='utf-8') as f:
        f.write(modified)

def add_content_type(extract_dir, part_name, content_type):
    """Register a new part in [Content_Types].xml.
    
    Args:
        extract_dir: Extraction root directory
        part_name: Part name with leading slash (e.g., "/ppt/slides/slide7.xml")
        content_type: Content type string
    """
    ct_path = os.path.join(extract_dir, '[Content_Types].xml')
    
    with open(ct_path, 'r', encoding='utf-8') as f:
        xml = f.read()
    
    # Check if already exists
    if f'PartName="{part_name}"' in xml:
        return
    
    # Parse and add
    root = ET.fromstring(xml)
    ns = 'http://schemas.openxmlformats.org/package/2006/content-types'
    override = ET.Element('{%s}Override' % ns)
    override.set('PartName', part_name)
    override.set('ContentType', content_type)
    root.append(override)
    
    # Write back with declaration
    tree = ET.ElementTree(root)
    tree.write(ct_path, xml_declaration=True, encoding='UTF-8')

def add_slide_content_type(extract_dir, slide_num):
    """Convenience function to register a new slide."""
    part_name = f"/ppt/slides/slide{slide_num}.xml"
    content_type = "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"
    add_content_type(extract_dir, part_name, content_type)

# Example usage
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <pptx_file> [output_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.pptx', '_modified.pptx')
    
    # Extract
    temp_dir = extract_pptx(input_file)
    print(f"Extracted to: {temp_dir}")
    
    # Example modification: replace font
    def replace_arial(xml):
        return xml.replace('typeface="Calibri"', 'typeface="Arial"')
    
    modify_slide_xml(temp_dir, 1, replace_arial)
    
    # Repack
    repack_pptx(temp_dir, output_file)
    print(f"Saved to: {output_file}")
    
    # Cleanup
    shutil.rmtree(temp_dir)
