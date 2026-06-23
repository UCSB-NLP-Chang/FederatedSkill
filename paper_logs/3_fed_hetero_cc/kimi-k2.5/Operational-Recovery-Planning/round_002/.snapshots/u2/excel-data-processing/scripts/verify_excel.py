#!/usr/bin/env python3
"""
Quick validation script for Excel file integrity.
Usage: python3 verify_excel.py <file.xlsx> [sheet_name]
"""
import sys

try:
    import pandas as pd
except ImportError:
    print("ERROR: pandas not installed. Run: pip install pandas openpyxl --break-system-packages")
    sys.exit(1)

if len(sys.argv) < 2:
    print("Usage: python3 verify_excel.py <file.xlsx> [sheet_name]")
    sys.exit(1)

file_path = sys.argv[1]
sheet = sys.argv[2] if len(sys.argv) > 2 else 0

try:
    df = pd.read_excel(file_path, sheet_name=sheet)
    print(f"✓ File: {file_path}")
    print(f"✓ Sheet: {sheet if isinstance(sheet, str) else f'index {sheet}'}")
    print(f"✓ Shape: {df.shape}")
    print(f"✓ Columns: {list(df.columns)[:10]}{'...' if len(df.columns) > 10 else ''}")
    print(f"\nFirst 3 rows:")
    print(df.head(3).to_string())
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)