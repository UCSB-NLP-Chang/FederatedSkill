#!/usr/bin/env python3
"""
Template for OCR extraction merged with reference data.
Extracts claim codes from images, looks up employee/trip data from CSV roster.

Adapt regex patterns and column names for your specific use case.
"""
import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from openpyxl import Workbook


def load_reference(ref_path: Path, key_col: str, val_cols: list[str]) -> dict[str, dict]:
    """Load reference CSV as lookup dict. Keys normalized to uppercase."""
    ref = {}
    with open(ref_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = row[key_col].strip().upper()
            ref[key] = {c: row[c] for c in val_cols}
    return ref


def preprocess_image(img: Image.Image) -> Image.Image:
    """Enhance contrast and sharpen for better OCR."""
    img = img.convert('L')
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)
    return img.filter(ImageFilter.SHARPEN)


def ocr_extract(img_path: Path) -> str:
    """Multi-strategy OCR: default + preprocessed + multiple PSM modes."""
    img = Image.open(img_path)
    texts = []
    
    # Strategy 1: Default
    try:
        texts.append(pytesseract.image_to_string(img))
    except Exception:
        pass
    
    # Strategy 2: Preprocessed
    try:
        proc = preprocess_image(img)
        texts.append(pytesseract.image_to_string(proc))
    except Exception:
        pass
    
    # Strategy 3: PSM variants for structured text
    for psm in [6, 11, 4]:
        try:
            texts.append(pytesseract.image_to_string(img, config=f'--psm {psm}'))
        except Exception:
            pass
    
    return '\n'.join(texts)


def extract_code(text: str) -> str | None:
    """Extract claim/order code with multiple label variations."""
    patterns = [
        r'(?:CLAIM\s*(?:CODE|REF|ID)?|EXPENSE\s*(?:CODE|ID))\s*[:\-]?\s*(CLM-\d{4}-\d{3})',
        r'\b(CLM-\d{4}-\d{3})\b',  # Generic fallback
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).upper()
    return None


def extract_date(text: str) -> str | None:
    """Extract and normalize date to YYYY-MM-DD. Returns None if invalid."""
    # Try explicit labels first
    label_patterns = [
        r'(?:TRANSACTION|PURCHASE)\s*DATE\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
        r'DATE\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
    ]
    for pat in label_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return parse_date(m.group(1))
    
    # Fallback: any ISO-like date
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', text)
    if m:
        return parse_date(f"{m.group(1)}-{m.group(2)}-{m.group(3)}", 'ymd')
    
    return None


def parse_date(s: str, fmt_hint: str = 'dmy') -> str | None:
    """Parse date string to ISO format. fmt_hint: 'dmy' or 'ymd'."""
    s = s.strip()
    sep = '/' if '/' in s else '-'
    parts = s.split(sep)
    
    if len(parts) != 3:
        return None
    
    try:
        if fmt_hint == 'ymd':
            y, m, d = map(int, parts)
        else:
            d, m, y = map(int, parts)
        # Handle 2-digit years
        if y < 100:
            y += 2000 if y < 50 else 1900
        return datetime(y, m, d).strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return None


def extract_amount(text: str) -> float | None:
    """Extract total amount with multiple label variations."""
    patterns = [
        r'REIMBURSABLE\s+TOTAL\s*[:\-]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
        r'TOTAL\s+CLAIM\s*[:\-]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
        r'AMOUNT\s+CLAIMED\s*[:\-]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
        r'\b(\d{1,3}(?:,\d{3})*\.\d{2})\b',  # Last resort: any decimal
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1).replace(',', ''))
            except ValueError:
                continue
    return None


def process_claims(
    img_dir: Path,
    ref_path: Path,
    output_path: Path,
    ref_key_col: str = 'claim_code',
    ref_val_cols: list[str] = None
) -> None:
    """
    Process images and merge with reference data.
    
    Args:
        img_dir: Directory containing images
        ref_path: Path to reference CSV
        output_path: Path for output Excel file
        ref_key_col: Column name in reference to join on
        ref_val_cols: Columns to merge (None = all except key)
    """
    # Load reference
    ref_data = load_reference(ref_path, ref_key_col, ref_val_cols or [])
    
    # Determine value columns from first row if not specified
    if ref_val_cols is None and ref_data:
        first_key = next(iter(ref_data))
        ref_val_cols = list(ref_data[first_key].keys())
    
    wb = Workbook()
    ws = wb.active
    ws.title = 'claims'
    
    # Header
    headers = ['filename', 'claim_code'] + ref_val_cols + ['date', 'total_amount']
    ws.append(headers)
    
    # Process images in sorted order
    img_files = sorted(img_dir.glob('*.jpg')) + sorted(img_dir.glob('*.png'))
    
    for img_path in img_files:
        text = ocr_extract(img_path)
        code = extract_code(text)
        date = extract_date(text)
        amt = extract_amount(text)
        
        # Lookup reference (left join)
        ref_vals = ref_data.get(code.upper(), {}) if code else {}
        row_data = {
            'filename': img_path.name,
            'claim_code': code or '',
            'date': date or '',
            'total_amount': amt if amt is not None else ''
        }
        for col in ref_val_cols:
            row_data[col] = ref_vals.get(col, '')
        
        ws.append([row_data[h] for h in headers])
        print(f"Processed {img_path.name}: code={code}, date={date}, amt={amt}")
    
    wb.save(output_path)
    print(f"\nSaved {len(img_files)} records to {output_path}")


if __name__ == '__main__':
    # Example usage - adapt paths as needed
    process_claims(
        img_dir=Path('/app/workspace/dataset/img'),
        ref_path=Path('/app/workspace/dataset/claim_roster.csv'),
        output_path=Path('/app/workspace/travel_claims.xlsx'),
        ref_key_col='claim_code',
        ref_val_cols=['employee_id', 'trip_id']
    )
