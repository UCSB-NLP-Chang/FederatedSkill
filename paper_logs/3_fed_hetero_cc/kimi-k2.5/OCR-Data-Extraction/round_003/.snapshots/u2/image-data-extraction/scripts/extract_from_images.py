#!/usr/bin/env python3
"""
Extract structured data from images using OCR with robust preprocessing.
Outputs to Excel with configurable column mapping.

Usage:
    python extract_from_images.py --input-dir ./images --output results.xlsx
"""

import os
import re
import glob
import argparse
from PIL import Image
import pytesseract
import openpyxl
from openpyxl import Workbook


def extract_text_with_fallbacks(image_path, min_length=10):
    """Extract text using multiple preprocessing strategies until success."""
    try:
        img = Image.open(image_path)
        
        # Strategy 1: Original
        text = pytesseract.image_to_string(img)
        if len(text.strip()) >= min_length:
            return text
        
        # Strategy 2: Grayscale
        img_gray = img.convert('L')
        text = pytesseract.image_to_string(img_gray)
        if len(text.strip()) >= min_length:
            return text
        
        # Strategy 3: Contrast enhancement (binarization)
        img_enhanced = img_gray.point(lambda x: 0 if x < 100 else 255, '1')
        text = pytesseract.image_to_string(img_enhanced)
        if len(text.strip()) >= min_length:
            return text
        
        # Strategy 4: Inverted
        img_inverted = Image.eval(img_gray, lambda x: 255 - x)
        text = pytesseract.image_to_string(img_inverted)
        if len(text.strip()) >= min_length:
            return text
        
        # Strategy 5: Page segmentation modes
        for psm in [6, 3, 4, 11]:
            custom_config = f'--psm {psm}'
            text = pytesseract.image_to_string(img, config=custom_config)
            if len(text.strip()) >= min_length:
                return text
        
        return text  # Return last attempt even if below threshold
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return ""


def parse_date_priority(text):
    """
    Extract date using priority: EXPIRY > EXPIRES > MFG.
    Returns ISO format YYYY-MM-DD or None.
    """
    text_upper = text.upper()
    
    # Priority 1: EXPIRY/EXP patterns
    patterns_expiry = [
        (r'EXP(?:IRY)?[:\s]+(\d{1,2})[/-](\d{1,2})[/-](\d{4})', 'dmy'),  # DD/MM/YYYY
        (r'EXP(?:IRY)?[:\s]+(\d{4})[/-](\d{1,2})[/-](\d{1,2})', 'ymd'),  # YYYY/MM/DD
        (r'EXP(?:IRY)?[:\s]+(\d{1,2})[/-](\d{4})', 'my'),              # MM/YYYY (day 1)
    ]
    
    # Priority 2: EXPIRES
    patterns_expires = [
        (r'EXPIRES?[:\s]+(\d{1,2})[/-](\d{1,2})[/-](\d{4})', 'dmy'),
        (r'EXPIRES?[:\s]+(\d{1,2})[/-](\d{4})', 'my'),
    ]
    
    # Priority 3: MFG/MANUFACTURED
    patterns_mfg = [
        (r'MFG[:\s]+(\d{1,2})[/-](\d{1,2})[/-](\d{4})', 'dmy'),
        (r'MANUFACTURED[:\s]+(\d{1,2})[/-](\d{1,2})[/-](\d{4})', 'dmy'),
    ]
    
    all_patterns = [
        ('expiry', patterns_expiry),
        ('expires', patterns_expires),
        ('mfg', patterns_mfg),
    ]
    
    for source, patterns in all_patterns:
        for pattern, fmt in patterns:
            match = re.search(pattern, text_upper)
            if match:
                groups = match.groups()
                try:
                    if fmt == 'dmy' and len(groups) == 3:
                        day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                        return f"{year:04d}-{month:02d}-{day:02d}"
                    elif fmt == 'ymd' and len(groups) == 3:
                        year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                        return f"{year:04d}-{month:02d}-{day:02d}"
                    elif fmt == 'my' and len(groups) == 2:
                        month, year = int(groups[0]), int(groups[1])
                        return f"{year:04d}-{month:02d}-01"
                except ValueError:
                    continue
    return None


def parse_price(text):
    """
    Extract price using multiple currency formats.
    Returns float or None.
    """
    # Priority: Labeled PRICE > any currency prefix
    price_patterns = [
        r'PRICE[:\s]+(?:RM|MYR|\$)\s*(\d+\.\d{2})',
        r'(?:RM|MYR|\$)\s*(\d+\.\d{2})',
        r'(\d+\.\d{2})\s*(?:RM|MYR|\$)',
    ]
    
    for pattern in price_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    return None


def main():
    parser = argparse.ArgumentParser(description='Extract data from images to Excel')
    parser.add_argument('--input-dir', required=True, help='Directory containing images')
    parser.add_argument('--output', required=True, help='Output Excel file path')
    parser.add_argument('--sheet', default='products', help='Sheet name (default: products)')
    args = parser.parse_args()
    
    # Discover images
    image_paths = sorted(glob.glob(os.path.join(args.input_dir, '*.*')))
    image_paths = [p for p in image_paths if p.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff'))]
    
    print(f"Found {len(image_paths)} images")
    
    # Process each image
    results = []
    for img_path in image_paths:
        filename = os.path.basename(img_path)
        print(f"Processing: {filename}")
        
        text = extract_text_with_fallbacks(img_path)
        date = parse_date_priority(text)
        price = parse_price(text)
        
        print(f"  Date: {date}, Price: {price}")
        results.append({
            'filename': filename,
            'date': date,
            'price': price,
        })
    
    # Write Excel
    wb = Workbook()
    ws = wb.active
    ws.title = args.sheet
    
    # Headers
    ws.append(['filename', 'date', 'price'])
    
    # Data
    for row in results:
        ws.append([
            row['filename'],
            row['date'] if row['date'] else '',
            f"{row['price']:.2f}" if row['price'] is not None else ''
        ])
    
    wb.save(args.output)
    print(f"\nSaved {len(results)} rows to {args.output}")


if __name__ == '__main__':
    main()