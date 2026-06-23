#!/usr/bin/env python3
"""
Neonatal Lab Harmonizer

Bidirectional unit detection for neonatal sepsis/critical care panels.
Detects US vs SI units per-analyte based on physiological thresholds.
Outputs full-precision values (NO ROUNDING).

Usage:
    python3 harmonize_neonatal.py input.csv output.csv
"""

import sys
import csv
import re
import numpy as np


def parse_value(val):
    """Parse value handling scientific notation and European decimals."""
    if val is None or str(val).lower() in ('nan', '', 'none', 'null', 'na'):
        return np.nan

    s = str(val).strip().strip('"').strip("'")
    if s.lower() in ('nan', 'none', 'null', 'na'):
        return np.nan

    # Scientific notation with comma decimal: "5,5585e+02"
    if re.match(r'^\d+,\d+e[+-]?\d+$', s, re.I):
        s = s.replace(',', '.', 1)
    # Comma decimal (no dot): "9,6056" -> "9.6056"
    elif ',' in s and '.' not in s:
        s = s.replace(',', '.')
    # Dot and comma: assume US format, remove commas
    elif ',' in s and '.' in s:
        s = s.replace(',', '')

    try:
        return float(s)
    except ValueError:
        return np.nan


# (target_unit, threshold_fn, factor, operation)
# operation: 'multiply' means value × factor (e.g., mg/dL × 88.4 = μmol/L)
# operation: 'divide' means value ÷ factor (e.g., mg/dL ÷ 9.0 = mmol/L)
CONVERSIONS = {
    'CRP_mg_L_or_mg_dL': ('mg/L', lambda v: v < 30, 10.0, 'multiply'),
    'CRP': ('mg/L', lambda v: v < 30, 10.0, 'multiply'),
    'Serum_Creat_umol_or_mgdl': ('μmol/L', lambda v: v < 20, 88.4, 'multiply'),
    'Creatinine': ('μmol/L', lambda v: v < 20, 88.4, 'multiply'),
    'BUN_mmol_or_mgdl': ('mmol/L', lambda v: v > 15, 0.357, 'multiply'),
    'BUN': ('mmol/L', lambda v: v > 15, 0.357, 'multiply'),
    'Glucose_mmol_or_mgdl': ('mmol/L', lambda v: v > 25, 0.0555, 'multiply'),
    'Glucose': ('mmol/L', lambda v: v > 25, 0.0555, 'multiply'),
    'Total_Bili_umol_or_mgdl': ('μmol/L', lambda v: v < 50, 17.1, 'multiply'),
    'Total_Bilirubin': ('μmol/L', lambda v: v < 50, 17.1, 'multiply'),
    'Direct_Bili_umol_or_mgdl': ('μmol/L', lambda v: v < 10, 17.1, 'multiply'),
    'Direct_Bilirubin': ('μmol/L', lambda v: v < 10, 17.1, 'multiply'),
    'Lactate_mgdl_or_mmol': ('mmol/L', lambda v: v > 10, 9.0, 'divide'),  # mg/dL→mmol/L
    'Lactate': ('mmol/L', lambda v: v > 10, 9.0, 'divide'),  # mg/dL→mmol/L (neonatal target)
    'Hemoglobin_gL_or_gdL': ('g/L', lambda v: v < 30, 10.0, 'multiply'),
    'Hemoglobin': ('g/L', lambda v: v < 30, 10.0, 'multiply'),
    'pCO2_kPa_or_mmHg': ('kPa', lambda v: v > 15, 7.50062, 'divide'),
    'pCO2': ('kPa', lambda v: v > 15, 7.50062, 'divide'),
}

# Analytes with no conversion needed
NO_CONVERSION = {
    'Sodium', 'Potassium', 'Chloride', 'WBC_Count', 'WBC',
    'Platelet_Count', 'Platelets', 'pH', 'pH_Arterial'
}


def convert_column(values, col_name):
    """Apply conversion to a column of values."""
    # Find matching conversion rule
    rule_key = None
    for key in CONVERSIONS:
        if key.lower() in col_name.lower() or col_name.lower() in key.lower():
            rule_key = key
            break

    if rule_key is None:
        # Check if no conversion needed
        base_name = col_name.split('_')[0]
        if any(nc.lower() in col_name.lower() for nc in NO_CONVERSION):
            return values
        return values

    target_unit, threshold_fn, factor, operation = CONVERSIONS[rule_key]
    result = []
    for v in values:
        if np.isnan(v):
            result.append(v)
            continue
        if threshold_fn(v):
            if operation == 'multiply':
                result.append(v * factor)
            else:
                result.append(v / factor)
        else:
            result.append(v)
    return result


def harmonize_neonatal(input_path, output_path):
    """Main harmonization workflow."""
    # Read input
    with open(input_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # Filter out ID columns
    id_cols = {'specimen_id', 'patient_id', 'case_id', 'patient_code', 'visit_id', 'visit_tag'}
    output_cols = [c for c in fieldnames if c not in id_cols]

    # Parse and convert
    parsed_rows = []
    for row in rows:
        parsed = {}
        has_missing = False
        for col in output_cols:
            val = parse_value(row.get(col, ''))
            if np.isnan(val):
                has_missing = True
                break
            parsed[col] = val
        if not has_missing:
            parsed_rows.append(parsed)

    # Apply conversions by column
    for col in output_cols:
        values = [r[col] for r in parsed_rows]
        converted = convert_column(values, col)
        for i, v in enumerate(converted):
            parsed_rows[i][col] = v

    # Write output - FULL PRECISION, NO ROUNDING
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=output_cols)
        writer.writeheader()
        for row in parsed_rows:
            # Write raw floats - csv module handles string conversion
            writer.writerow(row)

    print(f"Processed {len(rows)} input rows")
    print(f"Wrote {len(parsed_rows)} cleaned rows (dropped {len(rows) - len(parsed_rows)} with missing values)")
    print(f"Output columns: {output_cols}")
    return parsed_rows


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python3 harmonize_neonatal.py input.csv output.csv")
        sys.exit(1)

    harmonize_neonatal(sys.argv[1], sys.argv[2])