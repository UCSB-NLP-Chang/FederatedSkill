#!/usr/bin/env python3
"""Compute detrended correlation between two economic time series.

Usage:
    python detrended_correlation.py \
        --series1 /path/to/series1.xlsx \
        --series2 /path/to/series2.xlsx \
        --price-index /path/to/price_index.xlsx \
        --output /path/to/result.txt \
        --method hp

Methods:
    hp: Hodrick-Prescott filter (default, recommended for business cycles)
    loglinear: Linear regression on log values
"""

import argparse
import pandas as pd
import numpy as np
from scipy.stats import linregress, pearsonr

try:
    from statsmodels.tsa.filters.hp_filter import hpfilter
    HAS_HPFILTER = True
except ImportError:
    HAS_HPFILTER = False


def parse_year_markers(df, year_col='Year marker'):
    """Parse year markers handling trailing periods and quarterly formats."""
    years = []
    current_year = None
    for val in df[year_col]:
        val_str = str(val).strip()
        if ':' in val_str:
            current_year = int(val_str.split(':')[0])
            years.append(current_year)
        elif val_str.replace('.', '').isdigit():
            current_year = int(float(val_str))
            years.append(current_year)
        else:
            years.append(current_year)
    return years


def discover_data_rows(df, year_col_hint='Period'):
    """Find the first row that contains actual data by looking for year-like values."""
    for idx, row in df.iterrows():
        for val in row:
            val_str = str(val).strip()
            # Check for year patterns: '1993', '1993.', '2025:I'
            if ':' in val_str and val_str.split(':')[0].isdigit():
                return idx
            if val_str.replace('.', '').isdigit() and len(val_str.replace('.', '')) == 4:
                return idx
    return 0


def load_annual_series(filepath, value_col=None, year_col=None, skiprows=None, sheet_name=0, series_label=None, release_status='final'):
    """Load Excel file and return annual series with quarterly aggregation.
    
    Auto-discovers header row and column names if not specified.
    Supports filtering by series_label and release_status.
    """
    # First, inspect the file structure
    df_raw = pd.read_excel(filepath, header=None, sheet_name=sheet_name)
    
    if skiprows is None:
        data_start = discover_data_rows(df_raw)
        # Header is typically one row before data
        header_row = data_start - 1 if data_start > 0 else 0
    else:
        header_row = skiprows
    
    # Read with proper header
    df = pd.read_excel(filepath, header=header_row, sheet_name=sheet_name)
    
    # Filter by series_label if specified
    if series_label is not None:
        label_col = None
        for col in df.columns:
            if 'series' in str(col).lower() and 'label' in str(col).lower():
                label_col = col
                break
            if 'series_label' in str(col).lower():
                label_col = col
                break
        if label_col:
            df = df[df[label_col] == series_label]
    
    # Filter by release_status if column exists
    if release_status:
        status_col = None
        for col in df.columns:
            if 'release' in str(col).lower() and 'status' in str(col).lower():
                status_col = col
                break
        if status_col:
            df = df[df[status_col] == release_status]
    
    # Auto-discover column names if not specified
    if year_col is None:
        for col in df.columns:
            if 'period' in str(col).lower() or 'year' in str(col).lower():
                year_col = col
                break
        if year_col is None:
            year_col = df.columns[0]  # Default to first column
    
    if value_col is None:
        # Find first numeric column that's not the year column
        for col in df.columns:
            if col != year_col and pd.api.types.is_numeric_dtype(df[col]):
                value_col = col
                break
        if value_col is None:
            value_col = df.columns[1]  # Default to second column
    
    years = parse_year_markers(df, year_col)
    df['year'] = years
    
    # Filter out non-numeric values (like 'Source note')
    df = df[pd.to_numeric(df[value_col], errors='coerce').notna()]
    
    # Remove duplicate years (keep first occurrence)
    df = df.drop_duplicates(subset=['year'], keep='first')
    
    # Aggregate by year (handles quarterly data)
    annual = df.groupby('year')[value_col].mean().reset_index()
    return annual


def deflate_and_detrend_hp(nominal_values, price_indices, lamb=100):
    """Deflate and detrend using HP filter."""
    if not HAS_HPFILTER:
        raise ImportError("statsmodels required for HP filter. Use --method loglinear or install statsmodels.")
    
    real_values = np.array(nominal_values) / np.array(price_indices)
    log_values = np.log(real_values)
    
    cycle, trend = hpfilter(log_values, lamb=lamb)
    return cycle


def deflate_and_detrend_loglinear(nominal_values, price_indices):
    """Deflate and detrend using log-linear method."""
    real_values = np.array(nominal_values) / np.array(price_indices)
    log_values = np.log(real_values)
    
    t = np.arange(len(log_values))
    slope, intercept, _, _, _ = linregress(t, log_values)
    trend = intercept + slope * t
    residuals = log_values - trend
    
    return residuals


def main():
    parser = argparse.ArgumentParser(description='Compute detrended correlation')
    parser.add_argument('--series1', required=True, help='Path to first series Excel file')
    parser.add_argument('--series2', required=True, help='Path to second series Excel file')
    parser.add_argument('--price-index', required=True, help='Path to price index Excel file')
    parser.add_argument('--value-col', default=None, help='Value column name (auto-detected if not specified)')
    parser.add_argument('--year-col', default=None, help='Year column name (auto-detected if not specified)')
    parser.add_argument('--price-year-col', default=None, help='Year column in price index (auto-detected if not specified)')
    parser.add_argument('--price-value-col', default=None, help='Price index value column (auto-detected if not specified)')
    parser.add_argument('--method', choices=['hp', 'loglinear'], default='hp', help='Detrending method')
    parser.add_argument('--lambda', dest='lamb', type=float, default=100, help='HP filter smoothing parameter (default: 100 for annual data)')
    parser.add_argument('--output', required=True, help='Output file path')
    parser.add_argument('--sheet1', default=0, help='Sheet name/index for series1')
    parser.add_argument('--sheet2', default=0, help='Sheet name/index for series2')
    parser.add_argument('--series-label1', default=None, help='Filter series1 by this label')
    parser.add_argument('--series-label2', default=None, help='Filter series2 by this label')
    parser.add_argument('--release-status', default='final', help='Filter by release status (default: final)')
    args = parser.parse_args()
    
    # Load data with auto-discovery
    s1 = load_annual_series(args.series1, args.value_col, args.year_col, 
                            sheet_name=args.sheet1, series_label=args.series_label1,
                            release_status=args.release_status)
    s2 = load_annual_series(args.series2, args.value_col, args.year_col,
                            sheet_name=args.sheet2, series_label=args.series_label2,
                            release_status=args.release_status)
    price_df = pd.read_excel(args.price_index)
    
    # Auto-detect price columns if not specified
    price_year_col = args.price_year_col
    price_value_col = args.price_value_col
    
    if price_year_col is None:
        for col in price_df.columns:
            if 'year' in str(col).lower():
                price_year_col = col
                break
        if price_year_col is None:
            price_year_col = price_df.columns[0]
    
    if price_value_col is None:
        for col in price_df.columns:
            if col != price_year_col and pd.api.types.is_numeric_dtype(price_df[col]):
                price_value_col = col
                break
        if price_value_col is None:
            price_value_col = price_df.columns[1]
    
    # Remove duplicate years from price index
    price_df = price_df.drop_duplicates(subset=[price_year_col], keep='first')
    
    # Align years
    common_years = sorted(set(s1['year']) & set(s2['year']) & set(price_df[price_year_col]))
    
    s1_aligned = s1[s1['year'].isin(common_years)].sort_values('year')[s1.columns[1]].values
    s2_aligned = s2[s2['year'].isin(common_years)].sort_values('year')[s2.columns[1]].values
    price_aligned = price_df[price_df[price_year_col].isin(common_years)].sort_values(price_year_col)[price_value_col].values
    
    # Detrend both series
    if args.method == 'hp':
        res1 = deflate_and_detrend_hp(s1_aligned, price_aligned, args.lamb)
        res2 = deflate_and_detrend_hp(s2_aligned, price_aligned, args.lamb)
    else:
        res1 = deflate_and_detrend_loglinear(s1_aligned, price_aligned)
        res2 = deflate_and_detrend_loglinear(s2_aligned, price_aligned)
    
    # Compute correlation
    corr, pval = pearsonr(res1, res2)
    
    with open(args.output, 'w') as f:
        f.write(f"{corr:.5f}\n")
    
    print(f"Correlation: {corr:.5f} (p={pval:.6f})")


if __name__ == '__main__':
    main()
