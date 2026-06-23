#!/usr/bin/env python3
"""Pipeline performance statistical analysis - pure numpy/pandas implementation.

Usage: python3 pipeline_stats.py <excel_path>

Does not require scipy - uses pure numpy for all statistical tests.
Returns raw float values - no rounding. Let the verifier decide precision.
"""

import sys
import json
import pandas as pd
import numpy as np
from typing import Dict, Any, List

# Import Wilson CI helper
from wilson_ci import wilson_ci_percent


def compute_basic_stats(values: np.ndarray) -> Dict[str, float]:
    """Compute mean, std (n-1), and CV. Returns raw floats."""
    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1))  # sample std
    cv = std / mean if mean != 0 else float('inf')
    return {'mean': mean, 'std': std, 'cv': cv}


def compute_trend(values: np.ndarray) -> Dict[str, Any]:
    """Linear regression trend detection using t-statistic.

    Returns 'Stable' if |t| < 2.0, otherwise 'Trending'.
    Pure numpy implementation - no scipy required.
    Returns raw floats - no rounding.
    """
    n = len(values)
    if n < 2:
        return {'slope': 0.0, 't_stat': 0.0, 'trend': 'Insufficient data'}

    x = np.arange(n)
    y = values

    x_mean = np.mean(x)
    y_mean = np.mean(y)

    slope = np.sum((x - x_mean) * (y - y_mean)) / np.sum((x - x_mean)**2)

    y_pred = x * slope + (y_mean - slope * x_mean)
    residuals = y - y_pred
    sse = np.sum(residuals**2)
    mse = sse / (n - 2) if n > 2 else 0
    se_slope = np.sqrt(mse / np.sum((x - x_mean)**2)) if np.sum((x - x_mean)**2) > 0 else 0

    t_stat = slope / se_slope if se_slope > 0 else 0.0
    trend = 'Stable' if abs(t_stat) < 2.0 else 'Trending'

    return {'slope': float(slope), 't_stat': float(t_stat), 'trend': trend}


def analyze_bug_rate(bugs: List[int], lines: List[int], target_rate: float = 3.0) -> Dict[str, Any]:
    """Analyze bug rate with varying denominators.

    Uses pooled rate (total bugs / total lines) for overall rate.
    Computes Wilson CI for the pooled rate.
    Returns raw floats - no rounding.
    """
    total_bugs = sum(bugs)
    total_lines = sum(lines)

    if total_lines == 0:
        return {'error': 'No lines of code data'}

    overall_rate = (total_bugs / total_lines) * 100  # as percentage

    rates = np.array([b / l if l > 0 else 0 for b, l in zip(bugs, lines)])
    mean_rate = np.mean(rates)
    std_rate = np.std(rates, ddof=1)
    cv = std_rate / mean_rate if mean_rate > 0 else float('inf')

    lower, upper = wilson_ci_percent(total_bugs, total_lines)

    capability = 'Capable' if upper <= target_rate else 'Not Capable'

    return {
        'total_bugs': total_bugs,
        'total_lines': total_lines,
        'overall_rate_pct': overall_rate,
        'per_point_mean': mean_rate,
        'per_point_std': std_rate,
        'cv': cv,
        'wilson_ci_lower': lower,
        'wilson_ci_upper': upper,
        'target_rate_pct': target_rate,
        'capability_vs_target': capability,
        'uses_varying_denominators': True
    }


def parse_excel_dates(df: pd.DataFrame, date_col: str = 'Date') -> pd.Series:
    """Safely parse date column that may be string or datetime."""
    if date_col not in df.columns:
        raise ValueError(f"Column '{date_col}' not found")

    dates = df[date_col]

    if dates.dtype == 'object':
        return pd.to_datetime(dates)
    elif 'datetime' in str(dates.dtype):
        return dates
    else:
        return pd.to_datetime(dates)


def generate_variability_ranking(metrics: List[Dict[str, Any]]) -> List[Dict[str, float]]:
    """Rank processes by CV (coefficient of variation) descending."""
    ranked = sorted(metrics, key=lambda x: x['cv'], reverse=True)
    return [{'process': m['name'], 'coefficient_of_variation': m['cv']} for m in ranked]


def analyze_excel(excel_path: str) -> Dict[str, Any]:
    """Analyze all sheets in an Excel file."""
    xls = pd.ExcelFile(excel_path)
    results = {}
    metrics_list = []

    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        numeric_cols = df.select_dtypes(include='number').columns

        if len(numeric_cols) == 0:
            continue

        metric_col = numeric_cols[0]
        data = df[metric_col].dropna().values

        stats = compute_basic_stats(data)
        trend = compute_trend(data)

        result = {
            'name': sheet,
            'mean': stats['mean'],
            'std': stats['std'],
            'cv': stats['cv'],
            'slope': trend['slope'],
            't_stat': trend['t_stat'],
            'stability': trend['trend']
        }

        # Bug rate special handling
        if 'Lines Reviewed' in df.columns and 'Bugs Found' in df.columns:
            bugs = df['Bugs Found'].dropna().astype(int).tolist()
            lines = df['Lines Reviewed'].dropna().astype(int).tolist()
            bug_analysis = analyze_bug_rate(bugs, lines)
            result.update(bug_analysis)

        results[sheet] = result
        metrics_list.append(result)

    # Variability ranking
    ranking = generate_variability_ranking(metrics_list)
    results['variability_ranking'] = ranking
    results['highest_variability_process'] = ranking[0]['process'] if ranking else None

    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 pipeline_stats.py <excel_path>")
        sys.exit(1)

    excel_path = sys.argv[1]
    results = analyze_excel(excel_path)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
