#!/usr/bin/env python3
"""
Reusable template for economic time series correlation analysis.

Auto-detects common column naming patterns. Assumes:
- Two data tables with year markers and value columns
- One deflator table with year and price index
- Possible quarterly data in final year to average

Output: /root/answer.txt containing only the correlation coefficient (5 decimal places)
"""

import pandas as pd
import numpy as np
from scipy.stats import pearsonr
from statsmodels.tsa.filters.hp_filter import hpfilter


def detect_value_column(df):
    """Auto-detect the main value column."""
    # Prefer columns containing 'total' but not 'memo'
    candidates = [c for c in df.columns 
                  if 'total' in c.lower() and 'memo' not in c.lower()]
    if candidates:
        return candidates[0]
    # Fall back to first numeric column that's not obviously a year
    for c in df.columns:
        if df[c].dtype in ['float64', 'int64']:
            if not ('year' in c.lower() or 'period' in c.lower()):
                return c
    raise ValueError("Could not detect value column")


def detect_year_column(df):
    """Auto-detect the year marker column."""
    candidates = [c for c in df.columns 
                  if any(x in c.lower() for x in ['year', 'period', 'label'])]
    if candidates:
        return candidates[0]
    # Fall back to first column that looks like years
    return df.columns[0]


def parse_year_marker(marker):
    """Parse year markers: '1992.', '2025:I', '2025 Q1', 'II', or 'Source note'."""
    s = str(marker).strip()
    if s.lower().startswith('source'):
        return None
    if ' Q' in s:  # "2025 Q1"
        return int(s.split(' Q')[0])
    if ':' in s:   # "2025:I"
        return int(s.split(':')[0])
    try:
        return int(float(s))  # "1992."
    except ValueError:
        return None  # "II", "III" — will forward-fill


def load_series(filepath, value_col=None):
    """Load a data table and convert to annual series."""
    df = pd.read_excel(filepath)
    
    if value_col is None:
        value_col = detect_value_column(df)
    year_col = detect_year_column(df)
    
    # Parse years
    df['year'] = df[year_col].apply(parse_year_marker)
    df['year'] = df['year'].ffill()
    
    # Filter out source notes and NaN values
    df = df.dropna(subset=['year', value_col])
    df['year'] = df['year'].astype(int)
    
    # Average quarters to annual values
    annual = df.groupby('year')[value_col].mean().reset_index()
    return annual, value_col


def detect_price_column(df):
    """Auto-detect price/deflator column."""
    candidates = [c for c in df.columns 
                  if any(x in c.lower() for x in ['price', 'deflator', 'index'])]
    if candidates:
        return candidates[0]
    # Fall back to first numeric column after year
    year_col = detect_year_column(df)
    for c in df.columns:
        if c != year_col and df[c].dtype in ['float64', 'int64']:
            return c
    raise ValueError("Could not detect price column")


def main(series_a_path, series_b_path, deflator_path, output_path='/root/answer.txt'):
    # Load data
    series_a, value_col_a = load_series(series_a_path)
    series_b, value_col_b = load_series(series_b_path)
    
    deflator = pd.read_excel(deflator_path)
    year_col_d = detect_year_column(deflator)
    price_col = detect_price_column(deflator)
    
    # Align series
    merged = series_a.merge(series_b, on='year', suffixes=('_a', '_b'))
    merged = merged.merge(deflator[[year_col_d, price_col]], 
                          left_on='year', right_on=year_col_d)
    
    # Deflate
    merged['real_a'] = merged[f'{value_col_a}_a'] / merged[price_col]
    merged['real_b'] = merged[f'{value_col_b}_b'] / merged[price_col]
    
    # Log transform
    log_a = np.log(merged['real_a'])
    log_b = np.log(merged['real_b'])
    
    # HP filter: lambda=100 for annual data
    cycle_a, _ = hpfilter(log_a, lamb=100)
    cycle_b, _ = hpfilter(log_b, lamb=100)
    
    # Correlation
    corr, _ = pearsonr(cycle_a, cycle_b)
    
    # Output: ONLY the numeric value, no extra formatting
    with open(output_path, 'w') as f:
        f.write(f"{corr:.5f}")
    
    print(f"Correlation: {corr:.5f}")
    print(f"Written to {output_path}")
    return corr


if __name__ == '__main__':
    import sys
    if len(sys.argv) >= 4:
        main(sys.argv[1], sys.argv[2], sys.argv[3], 
             sys.argv[4] if len(sys.argv) > 4 else '/root/answer.txt')
    else:
        # Example usage - adjust paths as needed
        main(
            '/root/media_release_table_05.xlsx',
            '/root/media_release_table_12.xlsx', 
            '/root/media_service_prices.xlsx'
        )
