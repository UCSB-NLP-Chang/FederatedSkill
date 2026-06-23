#!/usr/bin/env python3
"""
ICU Metabolic Panel Harmonizer

Parses CSV with potential mixed SI/US units, detects unit system based on
physiological thresholds, converts to US conventional units, and outputs
full-precision values (NO ROUNDING).

Usage:
    python3 icu_metabolic_harmonizer.py input.csv output.csv

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
CONVERSIONS = {
    'Glucose': (18.0, 'multiply', lambda v: v < 3.0),
    'Creatinine': (88.4, 'divide', lambda v: v > 20),
    'Calcium': (4.0, 'multiply', lambda v: 1.5 <= v <= 4.0),
    'Magnesium': (2.43, 'multiply', lambda v: v < 1.0),
    'Phosphorus': (3.097, 'multiply', lambda v: v < 3.0),
    'BUN': (2.8, 'multiply', lambda v: v < 5.0),
    'pCO2_Arterial': (7.50062, 'multiply', lambda v: v < 15),
    'pO2_Arterial': (7.50062, 'multiply', lambda v: v < 15),
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
    
    # CRITICAL: Write full precision, NO rounding
    # Do NOT use float_format - pandas writes full precision by default
    # Never use round(), format(), or fixed decimal formatting
    df.to_csv(output_path, index=False)
    
    print(f"Harmonized {len(df)} records")
    print(f"Output columns: {list(df.columns)}")
    return df


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python3 icu_metabolic_harmonizer.py input.csv output.csv")
        sys.exit(1)
    
    harmonize_icu_panel(sys.argv[1], sys.argv[2])
