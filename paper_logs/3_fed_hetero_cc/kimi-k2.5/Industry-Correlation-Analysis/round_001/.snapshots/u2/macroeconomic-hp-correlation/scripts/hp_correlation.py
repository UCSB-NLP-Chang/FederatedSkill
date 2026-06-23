#!/usr/bin/env python3
"""
HP Filter Correlation Calculator

Computes cyclical correlation between two economic time series.
Expects: year, nominal_value columns for each series, plus price index data.
"""

import pandas as pd
import numpy as np
from statsmodels.tsa.filters.hp_filter import hpfilter
from scipy.stats import pearsonr
import sys

def load_and_average_quarters(df, year_col='year', value_col='value'):
    """Average quarterly data to annual when needed."""
    annual = df.groupby(year_col)[value_col].mean().reset_index()
    return annual

def deflate_series(nominal_df, price_df, year_col='year', 
                   nominal_col='value', price_col='index'):
    """Deflate nominal series using price index."""
    merged = pd.merge(nominal_df, price_df, on=year_col, how='inner')
    merged['real'] = merged[nominal_col] / merged[price_col]
    return merged[[year_col, 'real']]

def hp_correlation(series1, series2, lamb=100):
    """
    Compute HP-filtered cyclical correlation.
    
    Args:
        series1, series2: Arrays of real values (same length)
        lamb: HP filter lambda (100=annual, 1600=quarterly, 14400=monthly)
    
    Returns:
        Pearson correlation coefficient of cyclical components
    """
    log1 = np.log(series1)
    log2 = np.log(series2)
    
    _, cyclical1 = hpfilter(log1, lamb=lamb)
    _, cyclical2 = hpfilter(log2, lamb=lamb)
    
    # Verify cyclical components sum to ~0
    assert abs(np.mean(cyclical1)) < 1e-10, "Cyclical1 mean not zero"
    assert abs(np.mean(cyclical2)) < 1e-10, "Cyclical2 mean not zero"
    
    corr, _ = pearsonr(cyclical1, cyclical2)
    return corr

def main():
    if len(sys.argv) != 4:
        print("Usage: hp_correlation.py <series1_file> <series2_file> <price_index_file>")
        print("Files should be CSV with columns: year, value")
        print("Price index file should have: year, index (base year = 1.0)")
        sys.exit(1)
    
    s1_file, s2_file, price_file = sys.argv[1:4]
    
    # Load data
    s1 = pd.read_csv(s1_file)
    s2 = pd.read_csv(s2_file)
    price = pd.read_csv(price_file)
    
    # Deflate
    s1_real = deflate_series(s1, price)
    s2_real = deflate_series(s2, price)
    
    # Align
    merged = pd.merge(s1_real, s2_real, on='year', suffixes=('_1', '_2'))
    
    # Compute correlation
    corr = hp_correlation(merged['real_1'].values, merged['real_2'].values)
    
    print(f"Correlation: {corr:.5f}")
    return corr

if __name__ == '__main__':
    main()