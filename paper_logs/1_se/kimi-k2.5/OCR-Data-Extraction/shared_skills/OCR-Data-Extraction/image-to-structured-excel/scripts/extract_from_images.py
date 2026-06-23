#!/usr/bin/env python3
"""
Extract structured data from image collections using OCR.
Supports reference-based enrichment and multi-format date parsing.

Usage:
    python3 extract_from_images.py /path/to/images/ output.xlsx [--roster roster.csv]

Features:
- OCR with pytesseract
- Reference CSV lookup for field enrichment
- Date format auto-detection or explicit hint
- Proper empty cell handling (empty strings, not None)
- Sorted output by filename
"""

import os
import re
import sys
import csv
import argparse
from PIL import Image
import pytesseract
import openpyxl
from openpyxl import Workbook


def detect_date_format(sample_text):
    """Inspect OCR text to determine date format."""
    # Find all dates in text
    dates = re.findall(r'\d{2}/\d{2}/\d{4}', sample_text)
    for d in dates:
        parts = d.split('/')
        first, second = int(parts[0]), int(parts[1])
        if first > 12:
            return 'DD/MM'
        elif second > 12:
            return 'MM/DD'
    return 'DD/MM'  # Default


def parse_date(date_str, fmt='DD/MM'):
    """Parse date to ISO format YYYY-MM-DD."""
    date_str = date_str.strip()
    
    # Try explicit formats
    patterns = [
        (r'(\d{2})/(\d{2})/(\d{4})', fmt),
        (r'(\d{2})-(\d{2})-(\d{4})', fmt),
        (r'(\d{2})/(\d{4})', 'MM/YYYY'),
    ]
    
    for pattern, pfmt in patterns:
        m = re.search(pattern, date_str)
        if not m:
            continue
            
        if pfmt == 'DD/MM':
            return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
        elif pfmt == 'MM/DD':
            return f"{m.group(3)}-{m.group(1)}-{m.group(2)}"
        elif pfmt == 'MM/YYYY':
            return f"{m.group(2)}-{m.group(1)}-01"
    
    return None


def format_price(value):
    """Format price as string with 2 decimal places."""
    if value is None or value == '':
        return ''
    try:
        # Strip currency and whitespace
        clean = re.sub(r'[RM$Y,\s]', '', str(value))
        return f"{float(clean):.2f}"
    except (ValueError, TypeError):
        return ''


def load_roster(csv_path, key_col='claim_code', delimiter='\t'):
    """Load reference data for enrichment."""
    roster = {}
    with open(csv_path, 'r', newline='') as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        for row in reader:
            key = row.get(key_col)
            if key:
                roster[key] = {k: v for k, v in row.items() if k != key_col}
    return roster


def extract_from_image(image_path, date_format='DD/MM'):
    """Extract structured data from single image."""
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image)
    
    # Flexible patterns - customize for your use case
    patterns = {
        'claim_code': r'CLAIM CODE:\s*(CLM-\d{4}-\d+)',
        'date': r'TRANSACTION DATE:\s*([\d/]+)',
        'amount': r'(?:REIMBURSABLE TOTAL|GRAND TOTAL|TOTAL):\s*\$?([\d.]+)',
    }
    
    result = {'filename': os.path.basename(image_path), 'raw_text': text}
    
    for field, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            if field == 'date':
                result[field] = parse_date(val, date_format)
            elif field == 'amount':
                result[field] = format_price(val)
            else:
                result[field] = val
        else:
            result[field] = ''
    
    return result


def create_excel(data, output_path, sheet_name='Sheet1', extra_cols=None):
    """Create Excel with proper empty cell handling."""
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    
    # Headers
    headers = ['filename', 'claim_code', 'date', 'total_amount']
    if extra_cols:
        headers = ['filename', 'claim_code'] + extra_cols + ['date', 'total_amount']
    
    ws.append(headers)
    
    # Data rows - ensure empty strings, not None
    for row in data:
        values = []
        for h in headers:
            val = row.get(h, '')
            values.append(val if val is not None else '')
        ws.append(values)
    
    wb.save(output_path)


def main():
    parser = argparse.ArgumentParser(description='Extract data from images to Excel')
    parser.add_argument('image_dir', help='Directory containing images')
    parser.add_argument('output', help='Output Excel path')
    parser.add_argument('--roster', help='Reference CSV for enrichment')
    parser.add_argument('--sheet-name', default='claims', help='Sheet name')
    parser.add_argument('--date-format', choices=['DD/MM', 'MM/DD', 'auto'], 
                       default='auto', help='Date format hint')
    args = parser.parse_args()
    
    # Load roster if provided
    roster = {}
    if args.roster:
        roster = load_roster(args.roster)
        print(f"Loaded {len(roster)} entries from roster")
    
    # Get sorted images
    images = sorted([f for f in os.listdir(args.image_dir)
                    if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    
    if not images:
        print("No images found!")
        sys.exit(1)
    
    # Detect date format from first sample if auto
    date_fmt = args.date_format
    if date_fmt == 'auto':
        sample = pytesseract.image_to_string(
            Image.open(os.path.join(args.image_dir, images[0])))
        date_fmt = detect_date_format(sample)
        print(f"Detected date format: {date_fmt}")
    
    # Process all images
    results = []
    for img_name in images:
        img_path = os.path.join(args.image_dir, img_name)
        result = extract_from_image(img_path, date_fmt)
        
        # Enrich from roster
        code = result.get('claim_code', '')
        if code in roster:
            result.update(roster[code])
        else:
            # Ensure extra columns exist as empty strings
            for col in (list(roster.values())[0].keys() if roster else []):
                result[col] = ''
        
        results.append(result)
        print(f"Processed {img_name}: {result.get('claim_code', 'N/A')}")
    
    # Determine extra columns from roster
    extra_cols = list(list(roster.values())[0].keys()) if roster else None
    
    # Create Excel
    create_excel(results, args.output, args.sheet_name, extra_cols)
    print(f"\nSaved to {args.output}")
    
    # Summary
    matched = sum(1 for r in results if r.get('claim_code') in roster)
    print(f"Total images: {len(images)}")
    print(f"Roster matches: {matched}/{len(images)}")


if __name__ == '__main__':
    main()
