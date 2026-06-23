#!/usr/bin/env python3
"""Harmonize clinical lab CSV data with bidirectional unit conversion testing.

Usage:
    python3 harmonize_lab_csv.py input.csv output.csv [--id-column encounter_id]
"""
import csv
import re
import sys
import argparse

# Extended plausible ranges (wider than normal to avoid converting pathological values)
PLAUSIBLE_CONVENTIONAL = {
    # Electrolytes & Metabolites
    'Glucose': (30, 700),      # mg/dL - wide range for DKA, severe hypoglycemia
    'Creatinine': (0.3, 15),   # mg/dL - wide range for AKI/CKD
    'Calcium': (6, 14),        # mg/dL - wide range for hypo/hypercalcemia
    'Magnesium': (0.5, 5),     # mg/dL - wide range for deficiency/toxicity
    # Hepatic Panel
    'Total_Bilirubin': (0.1, 30),    # mg/dL - includes cholestasis
    'Direct_Bilirubin': (0.0, 10),   # mg/dL
    'Bilirubin': (0.1, 30),          # mg/dL - generic field name
    'Albumin': (1.0, 6.0),           # g/dL - includes severe hypoalbuminemia
    'Total_Protein': (3.0, 12.0),    # g/dL
    'Hemoglobin': (5.0, 20.0),       # g/dL - includes severe anemia/polycythemia
    'Hb': (5.0, 20.0),               # g/dL - alternate name
    'Ammonia': (10, 200),            # μg/dL - hepatic encephalopathy
}

PLAUSIBLE_SI = {
    'Glucose': (2, 40),        # mmol/L
    'Creatinine': (25, 1300),   # μmol/L
    'Calcium': (1.5, 3.5),      # mmol/L
    'Magnesium': (0.2, 2),      # mmol/L
    'Total_Bilirubin': (2, 500),     # μmol/L
    'Direct_Bilirubin': (0, 170),     # μmol/L
    'Bilirubin': (2, 500),           # μmol/L
    'Albumin': (10, 60),             # g/L
    'Total_Protein': (30, 120),      # g/L
    'Hemoglobin': (50, 200),        # g/L
    'Hb': (50, 200),                # g/L
    'Ammonia': (5, 120),            # μmol/L
}

# Conversion factors (SI to Conventional)
# For multiply-type: SI_value * factor = conventional
# For divide-type: SI_value / factor = conventional
FACTORS = {
    'Glucose': 18.0,       # mmol/L * 18.0 = mg/dL
    'Creatinine': 88.4,    # μmol/L / 88.4 = mg/dL (divide-type)
    'Calcium': 4.0,        # mmol/L * 4.0 = mg/dL
    'Magnesium': 2.43,     # mmol/L * 2.43 = mg/dL
    'Total_Bilirubin': 17.1,    # μmol/L / 17.1 = mg/dL (divide-type)
    'Direct_Bilirubin': 17.1,   # μmol/L / 17.1 = mg/dL (divide-type)
    'Bilirubin': 17.1,          # μmol/L / 17.1 = mg/dL (divide-type)
    'Albumin': 10,              # g/L / 10 = g/dL (divide-type)
    'Total_Protein': 10,       # g/L / 10 = g/dL (divide-type)
    'Hemoglobin': 10,          # g/L / 10 = g/dL (divide-type)
    'Hb': 10,                  # g/L / 10 = g/dL (divide-type)
    'Ammonia': 1.7,            # μmol/L / 1.7 = μg/dL (divide-type)
}

# Which analytes use divide-type conversion (SI_value / factor = conventional)
DIVIDE_TYPE = {'Creatinine', 'Total_Bilirubin', 'Direct_Bilirubin', 'Bilirubin',
               'Albumin', 'Total_Protein', 'Hemoglobin', 'Hb', 'Ammonia'}

# Reference means for tie-breaking
REF_MEANS = {
    'Glucose': 100,        # mg/dL
    'Creatinine': 1.0,     # mg/dL
    'Calcium': 9.5,        # mg/dL
    'Magnesium': 2.0,      # mg/dL
    'Total_Bilirubin': 0.8,     # mg/dL
    'Direct_Bilirubin': 0.2,    # mg/dL
    'Bilirubin': 0.8,           # mg/dL
    'Albumin': 4.0,             # g/dL
    'Total_Protein': 7.0,       # g/dL
    'Hemoglobin': 14.0,         # g/dL
    'Hb': 14.0,                 # g/dL
    'Ammonia': 30,              # μg/dL
}


def parse_value(val_str):
    """Parse string handling scientific notation and comma decimals."""
    if not val_str or val_str.lower() in ('nan', 'na', '', 'null', 'none'):
        return None

    s = val_str.strip()

    # Handle comma as decimal separator (European format)
    # Only replace comma between digits: "142,0205" -> "142.0205"
    s = re.sub(r'(\d),(\d)', r'\1.\2', s)

    try:
        return float(s)
    except ValueError:
        return None


def bidirectional_convert(analyte, value):
    """
    Detect if value is in SI or conventional units using bidirectional testing.
    Test both conversion directions and keep the one landing in plausible range.
    Returns converted value in conventional units.
    """
    if analyte not in PLAUSIBLE_CONVENTIONAL:
        return value

    conv_min, conv_max = PLAUSIBLE_CONVENTIONAL[analyte]
    factor = FACTORS[analyte]
    ref_mean = REF_MEANS.get(analyte, (conv_min + conv_max) / 2)

    # Check if already in plausible conventional range
    if conv_min <= value <= conv_max:
        return value

    # Test both conversion directions
    if analyte in DIVIDE_TYPE:
        # Divide-type: SI_value / factor = conventional
        # So: conventional_value * factor = SI_value
        # To convert unknown to conventional: try divide (if it was SI) or multiply (if it was conv)
        result_div = value / factor   # If value was SI, this gives conventional
        result_mult = value * factor  # If value was conventional, this gives SI (wrong direction)
    else:
        # Multiply-type: SI_value * factor = conventional
        result_mult = value * factor  # If value was SI, this gives conventional
        result_div = value / factor   # If value was conventional, this gives SI (wrong direction)

    candidates = []

    # Check which results land in plausible conventional range
    if conv_min <= result_mult <= conv_max:
        candidates.append(('mult', result_mult))
    if conv_min <= result_div <= conv_max:
        candidates.append(('div', result_div))

    if len(candidates) == 0:
        # Neither direction lands in range - might be extreme pathological value
        # Keep original and let validation catch it if truly wrong
        return value

    if len(candidates) == 1:
        return candidates[0][1]

    # Tie-break: prefer result closer to reference mean
    best = min(candidates, key=lambda x: abs(x[1] - ref_mean))
    return best[1]


def process_csv(input_path, output_path, id_column='encounter_id'):
    """Process lab CSV: parse formats, convert units, round, drop incomplete rows."""
    with open(input_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames) if reader.fieldnames else []

        # Remove identifier columns from output
        id_cols = {id_column.lower(), 'id', 'patient_id', 'encounter_id'}
        output_fields = [col for col in fieldnames if col.lower() not in id_cols]

        rows_out = []
        dropped = 0

        for row in reader:
            new_row = {}
            has_missing = False

            for col in output_fields:
                raw = row.get(col, '')
                val = parse_value(raw)

                if val is None:
                    has_missing = True
                    break

                # Detect and convert units using bidirectional testing
                val = bidirectional_convert(col, val)

                # Round to 2 decimal places and format as string
                # CSV writer outputs variable decimals for floats; use string for exact 2dp
                val = round(val, 2)
                new_row[col] = f"{val:.2f}"

            if has_missing:
                dropped += 1
                continue

            rows_out.append(new_row)

    # Write with Unix line endings explicitly (CRITICAL for Windows)
    with open(output_path, 'w', newline='\n', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=output_fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"Processed {len(rows_out)} rows")
    print(f"Dropped {dropped} rows with missing values")


def main():
    parser = argparse.ArgumentParser(description='Harmonize clinical lab CSV data')
    parser.add_argument('input', help='Input CSV file')
    parser.add_argument('output', help='Output CSV file')
    parser.add_argument('--id-column', default='encounter_id',
                       help='Identifier column to remove (default: encounter_id)')

    args = parser.parse_args()
    process_csv(args.input, args.output, args.id_column)


if __name__ == '__main__':
    main()
