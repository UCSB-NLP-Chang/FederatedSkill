#!/usr/bin/env python3
"""
Extract travel claim data from images with roster merging.
Handles claim codes with multiple label variants, multi-line amounts,
and lookup against employee/trip roster.

Usage:
    python extract_travel_claims.py --img-dir ./claims --roster roster.csv --output claims.xlsx

Environment variables:
    IMG_DIR: Directory containing claim images
    ROSTER_FILE: Path to CSV with claim_code,employee_id,trip_id columns
    OUTPUT: Output Excel file path
"""

import os
import re
import csv
import glob
import argparse
from PIL import Image
import pytesseract
import openpyxl
from openpyxl import Workbook


def load_roster(roster_path):
    """Load claim_code → employee_id, trip_id mapping from CSV."""
    roster = {}
    if not roster_path or not os.path.exists(roster_path):
        return roster

    with open(roster_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Try common column names for claim code
            claim_code = None
            for key in ['claim_code', 'ClaimCode', 'claim_ref', 'reference']:
                if key in row and row[key]:
                    claim_code = row[key].strip().upper()
                    break

            if claim_code:
                roster[claim_code] = {
                    'employee_id': row.get('employee_id', row.get('EmployeeID', row.get('emp_id', None))),
                    'trip_id': row.get('trip_id', row.get('TripID', row.get('trip', None)))
                }
    return roster


def ocr_with_fallbacks(image_path, min_length=10):
    """Extract text using multiple preprocessing strategies."""
    img = Image.open(image_path)

    strategies = [
        lambda i: i,  # Original
        lambda i: i.convert('L'),  # Grayscale
        lambda i: i.convert('L').point(lambda x: 0 if x < 100 else 255, '1'),  # Binarize
        lambda i: Image.eval(i.convert('L'), lambda x: 255 - x),  # Inverted
    ]

    psms = [6, 3, 4, 11]  # Page segmentation modes

    for strategy in strategies:
        try:
            processed = strategy(img)
            text = pytesseract.image_to_string(processed)
            if len(text.strip()) >= min_length:
                return text
        except Exception:
            continue

    # Fallback to PSM variations
    for psm in psms:
        try:
            text = pytesseract.image_to_string(img, config=f'--psm {psm}')
            if len(text.strip()) >= min_length:
                return text
        except Exception:
            continue

    return ""


def extract_claim_code(text):
    """
    Extract claim code with multiple label priority.
    Returns code or None.
    """
    text_upper = text.upper()

    # Priority: explicit labels
    patterns = [
        r'CLAIM\s*(?:CODE|REF|REFERENCE)[:\s#]+([A-Z0-9-]+)',
        r'EXPENSE\s*(?:CODE|REF)[:\s#]+([A-Z0-9-]+)',
        r'REF(?:ERENCE)?[:\s#]+([A-Z0-9-]+)',
        r'\b(CLM-\d{4}-\d{3,})',  # CLM-YYYY-NNN pattern
        r'\b(EXP-\d{4}-\d{3,})',  # EXP-YYYY-NNN pattern
    ]

    for pattern in patterns:
        match = re.search(pattern, text_upper)
        if match:
            return match.group(1).strip()
    return None


def extract_date(text):
    """
    Extract date from multiple formats.
    Returns ISO format YYYY-MM-DD or None.
    """
    # Patterns for various date formats
    patterns = [
        # DD/MM/YYYY or DD-MM-YYYY
        (r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', 'dmy'),
        # YYYY/MM/DD or YYYY-MM-DD
        (r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', 'ymd'),
        # MM/YYYY (day = 01)
        (r'(\d{1,2})[/-](\d{4})', 'my'),
    ]

    for pattern, fmt in patterns:
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            try:
                if fmt == 'dmy' and len(groups) == 3:
                    day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                    # Heuristic: if first > 12, it's likely day
                    if day > 12:
                        return f"{year:04d}-{month:02d}-{day:02d}"
                    else:
                        # Ambiguous - assume DD/MM for travel claims
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


def extract_amount(text):
    """
    Extract total amount with keyword priority.
    Handles multi-line formats where keyword and amount are on separate lines.
    Returns raw float or None (no formatting/rounding).
    """
    text_upper = text.upper()

    # Lines for multi-line parsing
    lines = [l.strip() for l in text_upper.split('\n') if l.strip()]

    # Priority keywords for valid claim amounts
    valid_keywords = ['REIMBURSABLE', 'TOTAL CLAIM', 'AMOUNT CLAIMED',
                      'TOTAL DUE', 'BALANCE DUE', 'GRAND TOTAL']
    # Keywords to exclude (not valid claim amounts)
    exclude_keywords = ['ADVANCE', 'TIP', 'DEPOSIT', 'GRATUITY']

    # Pattern for amount value
    amount_pattern = r'(?:RM|MYR|\$|€|£)?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'

    # Strategy 1: Keyword and amount on same line
    for keyword in valid_keywords:
        for line in lines:
            if keyword in line:
                # Check exclusion
                if any(ex in line for ex in exclude_keywords):
                    continue
                match = re.search(amount_pattern, line)
                if match:
                    try:
                        return float(match.group(1).replace(',', ''))
                    except ValueError:
                        continue

    # Strategy 2: Multi-line - amount on line following keyword
    for i, line in enumerate(lines):
        for keyword in valid_keywords:
            if keyword in line:
                # Check next line for amount
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if any(ex in next_line for ex in exclude_keywords):
                        continue
                    match = re.search(amount_pattern, next_line)
                    if match:
                        try:
                            return float(match.group(1).replace(',', ''))
                        except ValueError:
                            continue

    # Strategy 3: Any valid amount pattern (fallback)
    for line in lines:
        if any(ex in line for ex in exclude_keywords):
            continue
        match = re.search(r'(?:TOTAL|AMOUNT|DUE)[^\d]*(\d+\.\d{2})', line)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue

    return None


def process_claims(img_dir, roster_path, output_path):
    """Process all claim images and generate Excel output."""
    # Load roster
    roster = load_roster(roster_path)
    print(f"Loaded {len(roster)} entries from roster")

    # Discover images
    image_paths = sorted(glob.glob(os.path.join(img_dir, '*.*')))
    image_paths = [p for p in image_paths
                   if p.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff'))]

    print(f"Found {len(image_paths)} images")

    # Process each image
    results = []
    unmatched_claims = []

    for img_path in image_paths:
        filename = os.path.basename(img_path)
        print(f"Processing: {filename}")

        # OCR
        text = ocr_with_fallbacks(img_path)

        # Extract fields
        claim_code = extract_claim_code(text)
        date = extract_date(text)
        amount = extract_amount(text)

        # Roster lookup
        if claim_code and claim_code.upper() in roster:
            emp_id = roster[claim_code.upper()]['employee_id']
            trip_id = roster[claim_code.upper()]['trip_id']
        else:
            emp_id = None
            trip_id = None
            if claim_code:
                unmatched_claims.append((filename, claim_code))

        results.append({
            'filename': filename,
            'claim_code': claim_code,
            'employee_id': emp_id,
            'trip_id': trip_id,
            'date': date,
            'total_amount': amount
        })

        print(f"  Code: {claim_code}, Date: {date}, Amount: {amount}, Emp: {emp_id}, Trip: {trip_id}")

    # Log unmatched
    if unmatched_claims:
        print(f"\nWarning: {len(unmatched_claims)} claim(s) not in roster:")
        for filename, code in unmatched_claims:
            print(f"  {filename}: {code}")

    # Write Excel
    wb = Workbook()
    ws = wb.active
    ws.title = 'claims'

    # Headers
    ws.append(['filename', 'claim_code', 'employee_id', 'trip_id', 'date', 'total_amount'])

    # Data - write raw values (None becomes empty cell, amount as raw float)
    for row in results:
        ws.append([
            row['filename'],
            row['claim_code'],
            row['employee_id'],
            row['trip_id'],
            row['date'],
            row['total_amount']  # Raw float, no formatting
        ])

    wb.save(output_path)
    print(f"\nSaved {len(results)} rows to {output_path}")

    return results


def main():
    parser = argparse.ArgumentParser(description='Extract travel claims from images')
    parser.add_argument('--img-dir', default=os.environ.get('IMG_DIR', '/app/workspace/dataset/img'),
                        help='Directory containing claim images')
    parser.add_argument('--roster', default=os.environ.get('ROSTER_FILE', ''),
                        help='Path to roster CSV file')
    parser.add_argument('--output', default=os.environ.get('OUTPUT', '/app/workspace/travel_claims.xlsx'),
                        help='Output Excel file path')
    args = parser.parse_args()

    process_claims(args.img_dir, args.roster, args.output)


if __name__ == '__main__':
    main()