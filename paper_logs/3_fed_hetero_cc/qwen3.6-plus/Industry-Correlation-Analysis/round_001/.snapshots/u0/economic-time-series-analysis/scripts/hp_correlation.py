#!/usr/bin/env python3
"""
Reusable helper for economic time series analysis:
- Cleans year/index columns
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
    aligned = pd.concat([series1, series2], axis=1).dropna()
    s1, s2 = aligned.iloc[:, 0], aligned.iloc[:, 1]

    # Apply HP filter to log-transformed real values (not levels)
    cycle1, _ = hpfilter(np.log(s1), lamb=lamb)
    cycle2, _ = hpfilter(np.log(s2), lamb=lamb)

    corr, pval = pearsonr(cycle1, cycle2)
    return corr, pval, cycle1, cycle2

if __name__ == '__main__':
    print("Import and use functions directly in your analysis script.")
