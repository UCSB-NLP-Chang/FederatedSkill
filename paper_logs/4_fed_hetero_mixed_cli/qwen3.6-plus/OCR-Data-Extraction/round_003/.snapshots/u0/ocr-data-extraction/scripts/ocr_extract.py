#!/usr/bin/env python3
"""Multi-strategy OCR pipeline for extracting structured data from images."""
import argparse
import csv
import re
import sys
from pathlib import Path

try:
    import pytesseract
    from PIL import Image, ImageEnhance
except ImportError:
    print("Install: pip install pytesseract pillow")
    sys.exit(1)

def run_ocr(image_path, config="", lang="eng"):
    try:
        return pytesseract.image_to_string(Image.open(image_path), lang=lang, config=config)
    except Exception as e:
        return f"ERROR: {e}"

def preprocess_and_ocr(image_path):
    img = Image.open(image_path)
    results = {}
    for cfg in ["", "--psm 6", "--psm 11"]:
        results[f"default_{cfg or 'auto'}"] = run_ocr(image_path, config=cfg)
        
    for name, proc_img in [
        ("thresh", img.convert("L").point(lambda p: 255 if p > 128 else 0)),
        ("contrast", ImageEnhance.Contrast(img).enhance(2.0)),
        ("upscale", img.resize((img.width*2, img.height*2), Image.LANCZOS))
    ]:
        for cfg in ["--psm 6", "--psm 11"]:
            tmp = Path("/tmp/ocr_proc.png")
            proc_img.save(tmp)
            results[f"{name}_{cfg}"] = run_ocr(str(tmp), config=cfg)
            tmp.unlink()
    return results

def normalize_date(date_str):
    date_str = date_str.strip()
    m = re.match(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", date_str)
    if m: return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.match(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", date_str)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), m.group(3)
        if a > 12: return f"{y}-{b:02d}-{a:02d}"
        if b > 12: return f"{y}-{a:02d}-{b:02d}"
        return f"{y}-{b:02d}-{a:02d}"
    m = re.match(r"(\d{1,2})[-/](\d{4})", date_str)
    if m: return f"{m.group(2)}-{int(m.group(1)):02d}-01"
    return date_str

def normalize_price(price_str):
    """Extract numeric price value without rounding/formatting."""
    m = re.search(r"(\d+\.?\d*)", price_str.replace(",", ""))
    return float(m.group(1)) if m else price_str

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run multi-strategy OCR and extract dates/prices")
    parser.add_argument("--input-dir", required=True, help="Directory containing images")
    parser.add_argument("--output", default="ocr_output.csv", help="Output CSV path")
    args = parser.parse_args()

    rows = []
    for img in sorted(Path(args.input_dir).glob("*.jpg")):
        print(f"Processing {img.name}...")
        ocr_data = preprocess_and_ocr(img)
        full_text = "\n".join(ocr_data.values())
        
        dates = re.findall(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b|\b\d{1,2}[-/]\d{4}\b", full_text)
        prices = re.findall(r"(?:RM|MYR|\$|€)?\s*(\d+\.\d{2})", full_text)
        
        rows.append({
            "filename": img.name,
            "raw_text": full_text[:200],
            "dates": [normalize_date(d) for d in dates],
            "prices": [normalize_price(p) for p in prices]
        })

    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "raw_text", "dates", "prices"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {args.output}")