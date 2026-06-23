#!/usr/bin/env python3
"""
Transform wide-format budget XLSX (Q1_BUDGET, Q2_BUDGET, etc.) to long format.
Call as: python3 wide_to_long_budget.py /path/to/budget.xlsx output.csv
"""

import sys
import pandas as pd

def wide_to_long_budget(xlsx_path, output_csv=None):
    """Convert wide budget format to long format suitable for merging."""
    df = pd.read_excel(xlsx_path)

    # Identify quarter columns (pattern: Q*_BUDGET or similar)
    quarter_cols = [c for c in df.columns if c.startswith('Q') and 'BUDGET' in c.upper()]
    if not quarter_cols:
        # Fallback: look for any Q1, Q2, Q3, Q4 columns
        quarter_cols = [c for c in df.columns if c.upper() in ['Q1', 'Q2', 'Q3', 'Q4']]

    if not quarter_cols:
        print("ERROR: No quarter columns found. Expected Q1_BUDGET, Q2_BUDGET, etc.")
        return None

    id_vars = [c for c in df.columns if c not in quarter_cols]

    long_df = df.melt(
        id_vars=id_vars,
        value_vars=quarter_cols,
        var_name='fiscal_quarter',
        value_name='BUDGET_AMOUNT'
    )

    # Normalize quarter names: strip '_BUDGET' suffix if present
    long_df['fiscal_quarter'] = long_df['fiscal_quarter'].str.replace('_BUDGET', '', case=False, regex=False)

    if output_csv:
        long_df.to_csv(output_csv, index=False)
        print(f"Saved to {output_csv}")

    return long_df

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 wide_to_long_budget.py <xlsx_path> [output.csv]")
        sys.exit(1)

    xlsx_path = sys.argv[1]
    output_csv = sys.argv[2] if len(sys.argv) > 2 else None

    df = wide_to_long_budget(xlsx_path, output_csv)
    if df is not None:
        print(f"Transformed {len(df)} rows (from {len(df['fiscal_quarter'].unique())} quarters)")
        print(df.head(3))