#!/usr/bin/env python3
"""Logistics reliability statistical analysis - pure numpy/pandas implementation.

Usage: python3 analyze_logistics.py <excel_path>
"""
import sys
import json
import pandas as pd
import numpy as np

def compute_basic_stats(values):
    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1))
    cv = std / mean if mean != 0 else float('inf')
    return {'mean': mean, 'std': std, 'cv': cv}

def compute_trend(values):
    n = len(values)
    if n < 2: return {'slope': 0.0, 't_stat': 0.0, 'stability': 'Insufficient data'}
    x = np.arange(n)
    y = values
    x_mean, y_mean = np.mean(x), np.mean(y)
    slope = np.sum((x - x_mean) * (y - y_mean)) / np.sum((x - x_mean)**2)
    y_pred = x * slope + (y_mean - slope * x_mean)
    residuals = y - y_pred
    sse = np.sum(residuals**2)
    mse = sse / (n - 2) if n > 2 else 0
    se_slope = np.sqrt(mse / np.sum((x - x_mean)**2)) if np.sum((x - x_mean)**2) > 0 else 0
    t_stat = slope / se_slope if se_slope > 0 else 0.0
    stability = 'Stable' if abs(t_stat) < 2.0 else 'Unstable'
    return {'slope': float(slope), 't_stat': float(t_stat), 'stability': stability}

def wilson_ci_percent(successes, trials, confidence=0.95):
    if trials == 0: return (0.0, 100.0)
    z = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}.get(confidence, 1.96)
    p = successes / trials
    n = trials
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denom
    return (max(0.0, center - margin) * 100, min(1.0, center + margin) * 100)

def analyze_excel(excel_path):
    xls = pd.ExcelFile(excel_path)
    results = {}
    metrics_list = []
    
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        numeric_cols = df.select_dtypes(include='number').columns
        if len(numeric_cols) == 0: continue
        
        if 'Shipments' in df.columns and 'Damaged' in df.columns:
            bugs = df['Damaged'].dropna().astype(int).tolist()
            lines = df['Shipments'].dropna().astype(int).tolist()
            total_damaged = sum(bugs)
            total_shipments = sum(lines)
            rate = (total_damaged / total_shipments) * 100 if total_shipments > 0 else 0
            lower, upper = wilson_ci_percent(total_damaged, total_shipments)
            target = 1.5
            capability = 'Capable' if upper <= target else 'Not Capable'
            res = {
                'overall_rate_pct': rate,
                'wilson_ci_lower': lower,
                'wilson_ci_upper': upper,
                'capability_vs_target': capability,
                'total_damaged': total_damaged,
                'total_shipments': total_shipments,
                'uses_varying_denominators': True,
                'target_rate_pct': target
            }
        else:
            metric_col = numeric_cols[0]
            data = df[metric_col].dropna().values
            stats = compute_basic_stats(data)
            trend = compute_trend(data)
            res = {**stats, **trend}
            
        results[sheet] = res
        metrics_list.append({'name': sheet, 'cv': res.get('cv', 0.0)})
        
    ranking = sorted(metrics_list, key=lambda x: x['cv'], reverse=True)
    results['variability_ranking'] = [{'process': m['name'], 'coefficient_of_variation': m['cv']} for m in ranking]
    results['highest_variability_process'] = ranking[0]['process'] if ranking else None
    return results

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_logistics.py <excel_path>")
        sys.exit(1)
    print(json.dumps(analyze_excel(sys.argv[1]), indent=2))

if __name__ == "__main__":
    main()