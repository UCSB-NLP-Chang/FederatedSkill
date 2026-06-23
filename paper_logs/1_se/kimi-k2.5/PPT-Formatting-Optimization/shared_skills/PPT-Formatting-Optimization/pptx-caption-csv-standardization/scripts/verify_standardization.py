#!/usr/bin/env python3
"""
Verify PPTX caption standardization against CSV mappings.
Checks: color (6B7280), font (Arial), size (1400), bold (off), auto-numbering.
"""

import zipfile
import re
import csv
import sys
from pathlib import Path

def load_expected_captions(csv_path):
    """Load normalized site names from CSV (active records only)."""
    captions = set()
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get('reported_name') or not row.get('normalized_site'):
                continue
            if row.get('record_status') in ('ignore', 'retired'):
                continue
            captions.add(row['normalized_site'].strip())
    return captions

def verify_slide(shape_xml, expected_texts, slide_name):
    """Verify a single caption shape."""
    issues = []
    
    texts = re.findall(r'<a:t[^>]*>([^<]*)</a:t>', shape_xml)
    full_text = ''.join(texts).strip()
    
    if full_text not in expected_texts:
        return issues  # Not a caption we care about
    
    # Check color - CRITICAL: must be 6B7280, not 5B6776
    if 'val="6B7280"' not in shape_xml:
        # Check for common wrong color
        if 'val="5B6776"' in shape_xml:
            issues.append(f"{slide_name}: '{full_text}' uses wrong color 5B6776 (should be 6B7280)")
        else:
            color_match = re.search(r'val="([0-9A-Fa-f]{6})"', shape_xml)
            found = color_match.group(1) if color_match else 'none'
            issues.append(f"{slide_name}: '{full_text}' wrong color {found} (expected 6B7280)")
    
    # Check font
    if 'typeface="Arial"' not in shape_xml:
        issues.append(f"{slide_name}: '{full_text}' missing Arial font")
    
    # Check all three typeface variants
    for variant in ['latin', 'ea', 'cs']:
        if f'<a:{variant} typeface="Arial"/>' not in shape_xml:
            issues.append(f"{slide_name}: '{full_text}' missing Arial {variant} typeface")
    
    # Check size
    if 'sz="1400"' not in shape_xml:
        size_match = re.search(r'sz="(\d+)"', shape_xml)
        found = size_match.group(1) if size_match else 'none'
        issues.append(f"{slide_name}: '{full_text}' wrong size {found} (expected 1400)")
    
    # Check bold is OFF
    if 'b="1"' in shape_xml:
        issues.append(f"{slide_name}: '{full_text}' has bold enabled (should be off)")
    
    return issues

def verify_index_slide(content, slide_name, expected_captions):
    """Verify index slide has auto-numbered list with correct captions."""
    issues = []
    
    # Check for auto-numbering
    auto_num_count = len(re.findall(r'<a:buAutoNum type="arabicPeriod"/>', content))
    
    # Find all text in the slide
    texts = re.findall(r'<a:t[^>]*>([^<]*)</a:t>', content)
    
    # Check which expected captions appear
    found_captions = [t for t in texts if t in expected_captions]
    
    if len(found_captions) != len(expected_captions):
        issues.append(f"{slide_name}: expected {len(expected_captions)} captions, found {len(found_captions)}")
    
    if auto_num_count != len(expected_captions):
        issues.append(f"{slide_name}: expected {len(expected_captions)} numbered items, found {auto_num_count}")
    
    return issues, found_captions

def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <pptx_file> <csv_file>")
        sys.exit(2)
    
    pptx_path = Path(sys.argv[1])
    csv_path = Path(sys.argv[2])
    
    expected_captions = load_expected_captions(csv_path)
    print(f"Expected {len(expected_captions)} unique captions from CSV")
    
    all_issues = []
    found_captions = []
    
    with zipfile.ZipFile(pptx_path) as zf:
        for name in sorted(zf.namelist()):
            if not name.startswith('ppt/slides/slide') or not name.endswith('.xml'):
                continue
            
            content = zf.read(name).decode('utf-8')
            slide_name = Path(name).name
            
            # Check if this is the index slide
            if 'Inspection Index' in content or 'Index' in content:
                idx_issues, idx_captions = verify_index_slide(content, slide_name, expected_captions)
                all_issues.extend(idx_issues)
                found_captions.extend(idx_captions)
                continue
            
            # Check regular slides for caption shapes
            shapes = re.findall(r'<p:sp>.*?</p:sp>', content, re.DOTALL)
            for shape in shapes:
                issues = verify_slide(shape, expected_captions, slide_name)
                all_issues.extend(issues)
                
                # Track found captions
                texts = re.findall(r'<a:t[^>]*>([^<]*)</a:t>', shape)
                full_text = ''.join(texts).strip()
                if full_text in expected_captions:
                    found_captions.append(full_text)
    
    # Summary
    unique_found = set(found_captions)
    missing = expected_captions - unique_found
    
    print(f"\nFound {len(unique_found)}/{len(expected_captions)} expected captions")
    if missing:
        print(f"Missing: {missing}")
        all_issues.append(f"Missing captions: {missing}")
    
    if all_issues:
        print(f"\nFAILED: {len(all_issues)} issue(s)")
        for issue in all_issues:
            print(f"  - {issue}")
        sys.exit(1)
    
    print("\nPASSED: All captions properly standardized")
    sys.exit(0)

if __name__ == '__main__':
    main()
