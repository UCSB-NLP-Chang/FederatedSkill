#!/usr/bin/env python3
"""
HP filter correlation analysis for economic time series.

Handles:
- Mixed annual/quarterly year markers
- Deflation by price index
- HP filter detrending
- Correlation computation

Usage:
    python3 hp_correlation.py

Adjust file paths and column names inside the script for your specific task.
"""

import pandas as pd
import numpy as np
from statsmodels.tsa.filters.hp_filter import hpfilter


def parse_series(df, year_col, value_col):
    """Parse mixed annual/quarterly year markers, returning {year: avg_value}."""
    result = {}
    quarters = {}
    last_year = None
    for _, row in df.iterrows():
        marker = str(row[year_col]).strip()
        val = float(row[value_col])

        # Handle prefixed quarterly markers like '2025:I'
        if ':' in marker:
            year = int(marker.split(':')[0])
            quarters.setdefault(year, []).append(val)
            last_year = year
        # Handle standalone Roman numerals (continuation rows)
        elif marker in ('I', 'II', 'III', 'IV'):
            if last_year is not None:
                quarters.setdefault(last_year, []).append(val)
        # Handle trailing dots: '1994.' -> 1994
        else:
            year = int(float(marker.rstrip('.')))
            result[year] = val
            last_year = year

    # Average quarterly values to get annual
    for y, vals in quarters.items():
        result[y] = np.mean(vals)

    return result


def align_and_compute(series1, series2, price_index, lambda_val=100):
    """
    Align two series with a price index and compute HP-filtered correlation.

    Args:
        series1, series2: dict mapping year -> nominal value
        price_index: dict mapping year -> price index (base year = 1.0)
        lambda_val: HP filter smoothing parameter (100 for annual, 1600 quarterly, 14400 monthly)

    Returns:
        Pearson correlation between cyclical components
    """
    # Find common years
    years = sorted(set(series1.keys()) & set(series2.keys()) & set(price_index.keys()))

    if len(years) < 4:
        raise ValueError(f"Insufficient overlapping years: {len(years)}")

    # Extract aligned arrays
    s1 = np.array([series1[y] for y in years])
    s2 = np.array([series2[y] for y in years])
    pi = np.array([price_index[y] for y in years])

    # Deflate to real values
    real1 = s1 / pi
    real2 = s2 / pi

    # Log transform
    log1 = np.log(real1)
    log2 = np.log(real2)

    # HP filter to extract cyclical component
    _, cycle1 = hpfilter(log1, lamb=lambda_val)
    _, cycle2 = hpfilter(log2, lamb=lambda_val)

    # Pearson correlation
    return np.corrcoef(cycle1, cycle2)[0, 1]


if __name__ == "__main__":
    # TEMPLATE - adjust paths and column names for your task
    # Example usage:
    #
    # df1 = pd.read_excel("table1.xlsx")
    # df2 = pd.read_excel("table2.xlsx")
    # df_pi = pd.read_excel("price_index.xlsx")
    #
    # s1 = parse_series(df1, "Year marker", "National total")
    # s2 = parse_series(df2, "Year marker", "National total")
    # pi = dict(zip(df_pi["Year"], df_pi["Price"]))
    #
    # corr = align_and_compute(s1, s2, pi, lambda_val=100)
    # print(f"{corr:.5f}")
    pass