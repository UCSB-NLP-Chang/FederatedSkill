#!/usr/bin/env python3
"""Validate PPTX structure and relationships."""

import zipfile
import xml.etree.ElementTree as ET
import sys
from pathlib import Path

def validate_pptx(pptx_path):
    """Check PPTX for common structural issues."""
    issues = []
    
    with zipfile.ZipFile(pptx_path, 'r') as zf:
        # Check Content_Types.xml exists
        if '[Content_Types].xml' not in zf.namelist():
            issues.append("Missing [Content_Types].xml")
            return issues
        
        # Parse Content_Types
        ct_xml = zf.read('[Content_Types].xml')
        ct_root = ET.fromstring(ct_xml)
        
        ns = {'ct': 'http://schemas.openxmlformats.org/package/2006/content-types'}
        overrides = {o.get('PartName') for o in ct_root.findall('ct:Override', ns)}
        
        # Find all slide files
        slides = [n for n in zf.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')]
        
        for slide in slides:
            part_name = '/' + slide
            if part_name not in overrides:
                issues.append(f"Missing ContentType for {slide}")
        
        # Check presentation.xml.rels
        try:
            rels_xml = zf.read('ppt/_rels/presentation.xml.rels')
            rels_root = ET.fromstring(rels_xml)
            rels_ns = {'r': 'http://schemas.openxmlformats.org/package/2006/relationships'}
            rel_ids = [r.get('Id') for r in rels_root.findall('r:Relationship', rels_ns)]
            
            if len(rel_ids) != len(set(rel_ids)):
                issues.append("Duplicate relationship IDs in presentation.xml.rels")
        except KeyError:
            issues.append("Missing ppt/_rels/presentation.xml.rels")
        
        # Check presentation.xml slide list
        try:
            pres_xml = zf.read('ppt/presentation.xml')
            pres_root = ET.fromstring(pres_xml)
            pres_ns = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'}
            slide_ids = [s.get('id') for s in pres_root.findall('.//p:sldId', pres_ns)]
            
            if len(slide_ids) != len(set(slide_ids)):
                issues.append("Duplicate slide IDs in presentation.xml")
        except KeyError:
            issues.append("Missing ppt/presentation.xml")
    
    return issues

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <pptx_file>")
        sys.exit(1)
    
    issues = validate_pptx(sys.argv[1])
    if issues:
        print("Validation FAILED:")
        for i in issues:
            print(f"  - {i}")
        sys.exit(1)
    else:
        print("Validation PASSED")
        sys.exit(0)
