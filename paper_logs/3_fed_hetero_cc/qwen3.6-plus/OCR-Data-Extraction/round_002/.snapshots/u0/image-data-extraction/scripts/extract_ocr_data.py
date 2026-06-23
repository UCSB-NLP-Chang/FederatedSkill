#!/usr/bin/env python3
"""Extract dates and prices from images using OCR with multi-pass preprocessing."""

import os
import re
import sys
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from openpyxl import Workbook

# Configuration
IMG_DIR = os.environ.get("IMG_DIR", "/app/workspace/dataset/img")
OUTPUT = os.environ.get("OUTPUT", "/app/workspace/output.xlsx")

def preprocess(image, mode="default"):
    """Apply preprocessing to improve OCR accuracy."""
    if mode == "default":
        return image
    elif mode == "grayscale":
        return image.convert("L")
    elif mode == "high_contrast":
        gray = image.convert("L")
        return ImageEnhance.Contrast(gray).enhance(2.5)
    elif mode == "threshold":
        gray = image.convert("L")
        return gray.point(lambda x: 255 if x > 127 else 0, "1")
    elif mode == "upscale":
        w, h = image.size
        return image.resize((w * 2, h * 2), Image.LANCZOS)
    return image

def ocr_image(image_path):
    """Run OCR with multiple preprocessing strategies and PSM configs."""
    img = Image.open(image_path)
    all_text_parts = []
    modes = ["default", "grayscale", "high_contrast", "threshold", "upscale"]
    psm_configs = ["--psm 6 -l eng", "--psm 4 -l eng", "--psm 3 -l eng", "--psm 1 -l eng"]

    for mode in modes:
        processed = preprocess(img, mode)
        for config in psm_configs:
            try:
                text = pytesseract.image_to_string(processed, config=config)
                if text.strip():
                    all_text_parts.append(text)
            except Exception:
                pass
    return "\n".join(all_text_parts)

def parse_date_str(parts, ambiguous_dd_mm=True):
    """Parse date components into ISO YYYY-MM-DD."""
    if len(parts) == 2:
        a, b = int(parts[0]), int(parts[1])
        if len(parts[1]) == 4 and 1 <= a <= 12:
            return f"{b:04d}-{a:02d}-01"
        elif len(parts[0]) == 4 and 1 <= b <= 12:
            return f"{a:04d}-{b:02d}-01"
    elif len(parts) == 3:
        a, b, c = [int(x) for x in parts]
        if c < 100:
            c += 2000
        if a > 12:
            return f"{c:04d}-{b:02d}-{a:02d}"
        elif b > 12:
            return f"{c:04d}-{a:02d}-{b:02d}"
        elif ambiguous_dd_mm:
            return f"{c:04d}-{b:02d}-{a:02d}"
        else:
            return f"{c:04d}-{a:02d}-{b:02d}"
    return None

def extract_date(text):
    """Extract and normalize the first valid date from OCR text."""
    date_patterns = [
        r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',
        r'(\d{1,2})[/-](\d{4})'
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            return parse_date_str(match.groups())
    return None

def extract_price(text):
    """Extract price from OCR text, handling currency symbols.

    Returns raw float value (no rounding) - verifier decides precision tolerance.
    """
    price_patterns = [
        r'(?:RM|MYR|\$|€|£)\s*(\d+\.?\d*)',
        r'(\d+\.?\d*)\s*(?:RM|MYR|\$|€|£)'
    ]
    for pattern in price_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None

def main():
    if not os.path.isdir(IMG_DIR):
        print(f"Error: Image directory {IMG_DIR} not found.")
        sys.exit(1)

    wb = Workbook()
    ws = wb.active
    ws.title = "products"
    ws.append(["filename", "date", "price"])

    files = sorted([f for f in os.listdir(IMG_DIR) if f.lower().endswith('.png', '.jpg', '.jpeg')])

    for fname in files:
        fpath = os.path.join(IMG_DIR, fname)
        print(f"Processing {fname}...")
        text = ocr_image(fpath)

        date = extract_date(text)
        price = extract_price(text)

        print(f"  Date: {date}, Price: {price}")
        ws.append([fname, date, price])

    wb.save(OUTPUT)
    print(f"\nResults saved to {OUTPUT}")

if __name__ == "__main__":
    main()