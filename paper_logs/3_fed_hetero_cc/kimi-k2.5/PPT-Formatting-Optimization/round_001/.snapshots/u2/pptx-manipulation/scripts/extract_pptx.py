#!/usr/bin/env python3
"""
Safe extraction and repacking of PPTX files preserving structure.
"""

import zipfile
import os
import shutil
import tempfile

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