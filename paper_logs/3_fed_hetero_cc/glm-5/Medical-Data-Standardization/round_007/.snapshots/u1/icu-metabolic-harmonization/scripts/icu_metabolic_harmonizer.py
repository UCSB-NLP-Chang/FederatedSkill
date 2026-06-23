#!/usr/bin/env python3
"""
ICU Metabolic Panel Harmonizer

Parses CSV with potential mixed SI/US units, detects unit system based on
physiological thresholds, converts to US conventional units, and outputs
full-precision values (NO ROUNDING).

Usage:
    python3 icu_metabolic_harmonizer.py input.csv output.csv

The script uses float_format='%.10g' to preserve full precision.
DO NOT modify this to use .2f or any rounding format.
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
        s = s.replace(',', '.')
    elif ',' in s and '.' in s:
        last_comma = s.rfind(',')
        last_dot = s.rfind('.')
        if last_comma > last_dot:
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')

    try:
        return float(s)
    except ValueError:
        return np.nan


# ICU Conversion factors: (factor, operation, threshold, direction)
# direction: '<' means convert if value < threshold, '>' means if value > threshold
ICU_CONVERSIONS = {
    'Glucose': (18.0, 'multiply', 3.0, '<'),
    'Creatinine': (88.4, 'divide', 20, '>'),
    'Calcium': (4.0, 'multiply', (1.5, 4.0), 'range'),
    'Magnesium': (2.43, 'multiply', 1.0, '<'),
    'Phosphorus': (3.097, 'multiply', 3.0, '<'),
    'BUN': (2.8, 'multiply', 5.0, '<'),
    'pCO2_Arterial': (7.50062, 'multiply', 15, '<'),
    'pO2_Arterial': (7.50062, 'multiply', 15, '<'),
}


def should_convert(col_name, val):
    """Determine if a value should be converted based on ICU thresholds."""
    if col_name not in ICU_CONVERSIONS:
        return False

    factor, operation, threshold, direction = ICU_CONVERSIONS[col_name]

    if direction == '<':
        return val < threshold
    elif direction == '>':
        return val > threshold
    elif direction == 'range':
        lo, hi = threshold
        return lo <= val <= hi
    return False


def convert_icu_value(col_name, val):
    """Apply ICU conversion to a single value."""
    if pd.isna(val):
        return val

    if col_name not in ICU_CONVERSIONS:
        return val

    if not should_convert(col_name, val):
        return val

    factor, operation, _, _ = ICU_CONVERSIONS[col_name]

    if operation == 'multiply':
        return val * factor
    elif operation == 'divide':
        return val / factor
    return val


def harmonize_icu_panel(input_path, output_path, join_files=None, join_key='record_id'):
    """Main harmonization workflow.

    Args:
        input_path: Path to primary CSV file
        output_path: Path for output CSV
        join_files: Optional list of additional CSV files to join
        join_key: Column name for joining (default 'record_id')
    """
    df = pd.read_csv(input_path)

    # If additional files provided, join them
    if join_files:
        for f in join_files:
            other = pd.read_csv(f)
            df = df.merge(other, on=join_key, how='inner')

    # Drop ID columns if present
    id_cols = [c for c in df.columns if 'id' in c.lower() and c != join_key]
    if join_key in df.columns:
        id_cols.append(join_key)

    # Parse all values
    for col in df.columns:
        if col not in id_cols:
            df[col] = df[col].apply(parse_value)

    # Drop rows with any missing measurement values
    measurement_cols = [c for c in df.columns if c not in id_cols]
    df = df.dropna(subset=measurement_cols)

    # Apply conversions
    for col in df.columns:
        if col not in id_cols:
            df[col] = df[col].apply(lambda v: convert_icu_value(col, v))

    # Remove ID columns from output
    for col in id_cols:
        if col in df.columns:
            df = df.drop(columns=[col])

    # CRITICAL: Write full precision, NO rounding
    # Using %.10g preserves precision without scientific notation for reasonable values
    df.to_csv(output_path, index=False, float_format='%.10g')

    print(f"Harmonized {len(df)} records")
    print(f"Output columns: {list(df.columns)}")
    return df


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 icu_metabolic_harmonizer.py input.csv output.csv [join_file1.csv ...]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    join_files = sys.argv[3:] if len(sys.argv) > 3 else None

    harmonize_icu_panel(input_file, output_file, join_files)
