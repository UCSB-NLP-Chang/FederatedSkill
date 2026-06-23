#!/usr/bin/env python3
"""
Parse year markers from economic statistical tables.

Handles common formatting patterns:
- Trailing dots: '1994.' → 1994
- Prefixed quarters: '2025:I', '2025:II', '2025:III', '2025:IV'
- Continuation Roman numerals: 'I', 'II', 'III', 'IV' (forward-fills year)
- Standard years: '1994' → 1994

Usage:
    from parse_year_markers import parse_year_column, annualize_quarterly

    # Parse and annualize in one step
    df['Year'] = parse_year_column(df['Year marker'])
    df_annual = annualize_quarterly(df, year_col='Year', value_col='Private total')
"""

import re
import pandas as pd
import numpy as np


def parse_year_column(series):
    """
    Parse mixed year markers into integer years.

    Args:
        series: pandas Series containing year markers

    Returns:
        pandas Series of integer years (with quarters aggregated via mean)
    """
    series = series.astype(str).str.strip()
    result = []
    last_year = None

    for val in series:
        year, _ = _parse_single_marker(val, last_year)
        result.append(year)
        last_year = year

    return pd.Series(result, index=series.index)


def _parse_single_marker(val, last_year=None):
    """
    Parse a single year marker.

    Returns:
        tuple: (year, quarter_label or None)
    """
    s = str(val).strip()

    # Handle prefixed quarters: '2025:I' or '2025-Q1'
    if ':' in s:
        parts = s.split(':')
        year = int(float(parts[0].rstrip('.')))
        quarter = parts[1]
        return year, quarter

    if '-Q' in s.upper():
        match = re.match(r'(\d{4})[-\s]?[Qq](\d)', s)
        if match:
            return int(match.group(1)), match.group(2)

    # Handle standalone Roman numerals (continuation rows)
    if s.upper() in ['I', 'II', 'III', 'IV']:
        if last_year is None:
            raise ValueError(f"Roman numeral '{s}' appears without preceding year")
        return last_year, s

    # Handle trailing dots: '1994.' → 1994
    if '.' in s:
        return int(float(s)), None

    # Standard year
    return int(s), None


def annualize_quarterly(df, year_col='Year', value_col=None, agg_func='mean'):
    """
    Annualize a dataframe that may contain quarterly rows.

    Args:
        df: DataFrame with parsed year column
        year_col: name of the year column
        value_col: name of value column to aggregate (if None, aggregates all numeric)
        agg_func: 'mean' to average quarters, 'sum' to total them

    Returns:
        DataFrame with one row per year
    """
    df = df.copy()

    # Group by year
    if value_col:
        agg_dict = {value_col: agg_func}
        # Keep other columns (take first for non-numeric)
        for col in df.columns:
            if col != year_col and col != value_col:
                agg_dict[col] = 'first'
        return df.groupby(year_col, as_index=False).agg(agg_dict)
    else:
        # Auto-detect numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        numeric_cols = [c for c in numeric_cols if c != year_col]

        agg_dict = {col: agg_func for col in numeric_cols}
        for col in df.columns:
            if col not in numeric_cols and col != year_col:
                agg_dict[col] = 'first'

        return df.groupby(year_col, as_index=False).agg(agg_dict)


def parse_and_annualize(year_series, value_series, agg_func='mean'):
    """
    One-shot function: parse year markers and annualize values.

    Args:
        year_series: pandas Series of year markers
        value_series: pandas Series of values
        agg_func: aggregation function for multiple quarters

    Returns:
        tuple: (years_array, values_array) ready for analysis
    """
    years = parse_year_column(year_series)
    df = pd.DataFrame({'Year': years, 'Value': value_series})
    annual = annualize_quarterly(df, year_col='Year', value_col='Value', agg_func=agg_func)
    return annual['Year'].values, annual['Value'].values


if __name__ == "__main__":
    # Test cases
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Test 1: Trailing dots
        test1 = pd.Series(['1992.', '1993.', '1994.'])
        result1 = parse_year_column(test1)
        assert list(result1) == [1992, 1993, 1994], f"Failed trailing dots: {list(result1)}"
        print("Trailing dots handled")

        # Test 2: Mixed quarterly
        test2 = pd.Series(['2024.', '2025:I', 'II', 'III'])
        result2 = parse_year_column(test2)
        assert list(result2) == [2024, 2025, 2025, 2025], f"Failed quarterly: {list(result2)}"
        print("Quarterly markers handled")

        # Test 3: Annualization
        df_test = pd.DataFrame({
            'Year marker': ['2024.', '2025:I', 'II', 'III'],
            'Value': [100.0, 110.0, 120.0, 130.0]
        })
        df_test['Year'] = parse_year_column(df_test['Year marker'])
        annual = annualize_quarterly(df_test, year_col='Year', value_col='Value')
        assert len(annual) == 2, f"Expected 2 years, got {len(annual)}"
        assert annual[annual['Year'] == 2025]['Value'].iloc[0] == 120.0, "Mean calculation wrong"
        print("Annualization works (mean of 110, 120, 130 = 120)")

        # Test 4: One-shot function
        years, vals = parse_and_annualize(df_test['Year marker'], df_test['Value'])
        assert list(years) == [2024, 2025]
        print("One-shot parse_and_annualize works")

        print("\nAll tests passed!")