#!/usr/bin/env python3
"""Pipeline performance statistical analysis - pure numpy/pandas implementation.

Handles build duration, bug rate, and deployment failure analysis.
Does not require scipy - uses pure numpy for all statistical tests.
"""

import pandas as pd
import numpy as np
import json
from typing import Dict, Any, List, Tuple


def compute_basic_stats(values: np.ndarray) -> Dict[str, float]:
    """Compute mean, std (n-1), and CV."""
    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1))  # sample std
    cv = std / mean if mean != 0 else float('inf')
    return {'mean': mean, 'std': std, 'cv': cv}


def compute_trend(values: np.ndarray, dates: List) -> Dict[str, Any]:
    """Simple linear regression trend detection using t-statistic.
    
    Returns 'Stable' if |t| < 2.0, otherwise 'Trending'.
    Pure numpy implementation - no scipy required.
    """
    n = len(values)
    if n < 2:
        return {'slope': 0, 't_stat': 0, 'trend': 'Insufficient data'}
    
    x = np.arange(n)
    y = values
    
    # Linear regression coefficients
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    
    slope = np.sum((x - x_mean) * (y - y_mean)) / np.sum((x - x_mean)**2)
    
    # Standard error of slope
    y_pred = x * slope + (y_mean - slope * x_mean)
    residuals = y - y_pred
    sse = np.sum(residuals**2)
    mse = sse / (n - 2)
    se_slope = np.sqrt(mse / np.sum((x - x_mean)**2))
    
    # t-statistic
    t_stat = slope / se_slope if se_slope > 0 else 0
    
    trend = 'Stable' if abs(t_stat) < 2.0 else 'Trending'
    
    return {'slope': float(slope), 't_stat': float(t_stat), 'trend': trend}


def analyze_bug_rate(bugs: List[int], lines: List[int], target_rate: float = 3.0) -> Dict[str, Any]:
    """Analyze bug rate with varying denominators.
    
    Uses pooled rate (total bugs / total lines) for overall rate.
    Computes Wilson CI for the pooled rate.
    """
    total_bugs = sum(bugs)
    total_lines = sum(lines)
    
    if total_lines == 0:
        return {'error': 'No lines of code data'}
    
    overall_rate = (total_bugs / total_lines) * 100  # as percentage
    
    # Per-point rates for CV calculation
    rates = np.array([b / l if l > 0 else 0 for b, l in zip(bugs, lines)])
    mean_rate = np.mean(rates)
    std_rate = np.std(rates, ddof=1)
    cv = std_rate / mean_rate if mean_rate > 0 else float('inf')
    
    # Wilson CI (import from wilson_ci.py in practice)
    from wilson_ci import wilson_ci_percent
    lower, upper = wilson_ci_percent(total_bugs, total_lines)
    
    # Capability assessment
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
    """Safely parse date column that may be string or datetime.
    
    Anti-pattern: Don't call .date on string columns.
    """
    if date_col not in df.columns:
        raise ValueError(f"Column '{date_col}' not found")
    
    dates = df[date_col]
    
    if dates.dtype == 'object':
        # String dates - parse them
        return pd.to_datetime(dates)
    elif 'datetime' in str(dates.dtype):
        return dates
    else:
        return pd.to_datetime(dates)


def generate_variability_ranking(metrics: List[Dict[str, Any]]) -> List[Dict[str, float]]:
    """Rank processes by CV (coefficient of variation) descending.
    
    Higher CV = higher variability = higher risk.
    """
    ranked = sorted(metrics, key=lambda x: x['cv'], reverse=True)
    return [{'process': m['name'], 'coefficient_of_variation': m['cv']} for m in ranked]


if __name__ == "__main__":
    # Example usage
    print("Pipeline stats module loaded.")
    print("Key functions: compute_basic_stats, compute_trend, analyze_bug_rate")
