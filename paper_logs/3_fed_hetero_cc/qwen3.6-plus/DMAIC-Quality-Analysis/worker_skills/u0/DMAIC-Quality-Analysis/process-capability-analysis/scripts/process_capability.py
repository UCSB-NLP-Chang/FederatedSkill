#!/usr/bin/env python3
"""Process capability statistical analysis - pure numpy/pandas implementation.

Usage: python3 process_capability.py <excel_path>

No scipy required - uses pure numpy for all statistical tests.
"""
import sys
import json
import pandas as pd
import numpy as np


def compute_basic_stats(values):
    """Compute mean, sample std (n-1), and CV."""
    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1))
    cv = std / mean if mean != 0 else float('inf')
    return {'mean': mean, 'sample_std': std, 'cv': cv}


def compute_trend(values):
    """Simple linear regression trend detection using t-statistic.
    
    Returns 'Stable' if |t| < 2.0, otherwise 'Trending'.
    Pure numpy implementation - no scipy required.
    """
    n = len(values)
    if n < 2:
        return {'slope': 0.0, 't_stat': 0.0, 'stability': 'Insufficient data'}
    
    x = np.arange(n)
    y = values
    x_mean, y_mean = np.mean(x), np.mean(y)
    
    slope = np.sum((x - x_mean) * (y - y_mean)) / np.sum((x - x_mean)**2)
    
    # Standard error of slope
    y_pred = x * slope + (y_mean - slope * x_mean)
    residuals = y - y_pred
    sse = np.sum(residuals**2)
    mse = sse / (n - 2) if n > 2 else 0
    se_slope = np.sqrt(mse / np.sum((x - x_mean)**2)) if np.sum((x - x_mean)**2) > 0 else 0
    
    t_stat = slope / se_slope if se_slope > 0 else 0.0
    stability = 'Stable' if abs(t_stat) < 2.0 else 'Trending'
    
    return {'slope': float(slope), 't_stat': float(t_stat), 'stability': stability}


def wilson_ci_percent(successes, trials, confidence=0.95):
    """Wilson score confidence interval as percentage (0-100 scale).
    
    Pure numpy implementation - no scipy required.
    """
    if trials == 0:
        return [0.0, 100.0]
    
    z = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}.get(confidence, 1.96)
    p = successes / trials
    n = trials
    
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denom
    
    lower = max(0.0, center - margin) * 100
    upper = min(1.0, center + margin) * 100
    
    return [lower, upper]


def analyze_process_capability(excel_path, target_rate=1.0):
    """Analyze process capability from Excel file.
    
    Handles task duration, failure rate, and system errors sheets.
    Uses pooled rate for failure/error rates.
    """
    xls = pd.ExcelFile(excel_path)
    results = {}
    metrics_list = []
    
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        numeric_cols = df.select_dtypes(include='number').columns
        if len(numeric_cols) == 0:
            continue
        
        # Check for failure rate pattern (Failures/Units or similar)
        if 'Failures' in df.columns and 'Units' in df.columns:
            failures = df['Failures'].dropna().astype(int).tolist()
            units = df['Units'].dropna().astype(int).tolist()
            total_failures = sum(failures)
            total_units = sum(units)
            rate = (total_failures / total_units) * 100 if total_units > 0 else 0
            ci = wilson_ci_percent(total_failures, total_units)
            capability = 'Capable' if ci[1] <= target_rate else 'Not Capable'
            
            # CV from per-point rates
            rates = np.array([f / u if u > 0 else 0 for f, u in zip(failures, units)])
            mean_rate = np.mean(rates)
            std_rate = np.std(rates, ddof=1) if len(rates) > 1 else 0
            cv = std_rate / mean_rate if mean_rate > 0 else float('inf')
            
            res = {
                'overall_rate_pct': rate,
                'wilson_95_ci_pct': ci,
                'total_failures': total_failures,
                'total_units_processed': total_units,
                'target_rate_pct': target_rate,
                'capability_vs_target': capability,
                'uses_varying_denominators': True,
                'per_point_mean_proportion': float(mean_rate),
                'per_point_sample_std': float(std_rate),
                'cv': cv,
                'trend_analysis': compute_trend(rates)
            }
        else:
            # Single metric column
            metric_col = numeric_cols[0]
            data = df[metric_col].dropna().values
            stats = compute_basic_stats(data)
            trend = compute_trend(data)
            res = {**stats, 'n': len(data), 'trend_analysis': trend, 'min': float(np.min(data)), 'max': float(np.max(data))}
        
        results[sheet.lower().replace(' ', '_')] = res
        metrics_list.append({'name': sheet, 'cv': res.get('cv', 0.0)})
    
    # Variability ranking (descending by CV)
    ranking = sorted(metrics_list, key=lambda x: x['cv'], reverse=True)
    results['variability_ranking'] = [{'process': m['name'], 'cv': m['cv']} for m in ranking]
    results['highest_variability_process'] = ranking[0]['name'] if ranking else None
    results['highest_risk_statement'] = f"{ranking[0]['name']} is the highest-risk process." if ranking else None
    
    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 process_capability.py <excel_path>")
        sys.exit(1)
    
    result = analyze_process_capability(sys.argv[1])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
