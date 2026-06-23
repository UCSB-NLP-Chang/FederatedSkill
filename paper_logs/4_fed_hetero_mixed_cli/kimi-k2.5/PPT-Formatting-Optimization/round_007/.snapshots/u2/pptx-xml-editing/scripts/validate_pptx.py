#!/usr/bin/env python3
"""
Comprehensive PPTX validation helper.
Run after any PPTX modification to catch common errors before verifier runs.

Usage:
    python3 validate_pptx.py output.pptx [--slides 2-6 --slide7]
"""

import sys
import zipfile
import xml.etree.ElementTree as ET
import argparse
import re

NS = {
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
}


def register_namespaces():
    ET.register_namespace('', 'http://schemas.openxmlformats.org/presentationml/2006/main')
    ET.register_namespace('a', 'http://schemas.openxmlformats.org/drawingml/2006/main')
    ET.register_namespace('r', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')


def validate_basic_structure(z):
    """Check for common structural issues."""
    errors = []
    namelist = z.namelist()

    # Check for required files
    required = ['[Content_Types].xml', 'ppt/presentation.xml', 'ppt/_rels/presentation.xml.rels']
    for req in required:
        if req not in namelist:
            errors.append(f"Missing required file: {req}")

    # Check for r:r:id double prefix in presentation.xml
    pres = z.read('ppt/presentation.xml').decode('utf-8')
    if 'r:r:id' in pres:
        errors.append("Found 'r:r:id' double prefix in presentation.xml")

    # Check for duplicate xmlns
    if pres.count('xmlns=') > 1:
        errors.append("Possible duplicate xmlns in presentation.xml")

    return errors


def validate_slide_count(z, expected_count):
    """Verify slide count matches expectation."""
    errors = []
    pres = z.read('ppt/presentation.xml').decode('utf-8')
    actual_count = pres.count('<p:sldId')
    if actual_count != expected_count:
        errors.append(f"Slide count mismatch: expected {expected_count}, found {actual_count}")

    # Check slide files exist
    for i in range(1, expected_count + 1):
        slide_path = f'ppt/slides/slide{i}.xml'
        if slide_path not in z.namelist():
            errors.append(f"Missing slide file: {slide_path}")

    return errors


def validate_rid_consistency(z):
    """Check rId consistency between presentation.xml and .rels."""
    errors = []

    pres = z.read('ppt/presentation.xml').decode('utf-8')
    rels = z.read('ppt/_rels/presentation.xml.rels').decode('utf-8')

    # Extract rIds from presentation.xml
    pres_rids = set(re.findall(r'r:id="(rId\d+)"', pres))

    # Extract rIds from .rels
    rels_rids = set(re.findall(r'Id="(rId\d+)"', rels))

    # Check all presentation rIds exist in rels
    missing_in_rels = pres_rids - rels_rids
    if missing_in_rels:
        errors.append(f"rIds in presentation.xml but missing in .rels: {missing_in_rels}")

    return errors


def validate_content_types(z, expected_slides):
    """Check Content_Types has overrides for all slides."""
    errors = []
    ct = z.read('[Content_Types].xml').decode('utf-8')

    for i in range(1, expected_slides + 1):
        slide_ref = f'slide{i}.xml'
        if slide_ref not in ct:
            errors.append(f"Missing Content_Types override for {slide_ref}")

    return errors


def validate_bullets(z, slide_num, expected_texts):
    """Validate auto-numbered bullets on a slide."""
    errors = []
    slide_path = f'ppt/slides/slide{slide_num}.xml'

    if slide_path not in z.namelist():
        errors.append(f"Slide {slide_num} not found")
        return errors

    xml = z.read(slide_path).decode('utf-8')
    root = ET.fromstring(xml)

    # Find all paragraphs with buAutoNum
    bullet_paragraphs = []
    for p in root.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}p'):
        pPr = p.find('a:pPr', NS)
        if pPr is not None:
            buAutoNum = pPr.find('a:buAutoNum', NS)
            if buAutoNum is not None:
                # Check startAt value
                start_at = buAutoNum.get('startAt')
                if start_at != '1':
                    errors.append(f"Slide {slide_num}: buAutoNum startAt='{start_at}' should be '1'")

                # Extract text
                texts = []
                for r in p.findall('a:r', NS):
                    t = r.find('a:t', NS)
                    if t is not None and t.text:
                        texts.append(t.text.strip())
                bullet_paragraphs.append(''.join(texts))

    # Check expected texts
    for expected in expected_texts:
        found = any(expected in actual for actual in bullet_paragraphs)
        if not found:
            errors.append(f"Slide {slide_num}: Expected bullet text '{expected}' not found")

    return errors


def validate_text_formatting(z, slide_num, shape_name, expected_attrs):
    """Validate text formatting in a specific shape."""
    errors = []
    slide_path = f'ppt/slides/slide{slide_num}.xml'

    if slide_path not in z.namelist():
        errors.append(f"Slide {slide_num} not found")
        return errors

    xml = z.read(slide_path).decode('utf-8')
    root = ET.fromstring(xml)

    # Find shape by name
    target_sp = None
    for sp in root.iter('{http://schemas.openxmlformats.org/presentationml/2006/main}sp'):
        cnvpr = sp.find('p:nvSpPr/p:cNvPr', NS)
        if cnvpr is not None and cnvpr.get('name') == shape_name:
            target_sp = sp
            break

    if target_sp is None:
        errors.append(f"Slide {slide_num}: Shape '{shape_name}' not found")
        return errors

    # Find first rPr
    rPr = None
    for r in target_sp.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}r'):
        rPr = r.find('a:rPr', NS)
        if rPr is not None:
            break

    if rPr is None:
        errors.append(f"Slide {slide_num}: No rPr found in shape '{shape_name}'")
        return errors

    # Check attributes
    if 'sz' in expected_attrs:
        actual_sz = rPr.get('sz')
        if actual_sz != str(expected_attrs['sz']):
            errors.append(f"Slide {slide_num}: Font size {actual_sz} != expected {expected_attrs['sz']}")

    if 'bold' in expected_attrs:
        actual_b = rPr.get('b')
        if expected_attrs['bold'] is False and actual_b is not None:
            errors.append(f"Slide {slide_num}: Bold attribute present but should be removed")
        elif expected_attrs['bold'] is True and actual_b != '1':
            errors.append(f"Slide {slide_num}: Bold not set correctly")

    if 'font' in expected_attrs:
        latin = rPr.find('a:latin', NS)
        if latin is None:
            errors.append(f"Slide {slide_num}: No latin font element found")
        elif latin.get('typeface') != expected_attrs['font']:
            errors.append(f"Slide {slide_num}: Font '{latin.get('typeface')}' != expected '{expected_attrs['font']}'")

    if 'color' in expected_attrs:
        srgbClr = rPr.find('a:solidFill/a:srgbClr', NS)
        if srgbClr is None:
            errors.append(f"Slide {slide_num}: No color found")
        elif srgbClr.get('val').upper() != expected_attrs['color'].upper():
            errors.append(f"Slide {slide_num}: Color '{srgbClr.get('val')}' != expected '{expected_attrs['color']}'")

    return errors


def main():
    parser = argparse.ArgumentParser(description='Validate PPTX file structure and content')
    parser.add_argument('pptx_path', help='Path to PPTX file')
    parser.add_argument('--slides', help='Slide range to validate (e.g., 2-6)')
    parser.add_argument('--slide7', action='store_true', help='Validate slide 7 bullets')
    args = parser.parse_args()

    register_namespaces()

    try:
        z = zipfile.ZipFile(args.pptx_path, 'r')
    except Exception as e:
        print(f"FATAL: Cannot open PPTX: {e}")
        sys.exit(1)

    all_errors = []

    # Basic structure
    all_errors.extend(validate_basic_structure(z))

    # Count slides
    pres = z.read('ppt/presentation.xml').decode('utf-8')
    slide_count = pres.count('<p:sldId')
    all_errors.extend(validate_slide_count(z, slide_count))

    # rId consistency
    all_errors.extend(validate_rid_consistency(z))

    # Content types
    all_errors.extend(validate_content_types(z, slide_count))

    # Slide-specific validations
    if args.slides:
        start, end = map(int, args.slides.split('-'))
        for slide_num in range(start, end + 1):
            pass

    if args.slide7:
        expected_bullets = ['Harbor Exchange Platform', 'Civic Center Transfer Hall',
                           'Marina South Shuttle Bay', 'North Terminal Concourse']
        all_errors.extend(validate_bullets(z, 7, expected_bullets))

    z.close()

    if all_errors:
        print("VALIDATION FAILED:")
        for err in all_errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("VALIDATION PASSED")
        sys.exit(0)


if __name__ == '__main__':
    main()