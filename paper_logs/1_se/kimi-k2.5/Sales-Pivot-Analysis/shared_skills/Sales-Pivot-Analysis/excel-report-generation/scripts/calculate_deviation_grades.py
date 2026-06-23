#!/usr/bin/env python3
"""
Quality control deviation and grade calculation with missing value handling.

Usage:
    from calculate_deviation_grades import calculate_deviation, assign_grade, validate_qc_data
    
    df['DEVIATION_MM'] = df.apply(lambda r: calculate_deviation(
        r['MEASUREMENT_MM'], r['TOLERANCE_MM']), axis=1)
    df['QUALITY_GRADE'] = df['DEVIATION_MM'].apply(assign_grade)
    issues = validate_qc_data(df)
"""

import pandas as pd
import numpy as np


def calculate_deviation(measurement, target):
    """
    Calculate absolute deviation, preserving NaN.
    
    Args:
        measurement: Actual measured value (may be NaN)
        target: Target/tolerance value (may be NaN)
    
    Returns:
        Absolute deviation or NaN if either input is NaN
    """
    if pd.isna(measurement) or pd.isna(target):
        return np.nan
    return abs(measurement - target)


def calculate_relative_error(actual, target):
    """
    Calculate absolute relative error, preserving NaN.
    
    Args:
        actual: Actual value (may be NaN)
        target: Target value (may be NaN or zero)
    
    Returns:
        Relative error (0-1+) or NaN if inputs invalid
    """
    if pd.isna(actual) or pd.isna(target) or target == 0:
        return np.nan
    return abs(actual - target) / target


def assign_grade(deviation, thresholds=None):
    """
    Assign quality grade based on deviation.
    
    Default thresholds:
        A: deviation < 0.5
        B: 0.5 <= deviation < 1.0
        C: deviation >= 1.0
        N/A: NaN deviation
    
    Args:
        deviation: Numeric deviation value (may be NaN)
        thresholds: Optional dict {'A': 0.5, 'B': 1.0} for custom thresholds
    
    Returns:
        String grade: 'A', 'B', 'C', or 'N/A'
    """
    if thresholds is None:
        thresholds = {'A': 0.5, 'B': 1.0}
    
    if pd.isna(deviation):
        return "N/A"
    elif deviation < thresholds['A']:
        return "A"
    elif deviation < thresholds['B']:
        return "B"
    else:
        return "C"


def assign_grade_with_custom(deviation, a_max, b_max):
    """
    Assign grade with explicit thresholds.
    
    Args:
        deviation: Numeric deviation (may be NaN)
        a_max: Upper bound for grade A (exclusive)
        b_max: Upper bound for grade B (exclusive)
    
    Returns:
        'A', 'B', 'C', or 'N/A'
    """
    return assign_grade(deviation, {'A': a_max, 'B': b_max})


def validate_qc_data(df, measurement_col='MEASUREMENT_MM',
                     deviation_col='DEVIATION_MM',
                     grade_col='QUALITY_GRADE'):
    """
    Run standard quality control data validation checks.
    
    Returns:
        List of issue strings (empty if all checks pass)
    """
    issues = []
    
    # Check for unexpected negative deviations
    if deviation_col in df.columns:
        neg_count = (df[deviation_col] < 0).sum()
        if neg_count > 0:
            issues.append(f"Negative deviations found: {neg_count}")
    
    # Verify NaN measurements match NaN deviations
    if measurement_col in df.columns and deviation_col in df.columns:
        nan_meas = df[measurement_col].isna().sum()
        nan_dev = df[deviation_col].isna().sum()
        if nan_meas != nan_dev:
            issues.append(
                f"Mismatch: {nan_meas} NaN {measurement_col} but "
                f"{nan_dev} NaN {deviation_col}"
            )
    
    # Verify grade coverage
    if grade_col in df.columns:
        expected = {'A', 'B', 'C', 'N/A'}
        # Note: pandas may read "N/A" as NaN, so check both
        actual = set(df[grade_col].dropna().unique())
        # Also check for actual string "N/A" via object dtype check
        if df[grade_col].dtype == 'object':
            string_na = (df[grade_col] == "N/A").sum()
        else:
            string_na = 0
        
        unexpected = actual - expected
        if unexpected and not all(pd.isna(x) for x in unexpected):
            issues.append(f"Unexpected grade values: {unexpected}")
        
        # Check if missing grades correspond to NaN deviations
        if deviation_col in df.columns:
            nan_dev = df[deviation_col].isna().sum()
            na_grades = string_na + df[grade_col].isna().sum()
            if nan_dev != na_grades:
                issues.append(
                    f"Grade mismatch: {nan_dev} NaN deviations but "
                    f"{na_grades} N/A/missing grades"
                )
    
    return issues


def generate_qc_pivot_sheets(df, output_path, line_col='LINE', shift_col='SHIFT',
                             deviation_col='DEVIATION_MM', id_col='INSPECTION_ID'):
    """
    Generate standard 5-sheet quality control Excel report.
    
    Args:
        df: DataFrame with QC data
        output_path: Path for output Excel file
        *_col: Column name mappings
    """
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Sheet 1: Source data
        df.to_excel(writer, sheet_name='SourceData', index=False)
        
        # Sheet 2: Count by line
        if line_col in df.columns:
            df.groupby(line_col).size().reset_index(name='Count').to_excel(
                writer, sheet_name='Fail Rate by Line', index=False)
        
        # Sheet 3: Average deviation by line
        if line_col in df.columns and deviation_col in df.columns:
            df.groupby(line_col)[deviation_col].mean().reset_index(
                name=f'Average of {deviation_col}').to_excel(
                writer, sheet_name='Avg Deviation by Line', index=False)
        
        # Sheet 4: Count by shift
        if shift_col in df.columns:
            df.groupby(shift_col).size().reset_index(name='Count').to_excel(
                writer, sheet_name='Inspections by Shift', index=False)
        
        # Sheet 5: Line × Shift matrix
        if line_col in df.columns and shift_col in df.columns and id_col in df.columns:
            df.pivot_table(
                values=id_col,
                index=line_col,
                columns=shift_col,
                aggfunc='count',
                fill_value=0
            ).reset_index().to_excel(writer, sheet_name='Line Shift Matrix', index=False)


if __name__ == '__main__':
    # Test cases
    test_cases = [
        # (measurement, target, expected_dev, expected_grade)
        (10.0, 10.0, 0.0, 'A'),      # Perfect match
        (10.5, 10.0, 0.5, 'B'),      # At A threshold -> B (exclusive)
        (10.3, 10.0, 0.3, 'A'),      # Within A
        (11.0, 10.0, 1.0, 'C'),      # At B threshold -> C (exclusive)
        (12.0, 10.0, 2.0, 'C'),      # Beyond B
        (np.nan, 10.0, np.nan, 'N/A'),  # Missing measurement
        (10.0, np.nan, np.nan, 'N/A'),  # Missing target
    ]
    
    for meas, targ, exp_dev, exp_grade in test_cases:
        dev = calculate_deviation(meas, targ)
        grade = assign_grade(dev)
        
        if pd.isna(exp_dev):
            assert pd.isna(dev), f"Expected NaN deviation for {meas}, {targ}, got {dev}"
        else:
            assert abs(dev - exp_dev) < 0.001, f"Deviation mismatch: {dev} vs {exp_dev}"
        
        assert grade == exp_grade, f"Grade mismatch: {grade} vs {exp_grade} for deviation {dev}"
    
    print("All tests passed.")
