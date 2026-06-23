#!/usr/bin/env python3
"""
ICU Metabolic Panel Harmonizer

Parses CSV with potential mixed SI/US units, detects unit system based on
physiological thresholds, converts to US conventional units, and outputs
full-precision values (NO ROUNDING).

Usage:
    python3 icu_metabolic_harmonizer.py input.csv output.csv

For multi-file ICU data:
    # First join files on record_id, then harmonize
    python3 -c "import pandas as pd; pd.merge(...).to_csv('joined.csv', index=False)"
    python3 icu_metabolic_harmonizer.py joined.csv output.csv

See ../references/icu-metabolic-panel.md for conversion factors and thresholds.
"""

import sys
import pandas as pd
import numpy as np


def parse_value(val):
    """Parse value handling scientific notation and comma decimals."""
    if pd.isna(val):
        return np.nan

    s = str(val).strip().strip('"').strip("'")

    if s.lower() in ('nan', 'none', '', 'null'):
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
# CRITICAL: Do NOT round or format values
CONVERSIONS = {
    'Glucose': (18.0, 'multiply', lambda v: v < 3.0),
    'Creatinine': (88.4, 'divide', lambda v: v > 20),
    'Calcium': (4.0, 'multiply', lambda v: 1.5 <= v <= 4.0),
    'Magnesium': (2.43, 'multiply', lambda v: v < 1.0),
    'Phosphorus': (3.097, 'multiply', lambda v: v < 3.0),
    'BUN': (2.8, 'multiply', lambda v: v < 5.0),
    'pCO2_Arterial': (7.5006, 'multiply', lambda v: v < 15),
    'pO2_Arterial': (7.5006, 'multiply', lambda v: v < 15),
}

# These analytes use mmol/L globally or are unitless - NO CONVERSION
NO_CONVERSION = {
    'Lactate', 'Beta_Hydroxybutyrate', 'pH_Arterial',
    'Osmolality', 'Anion_Gap', 'Sodium', 'Potassium',
    'Chloride', 'Bicarbonate',
}


def convert_column(series, col_name):
    """Apply conversion to a column if it matches known analytes."""
    if col_name in NO_CONVERSION:
        return series
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


def harmonize_icu_panel(input_path, output_path):
    """Main harmonization workflow."""
    df = pd.read_csv(input_path)

    # Parse all values (handles commas, scientific notation)
    for col in df.columns:
        df[col] = df[col].apply(parse_value)

    # Drop rows with any missing measurement values
    df = df.dropna()

    # Apply conversions
    for col in df.columns:
        df[col] = convert_column(df[col], col)

    # CRITICAL: Write full precision, NO rounding, NO float_format
    # The default to_csv behavior preserves full precision
    df.to_csv(output_path, index=False)

    print(f"Harmonized {len(df)} records")
    print(f"Output columns: {list(df.columns)}")
    return df


def join_and_harmonize(file1, file2, output_path, join_col='record_id'):
    """Join two CSV files on a common column, then harmonize."""
    df1 = pd.read_csv(file1)
    df2 = pd.read_csv(file2)

    # Join on common column
    df = pd.merge(df1, df2, on=join_col, how='inner')

    # Write to temp file and harmonize
    temp_path = '/tmp/joined_icu_data.csv'
    df.to_csv(temp_path, index=False)

    return harmonize_icu_panel(temp_path, output_path)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 icu_metabolic_harmonizer.py input.csv output.csv")
        print("       python3 icu_metabolic_harmonizer.py --join file1.csv file2.csv output.csv record_id")
        sys.exit(1)

    if sys.argv[1] == '--join':
        if len(sys.argv) < 5:
            print("Usage: python3 icu_metabolic_harmonizer.py --join file1.csv file2.csv output.csv [record_id]")
            sys.exit(1)
        join_col = sys.argv[5] if len(sys.argv) > 5 else 'record_id'
        join_and_harmonize(sys.argv[2], sys.argv[3], sys.argv[4], join_col)
    else:
        harmonize_icu_panel(sys.argv[1], sys.argv[2])