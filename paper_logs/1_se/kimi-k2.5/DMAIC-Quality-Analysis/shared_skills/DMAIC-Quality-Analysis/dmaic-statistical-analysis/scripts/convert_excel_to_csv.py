#!/usr/bin/env python3
"""
Convert Excel (.xlsx) files to CSV for DMAIC analysis.
Handles common column name variations and data cleaning.

Usage:
    python convert_excel_to_csv.py <input.xlsx> <output.csv> [--value-col COLNAME]
"""

import pandas as pd
import sys
import argparse

def convert_excel_to_csv(input_path, output_path, value_col=None):
    """Read Excel and write clean CSV with standard columns."""
    # Read Excel
    df = pd.read_excel(input_path)
    
    # Strip whitespace from column names
    df.columns = [c.strip() for c in df.columns]
    
    # Detect date column
    date_col = None
    for col in df.columns:
        if col.lower() in ['date', 'day', 'timestamp']:
            date_col = col
            break
    
    if date_col is None:
        # Try to find datetime column
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                date_col = col
                break
    
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col])
        # Ensure Date column exists for script compatibility
        if date_col != 'Date':
            df['Date'] = df[date_col].dt.strftime('%Y-%m-%d')
    
    # Detect value column if not specified
    if value_col is None:
        for col in df.columns:
            if col in ['ResolvedAlerts', 'CompletedPanels', 'ClosedWorkOrders', 'UPR', 'Value', 'Metric', 'Count']:
                value_col = col
                break
    
    # Ensure Stage column exists
    if 'Stage' not in df.columns:
        df['Stage'] = 'Baseline'
    
    # Ensure Day column exists (weekday name)
    if 'Day' not in df.columns and date_col:
        df['Day'] = df[date_col].dt.day_name()
    
    # Write CSV
    df.to_csv(output_path, index=False)
    print(f"Converted {input_path} -> {output_path}")
    print(f"Columns: {list(df.columns)}")
    print(f"Rows: {len(df)}")
    if value_col:
        print(f"Value column: {value_col}")
    
    return output_path

def main():
    parser = argparse.ArgumentParser(description='Convert Excel to CSV for DMAIC analysis')
    parser.add_argument('input_xlsx', help='Input Excel file path')
    parser.add_argument('output_csv', help='Output CSV file path')
    parser.add_argument('--value-col', help='Name of value/metric column')
    args = parser.parse_args()
    
    convert_excel_to_csv(args.input_xlsx, args.output_csv, args.value_col)

if __name__ == '__main__':
    main()
