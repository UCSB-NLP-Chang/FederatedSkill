#!/usr/bin/env python3
"""
Reusable helper for economic time series analysis:
- Cleans year/index columns (handles trailing dots and quarterly suffixes)
- Aggregates mixed frequencies to annual
- Deflates nominal series
- Applies HP filter
- Computes Pearson correlation on cyclical components
"""
import pandas as pd
import numpy as np
from scipy.stats import pearsonr
from statsmodels.tsa.filters.hp_filter import hpfilter

def clean_year_index(df, col_name='Year marker'):
    """Clean year columns that may contain trailing dots or quarterly suffixes."""
    df[col_name] = df[col_name].astype(str).str.replace(r'\.', '', regex=True).str.strip()
    # Extract base year from formats like '2025:I' or '2025Q1'
    df[col_name] = df[col_name].str.extract(r'^(\d+)', expand=False)
    try:
        df[col_name] = pd.to_numeric(df[col_name])
    except ValueError:
        pass
    return df.set_index(col_name)

def deflate_series(nominal, price_index, base_value=1.0):
    """Convert nominal series to real terms using a price index."""
    return nominal / (price_index / base_value)

def run_hp_correlation(series1, series2, lamb=100):
    """Align, log-transform, HP filter, and compute Pearson correlation.

    Args:
        series1, series2: Real-valued time series (not nominal)
        lamb: HP filter lambda (100=annual, 1600=quarterly, 14400=monthly)

    Returns:
        corr, pval, cycle1, cycle2: Pearson correlation and cyclical components
    """
    # Aggregate duplicate years if present (e.g., from quarterly data)
    s1 = series1.groupby(level=0).mean()
    s2 = series2.groupby(level=0).mean()
    
    aligned = pd.concat([s1, s2], axis=1).dropna()
    if aligned.empty:
        raise ValueError("Series could not be aligned. Check index formats and ranges.")
        
    s1_aligned, s2_aligned = aligned.iloc[:, 0], aligned.iloc[:, 1]

    # Apply HP filter to log-transformed real values (not levels)
    cycle1, _ = hpfilter(np.log(s1_aligned), lamb=lamb)
    cycle2, _ = hpfilter(np.log(s2_aligned), lamb=lamb)

    corr, pval = pearsonr(cycle1, cycle2)
    return corr, pval, cycle1, cycle2

if __name__ == '__main__':
    print("Import and use functions directly in your analysis script.")
