#!/usr/bin/env python3
"""Verify production catch-up plan Excel file structure."""
import argparse
import sys
import pandas as pd
import numpy as np


def verify_plan(filepath, expected_weeks, sheet_name='Plan', expected_columns=None):
    """Verify Excel plan matches expected structure."""
    errors = []

    try:
        df = pd.read_excel(filepath, sheet_name=sheet_name)
    except ValueError as e:
        print(f"FAIL: Could not read sheet '{sheet_name}': {e}")
        return False

    # Check row count
    if len(df) != expected_weeks:
        errors.append(f"Row count: got {len(df)}, expected {expected_weeks}")

    # Check columns
    if expected_columns:
        actual_cols = list(df.columns)
        if actual_cols != expected_columns:
            errors.append(f"Column mismatch:\n  Got: {actual_cols}\n  Expected: {expected_columns}")

    # Check week sequence
    if 'Week' in df.columns:
        weeks = df['Week'].tolist()
        expected_seq = list(range(int(weeks[0]), int(weeks[0]) + expected_weeks))
        if weeks != expected_seq:
            missing = set(expected_seq) - set(weeks)
            extra = set(weeks) - set(expected_seq)
            if missing:
                errors.append(f"Missing weeks: {sorted(missing)}")
            if extra:
                errors.append(f"Extra weeks: {sorted(extra)}")

    # Check state carry if both columns present
    if 'End of Week Backlog/Buffer (Std Hrs)' in df.columns and \
       'Start of Week Past Due (Std Hrs)' in df.columns:
        end_vals = df['End of Week Backlog/Buffer (Std Hrs)'].iloc[:-1].values
        start_vals = df['Start of Week Past Due (Std Hrs)'].iloc[1:].values
        mismatches = []
        for i, (e, s) in enumerate(zip(end_vals, start_vals)):
            if e > 0 and abs(e - s) > 0.01:
                mismatches.append(f"Row {i+1}: end={e:.2f}, next_start={s:.2f}")
            elif e <= 0 and s != 0:
                mismatches.append(f"Row {i+1}: end={e:.2f} (<=0), next_start={s:.2f} (should be 0)")
        if mismatches:
            errors.append(f"State carry errors:\n  " + "\n  ".join(mismatches[:5]))

    if errors:
        print("FAIL:")
        for e in errors:
            print(f"  - {e}")
        return False

    print(f"PASS: {filepath} validated ({expected_weeks} rows, sheet '{sheet_name}')")
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Verify production plan Excel file')
    parser.add_argument('filepath', help='Path to Excel file')
    parser.add_argument('--weeks', type=int, required=True, help='Expected number of weeks/rows')
    parser.add_argument('--sheet', default='Plan', help='Sheet name to verify')

    args = parser.parse_args()
    success = verify_plan(args.filepath, args.weeks, args.sheet)
    sys.exit(0 if success else 1)