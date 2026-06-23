#!/usr/bin/env python3
"""
Fill HWPX template placeholders with JSON data.

Usage:
    python fill_hwpx_template.py <input.hwpx> <data.json> <output.hwpx>
    
Or import and call fill_hwpx_template() directly.
"""

import zipfile
import json
import re
import sys
from pathlib import Path
from datetime import datetime


def calculate_korean_age(birth_date_str: str, visit_date_str: str) -> int:
    """Calculate Korean age accounting for whether birthday passed this year."""
    birth = datetime.strptime(birth_date_str, '%Y-%m-%d')
    visit = datetime.strptime(visit_date_str, '%Y-%m-%d')
    
    age = visit.year - birth.year
    birthday_this_year = birth.replace(year=visit.year)
    if visit < birthday_this_year:
        age -= 1
    return age


def normalize_phone(phone: str) -> str:
    """Normalize phone number to hyphenated format."""
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 11 and digits.startswith('010'):
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    return phone


def fill_hwpx_template(input_path: str, data: dict, output_path: str, 
                       field_mapping: dict = None,
                       transformers: dict = None) -> dict:
    """
    Fill HWPX template with data, removing layout cache from modified paragraphs.
    
    Args:
        input_path: Path to source HWPX template
        data: Dictionary of field values
        output_path: Path for output HWPX file
        field_mapping: Optional mapping from data keys to template placeholder names
            e.g., {'phone': '전화번호'} maps data['phone'] to {{전화번호}}
        transformers: Optional dict of functions to transform values by field name
            e.g., {'생년월일': lambda v, d: f"{v} ({calculate_korean_age(v, d['방문일'])}세)"}
    
    Returns:
        Dict with 'replaced': {field: count}, 'removed_cache': count, 
        'placeholders_remaining': int, 'modified_files': list
    """
    field_mapping = field_mapping or {}
    transformers = transformers or {}
    
    # Apply transformers
    processed_data = {}
    for data_key, value in data.items():
        if data_key in transformers:
            try:
                value = transformers[data_key](value, data)
            except Exception:
                pass  # Keep original on transform failure
        processed_data[data_key] = value
    
    # Build reverse mapping: placeholder_name -> value
    placeholder_values = {}
    for data_key, value in processed_data.items():
        placeholder_name = field_mapping.get(data_key, data_key)
        placeholder_values[placeholder_name] = value
    
    with zipfile.ZipFile(input_path, 'r') as src_zip:
        file_list = src_zip.namelist()
        
        # Find XML files to process (typically Contents/section*.xml)
        xml_files = [f for f in file_list if f.endswith('.xml') and 'section' in f]
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as dst_zip:
            replaced_counts = {}
            total_cache_removed = 0
            modified_files = set()
            
            for item in src_zip.infolist():
                content = src_zip.read(item.filename)
                
                if item.filename in xml_files:
                    xml_str = content.decode('utf-8')
                    original_xml = xml_str
                    
                    # Replace placeholders
                    for placeholder, value in placeholder_values.items():
                        pattern = r'\{\{' + re.escape(placeholder) + r'\}\}'
                        count = len(re.findall(pattern, xml_str))
                        if count > 0:
                            xml_str = re.sub(pattern, str(value), xml_str)
                            replaced_counts[placeholder] = replaced_counts.get(placeholder, 0) + count
                    
                    # Remove layout cache from modified paragraphs
                    if xml_str != original_xml:
                        modified_files.add(item.filename)
                        cache_pattern = r'<hp:linesegarray>.*?</hp:linesegarray>'
                        cache_matches = re.findall(cache_pattern, xml_str, re.DOTALL)
                        total_cache_removed += len(cache_matches)
                        xml_str = re.sub(cache_pattern, '', xml_str, flags=re.DOTALL)
                    
                    content = xml_str.encode('utf-8')
                
                dst_zip.writestr(item, content)
    
    # Verify output
    with zipfile.ZipFile(output_path, 'r') as verify_zip:
        placeholders_remaining = 0
        for name in verify_zip.namelist():
            if name.endswith('.xml'):
                content = verify_zip.read(name).decode('utf-8')
                placeholders_remaining += len(re.findall(r'\{\{[^}]+\}\}', content))
    
    return {
        'replaced': replaced_counts,
        'removed_cache': total_cache_removed,
        'placeholders_remaining': placeholders_remaining,
        'modified_files': list(modified_files)
    }


def main():
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <input.hwpx> <data.json> <output.hwpx>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    json_path = sys.argv[2]
    output_path = sys.argv[3]
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Common transformers for Korean documents
    transformers = {}
    if '생년월일' in data and '방문일' in data:
        transformers['생년월일'] = lambda v, d: f"{v} ({calculate_korean_age(v, d['방문일'])}세)"
    if '회신전화' in data or '전화번호' in data:
        phone_key = '회신전화' if '회신전화' in data else '전화번호'
        transformers[phone_key] = lambda v, d: normalize_phone(v)
    
    result = fill_hwpx_template(input_path, data, output_path, transformers=transformers)
    
    print(f"Replaced fields: {result['replaced']}")
    print(f"Removed {result['removed_cache']} layout cache elements")
    print(f"Placeholders remaining: {result['placeholders_remaining']}")
    
    if result['placeholders_remaining'] > 0:
        print("WARNING: Some placeholders were not replaced!")
        sys.exit(1)
    
    print(f"SUCCESS: Output written to {output_path}")


if __name__ == '__main__':
    main()
