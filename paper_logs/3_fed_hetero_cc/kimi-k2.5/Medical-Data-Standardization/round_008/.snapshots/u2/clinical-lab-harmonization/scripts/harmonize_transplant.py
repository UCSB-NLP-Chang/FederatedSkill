#!/usr/bin/env python3
"""
Transplant Panel Harmonizer

Merges chemistry and liver panel CSVs, applies SI→US conversions,
drops incomplete rows, outputs full-precision values (NO ROUNDING).

Usage:
    python3 harmonize_transplant.py chemistry.csv liver.csv output.csv
"""

import sys
import pandas as pd
import numpy as np


def parse_value(val):
    """Parse value handling scientific notation and European decimal commas."""
    if pd.isna(val):
        return np.nan

    s = str(val).strip().strip('"').strip("'")

    if s.lower() in ('nan', 'none', '', 'null', 'na'):
        return np.nan

    # Handle comma as decimal vs thousands separator
    if ',' in s and '.' not in s:
        # European: comma is decimal
        s = s.replace(',', '.')
    elif ',' in s and '.' in s:
        last_comma = s.rfind(',')
        last_dot = s.rfind('.')
        if last_comma > last_dot:
            # European: comma is decimal, dot is thousands
            s = s.replace('.', '').replace(',', '.')
        else:
            # US: dot is decimal, comma is thousands
            s = s.replace(',', '')

    try:
        return float(s)
    except ValueError:
        return np.nan


# (factor, operation, threshold_func)
CONVERSIONS = {
    'Creatinine': (88.4, 'divide', lambda v: v > 20),
    'Glucose': (18.0, 'multiply', lambda v: v < 3.0),
    'Bilirubin_Total': (17.1, 'divide', lambda v: v > 30),
    'Albumin': (10.0, 'divide', lambda v: v > 60),
    'Phosphorus': (3.097, 'multiply', lambda v: v < 3.0),
    'Magnesium': (2.43, 'multiply', lambda v: v < 1.0),
}


def convert_column(series, col_name):
    """Apply conversion to a column if it matches known analytes."""
    if col_name not in CONVERSIONS:
        return series

    factor, operation, threshold_fn = CONVERSIONS[col_name]

    def convert_single(val):
        if pd.isna(val):
            return val
        if threshold_fn(val):
            if operation == 'multiply':
                return val * factor
            else:
                return val / factor
        return val

    return series.apply(convert_single)


def harmonize_transplant_panel(chem_path, liver_path, output_path):
    """Main harmonization workflow for transplant panels."""
    # Read CSVs
    chem = pd.read_csv(chem_path)
    liver = pd.read_csv(liver_path)

    # Identify measurement columns (exclude IDs)
    chem_measure_cols = [c for c in chem.columns if c != 'patient_code']
    liver_measure_cols = [c for c in liver.columns if c not in ['patient_code', 'visit_tag']]

    # Parse all numeric values
    for col in chem_measure_cols:
        chem[col] = chem[col].apply(parse_value)
    for col in liver_measure_cols:
        liver[col] = liver[col].apply(parse_value)

    # Merge on patient_code (inner join for complete data only)
    merged = pd.merge(chem, liver, on='patient_code', how='inner')

    # Determine final output columns in fixed order
    output_cols = [
        'Tacrolimus', 'Creatinine', 'Magnesium', 'Potassium', 'Glucose',
        'Bilirubin_Total', 'Albumin', 'AST', 'ALT', 'Phosphorus'
    ]

    # Verify all expected columns present
    for col in output_cols:
        if col not in merged.columns:
            raise ValueError(f"Expected column '{col}' not found in merged data")

    # Drop rows with any missing measurement values
    merged = merged.dropna(subset=output_cols)

    # Apply conversions
    for col in output_cols:
        merged[col] = convert_column(merged[col], col)

    # CRITICAL: Write full precision, NO rounding, WITH headers
    # Do NOT use float_format parameter
    merged[output_cols].to_csv(output_path, index=False)

    print(f"Harmonized {len(merged)} records")
    print(f"Output columns: {output_cols}")
    return merged


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python3 harmonize_transplant.py chemistry.csv liver.csv output.csv")
        sys.exit(1)

    harmonize_transplant_panel(sys.argv[1], sys.argv[2], sys.argv[3])
