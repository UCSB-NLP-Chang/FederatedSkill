#!/usr/bin/env python3
"""Fill HWPX template placeholders and clean layout cache.

Usage:
    python fill_hwpx_template.py <extracted_dir> <values.json>

The values.json should be a key-value mapping like:
    {"회사명": "세림 부품 주식회사", "담당자": "이지현"}
"""
import sys
import json
import re
import os

def fill_template(extracted_dir: str, values_file: str):
    """Replace {{placeholder}} patterns in HWPX XML files and clean layout cache."""
    
    # Load values
    with open(values_file, 'r', encoding='utf-8') as f:
        values = json.load(f)
    
    # Process each section file
    contents_dir = os.path.join(extracted_dir, 'Contents')
    
    for filename in os.listdir(contents_dir):
        if not filename.startswith('section') or not filename.endswith('.xml'):
            continue
        
        filepath = os.path.join(contents_dir, filename)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Track which paragraphs were modified
        modified_paragraphs = set()
        
        # Replace each placeholder
        for key, value in values.items():
            placeholder = '{{' + key + '}}'
            if placeholder in content:
                # Find paragraph IDs containing this placeholder
                pattern = r'<hp:p[^>]*id="(\d+)"[^>]*>.*?' + re.escape(placeholder) + r'.*?</hp:p>'
                for match in re.finditer(pattern, content, re.DOTALL):
                    modified_paragraphs.add(match.group(1))
                content = content.replace(placeholder, value)
        
        # Remove layout cache from modified paragraphs
        for para_id in modified_paragraphs:
            # Pattern to match linesegarray within a specific paragraph
            pattern = r'(<hp:p[^>]*id="' + para_id + r'"[^>]*>.*?<hp:t>[^<]*</hp:t></hp:run>)(<hp:linesegarray>.*?</hp:linesegarray>)'
            content = re.sub(pattern, r'\1', content, flags=re.DOTALL)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Updated {filename}: {len(modified_paragraphs)} paragraphs modified")
    
    print("Template filling complete")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python fill_hwpx_template.py <extracted_dir> <values.json>")
        sys.exit(1)
    fill_template(sys.argv[1], sys.argv[2])