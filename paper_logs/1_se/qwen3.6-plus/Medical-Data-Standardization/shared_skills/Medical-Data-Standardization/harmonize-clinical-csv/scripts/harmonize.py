#!/usr/bin/env python3
"""
Robust template for harmonizing clinical lab CSV data.
Handles European decimals, scientific notation, missing values, and bidirectional unit conversion.
Run: python3 harmonize.py input.csv output.csv
"""
import csv
import sys

INPUT_FILE = sys.argv[1] if len(sys.argv) > 1 else "input.csv"
OUTPUT_FILE = sys.argv[2] if len(sys.argv) > 2 else "output.csv"
DECIMAL_PLACES = 2
DROP_COLUMNS = {"encounter_id", "id", "patient_id"}

# Define plausible ranges and conversion factors.
# Ranges are intentionally widened (~20%) for clinical/diseased populations.
# op_hint suggests the primary direction, but script auto-detects.
# Factors convert SI -> Conventional.
ANALYTE_RULES = {
    "Calcium":        {"si_range": (0.8, 3.5),   "conv_range": (7.0, 12.0),   "factor": 0.25,    "op_hint": "div"},
    "Glucose":        {"si_range": (1.5, 18.0),   "conv_range": (27, 324),     "factor": 0.0555,  "op_hint": "div"},
    "Creatinine":     {"si_range": (40, 180),     "conv_range": (0.3, 12.0),   "factor": 88.4,    "op_hint": "div"},
    "Total_Bilirubin":{"si_range": (1.0, 350.0),  "conv_range": (0.06, 20.0),  "factor": 17.1,    "op_hint": "div"},
    "Albumin":        {"si_range": (20.0, 60.0),  "conv_range": (2.0, 6.0),    "factor": 10.0,    "op_hint": "div"},
    "Hemoglobin":     {"si_range": (50.0, 200.0), "conv_range": (5.0, 20.0),   "factor": 10.0,    "op_hint": "div"},
    "Ferritin":       {"si_range": (100.0, 15000.0), "conv_range": (45, 6660), "factor": 2.247,   "op_hint": "div"},
    "Free_T4":        {"si_range": (6.0, 30.0),   "conv_range": (0.5, 2.5),    "factor": 12.87,   "op_hint": "div"},
    "Free_T3":        {"si_range": (15.0, 120.0), "conv_range": (1.0, 8.0),    "factor": 15.38,   "op_hint": "div"},
    "Total_T4":       {"si_range": (60, 200),     "conv_range": (5.0, 15.0),   "factor": 12.87,   "op_hint": "div"},
    "Total_T3":       {"si_range": (0.8, 4.5),    "conv_range": (50, 300),     "factor": 64.87,   "op_hint": "mul"},
    "PTH":            {"si_range": (1.0, 15.0),   "conv_range": (10, 150),     "factor": 0.106,   "op_hint": "mul"},
    "Vitamin_D_25OH": {"si_range": (50, 250),     "conv_range": (20, 100),     "factor": 2.5,     "op_hint": "div"},
    "Magnesium":      {"si_range": (0.7, 1.1),    "conv_range": (1.5, 3.0),    "factor": 2.43,    "op_hint": "mul"},
    "Phosphorus":     {"si_range": (0.4, 2.2),    "conv_range": (1.5, 6.0),    "factor": 3.097,   "op_hint": "mul"},
    "Troponin_I":     {"si_range": (10, 50000),   "conv_range": (0.01, 50.0),  "factor": 1000,    "op_hint": "div"},
    "Troponin_T":     {"si_range": (10, 50000),   "conv_range": (0.01, 50.0),  "factor": 1000,    "op_hint": "div"},
    "BNP":            {"si_range": (1, 1000),     "conv_range": (1, 1000),     "factor": 1.0,     "op_hint": "none"},
    "NT_proBNP":      {"si_range": (1, 30000),    "conv_range": (1, 30000),    "factor": 1.0,     "op_hint": "none"},
}

def parse_value(val):
    if not val or val.strip().lower() in ("nan", "none", ""):
        return None
    val = val.strip().strip('"').replace(",", ".")
    try:
        return float(val)
    except ValueError:
        return None

def in_range(val, low, high):
    return low <= val <= high

def convert_value(val, rule):
    si_low, si_high = rule["si_range"]
    conv_low, conv_high = rule["conv_range"]
    factor = rule["factor"]
    
    # Check if already in conventional range
    if in_range(val, conv_low, conv_high):
        return val
        
    # Check if already in SI range
    if in_range(val, si_low, si_high):
        if factor == 1.0:
            return val
        div_res = val / factor
        mul_res = val * factor
        if in_range(div_res, conv_low, conv_high):
            return div_res
        if in_range(mul_res, conv_low, conv_high):
            return mul_res
        return val # Keep SI if conversion fails
        
    # Value is out of both ranges, try both conversions
    if factor == 1.0:
        return val
    div_res = val / factor
    mul_res = val * factor
    
    div_ok = in_range(div_res, conv_low, conv_high)
    mul_ok = in_range(mul_res, conv_low, conv_high)
    
    if div_ok and not mul_ok:
        return div_res
    if mul_ok and not div_ok:
        return mul_res
    if div_ok and mul_ok:
        # Prefer the one closer to the median of the conventional range
        conv_mid = (conv_low + conv_high) / 2
        if abs(div_res - conv_mid) < abs(mul_res - conv_mid):
            return div_res
        return mul_res
        
    # Neither works, keep original (might be pathological or already correct)
    return val

def main():
    rows = []
    with open(INPUT_FILE, "r") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        for row in reader:
            parsed = {}
            for k, v in row.items():
                num = parse_value(v)
                # Preserve missing values as empty strings instead of dropping rows
                parsed[k] = num if num is not None else ""
            rows.append(parsed)

    for row in rows:
        for col, val in row.items():
            if val == "":
                continue
            if col in ANALYTE_RULES:
                row[col] = convert_value(val, ANALYTE_RULES[col])
            row[col] = round(row[col], DECIMAL_PLACES)

    out_headers = [h for h in headers if h.lower() not in DROP_COLUMNS]
    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: f"{v:.{DECIMAL_PLACES}f}" if isinstance(v, float) else v for k, v in row.items() if k in out_headers})

    print(f"Wrote {len(rows)} rows to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
