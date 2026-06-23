#!/usr/bin/env python3
"""Verify caption formatting across all slides in extracted PPTX."""

import sys
import os
import re
from pathlib import Path

def verify_slide(slide_file, expected_captions=None):
    """Verify caption formatting in a single slide."""
    with open(slide_file) as f:
        content = f.read()
    
    issues = []
    slide_num = re.search(r'slide(\d+)\.xml', slide_file.name)
    slide_name = slide_num.group(1) if slide_num else str(slide_file)
    
    # Find all shapes
    shapes = re.findall(r'<p:sp>.*?</p:sp>', content, re.DOTALL)
    
    captions = []
    for shape in shapes:
        texts = re.findall(r'<a:t>([^<]+)</a:t>', shape)
        name_match = re.search(r'<p:cNvPr[^>]*name="([^"]*)"', shape)
        name = name_match.group(1) if name_match else "unknown"
        
        text = ' '.join(texts) if texts else ""
        
        # Identify captions by name pattern or content
        is_caption = ('文本框' in name or 'caption' in name.lower() or
                      any(kw in text.lower() for kw in ['camera', 'badge', 'elevator', 'stairwell', 'entry', 'lobby']))
        
        if is_caption and text:
            captions.append({
                'name': name,
                'text': text,
                'xml': shape,
                'is_placeholder': '<p:ph ' in shape
            })
    
    print(f"\n=== Slide {slide_name} ===")
    print(f"Found {len(captions)} caption-like shape(s)")
    
    for i, cap in enumerate(captions):
        print(f"\n  Caption {i+1}: '{cap['text'][:50]}...'" if len(cap['text']) > 50 else f"\n  Caption {i+1}: '{cap['text']}'")
        print(f"    Name: {cap['name']}")
        print(f"    Placeholder: {cap['is_placeholder']}")
        
        xml = cap['xml']
        
        # Check formatting
        checks = {
            'Font Arial': 'typeface="Arial"' in xml,
            'Size 14pt (1400)': 'sz="1400"' in xml,
            'Color #6B7280': 'val="6B7280"' in xml,
            'Center aligned': 'algn="ctr"' in xml,
            'Bold off': 'b="1"' not in xml or xml.count('b="1"') == 0,
        }
        
        for check, passed in checks.items():
            status = "✓" if passed else "✗"
            print(f"    {status} {check}")
            if not passed:
                issues.append(f"Slide {slide_name}: '{cap['text'][:30]}' - {check} failed")
        
        # Check position
        xfrm = re.search(r'<a:off x="(\d+)" y="(\d+)"', xml)
        if xfrm:
            x, y = int(xfrm.group(1)), int(xfrm.group(2))
            print(f"    Position: x={x}, y={y}")
            if y < 5000000:
                print(f"    ⚠ Position not at bottom (y should be ~6,000,000)")
                issues.append(f"Slide {slide_name}: y position {y} too high")
    
    # Check for duplicates by text similarity
    texts = [c['text'] for c in captions]
    unique = set(texts)
    if len(texts) != len(unique):
        print(f"\n  ⚠ WARNING: Duplicate captions detected!")
        issues.append(f"Slide {slide_name}: Duplicate captions")
    
    return issues

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <pptx_extract_dir>")
        print(f"Example: {sys.argv[0]} /tmp/pptx_work")
        sys.exit(1)
    
    pptx_dir = Path(sys.argv[1])
    slides_dir = pptx_dir / 'ppt' / 'slides'
    
    if not slides_dir.exists():
        print(f"Error: Slides directory not found: {slides_dir}")
        sys.exit(1)
    
    all_issues = []
    slide_files = sorted(slides_dir.glob('slide*.xml'))
    
    for slide_file in slide_files:
        issues = verify_slide(slide_file)
        all_issues.extend(issues)
    
    print(f"\n{'='*50}")
    if all_issues:
        print(f"FAIL: {len(all_issues)} issue(s) found:")
        for issue in all_issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("PASS: All captions properly formatted")
        sys.exit(0)

if __name__ == '__main__':
    main()
