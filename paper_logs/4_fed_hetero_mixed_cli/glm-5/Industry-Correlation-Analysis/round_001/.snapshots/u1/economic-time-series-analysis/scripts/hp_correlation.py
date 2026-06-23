#!/usr/bin/env python3
import pandas as pd
import numpy as np
from statsmodels.tsa.filters.hp_filter import hpfilter

def parse_series(df, year_col, value_col):
    """Parse mixed annual/quarterly year markers, returning {year: avg_value}."""
    result = {}
    quarters = {}
    for _, row in df.iterrows():
        marker = str(row[year_col]).strip()
        val = float(row[value_col])
        if ':' in marker or marker in ('II', 'III', 'IV'):
            if ':' in marker:
                year = int(marker.split(':')[0])
            else:
                year = max(quarters.keys()) if quarters else 0
            quarters.setdefault(year, []).append(val)
        else:
            year = int(marker.rstrip('.'))
            result[year] = val
    for y, vals in quarters.items():
        result[y] = np.mean(vals)
    return result

def align_and_compute(series1, series2, price_index, lambda_val=100):
    years = sorted(set(series1.keys()) & set(series2.keys()) & set(price_index.keys()))
    s1 = np.array([series1[y] for y in years])
    s2 = np.array([series2[y] for y in years])
    pi = np.array([price_index[y] for y in years])

    real1 = s1 / pi
    real2 = s2 / pi

    log1 = np.log(real1)
    log2 = np.log(real2)

    _, cycle1 = hpfilter(log1, lamb=lambda_val)
    _, cycle2 = hpfilter(log2, lamb=lambda_val)

    return np.corrcoef(cycle1, cycle2)[0, 1]

if __name__ == "__main__":
    # Adjust paths and column names for your task
    # df1 = pd.read_excel("table1.xlsx")
    # df2 = pd.read_excel("table2.xlsx")
    # df_pi = pd.read_excel("price_index.xlsx")
    # s1 = parse_series(df1, "Year marker", "National total")
    # s2 = parse_series(df2, "Year marker", "National total")
    # pi = dict(zip(df_pi["Year"], df_pi["Price"]))
    # corr = align_and_compute(s1, s2, pi, lambda_val=100)
    # print(f"{corr:.5f}")
    pass