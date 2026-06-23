#!/usr/bin/env python3
"""
DMAIC Analyze Phase Statistical Analysis Template
Generates metrics JSON and tollgate brief matching verifier schema.

Usage:
    python3 analysis_template.py --input data.csv --baseline 500 --target 560 --lsl 560 \
        --output-prefix tollgate [--primary-days 40] [--imr-days 35]
    
    # With explicit date ranges (phase-aware filtering):
    python3 analysis_template.py --input data.csv --baseline 115 --target 140 --lsl 140 \
        --primary-start 2025-01-04 --primary-end 2025-03-01 --imr-end 2025-02-21 \
        --metric-col ClosedWorkOrders --output-prefix analyze
"""
import argparse
import json
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime


def filter_business_days(df):
    """Filter DataFrame to business days only (Mon-Fri)"""
    df = df.copy()
    df['Date'] = pd.to_datetime(df['Date'])
    df['weekday_num'] = df['Date'].dt.dayofweek  # Monday=0, Sunday=6
    business_days = df[df['weekday_num'] < 5].copy()
    return business_days.sort_values('Date').reset_index(drop=True)


def calculate_anova(df, metric_col):
    """One-way ANOVA by weekday"""
    weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    groups = []

    for day in weekday_names:
        day_data = df[df['Day'] == day][metric_col]
        if len(day_data) > 0:
            groups.append(day_data.values)

    if len(groups) < 2:
        return None

    f_stat, p_value = stats.f_oneway(*groups)

    # Calculate weekday means
    weekday_means = {}
    for day in weekday_names:
        day_data = df[df['Day'] == day][metric_col]
        if len(day_data) > 0:
            weekday_means[day] = round(float(day_data.mean()), 3)

    highest = max(weekday_means, key=weekday_means.get) if weekday_means else None
    lowest = min(weekday_means, key=weekday_means.get) if weekday_means else None

    return {
        'weekday_means': weekday_means,
        'p_value': float(p_value),
        'f_statistic': round(float(f_stat), 4),
        'highest_mean_day': highest,
        'lowest_mean_day': lowest
    }


def calculate_imr(data, window_size):
    """
    Calculate I-MR (Individuals-Moving Range) control chart.
    Uses MR-bar/d2 method for sigma estimate.
    """
    subset = data.iloc[:window_size].values
    n = len(subset)

    # Individuals chart
    center = np.mean(subset)

    # Moving Range
    mr = np.abs(np.diff(subset))
    mr_bar = np.mean(mr)

    # Control limits using d2 = 1.128 for n=2
    sigma_est = mr_bar / 1.128
    ucl = center + 3 * sigma_est
    lcl = center - 3 * sigma_est

    # MR chart upper control limit
    mr_ucl = 3.267 * mr_bar

    return {
        'points': n,
        'center_line': round(float(center), 3),
        'ucl': round(float(ucl), 3),
        'lcl': round(float(lcl), 3),
        'mr_bar': round(float(mr_bar), 3),
        'mr_ucl': round(float(mr_ucl), 3)
    }


def calculate_regression(data):
    """Linear regression on day index vs metric"""
    x = np.arange(len(data))
    y = data.values

    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

    return {
        'slope': round(float(slope), 6),
        'intercept': round(float(intercept), 3),
        'r_value': round(float(r_value), 4),
        'r_squared': round(float(r_value ** 2), 4),
        'p_value': float(p_value),
        'n_observations': len(data)
    }


def calculate_ttest(data, target):
    """One-sample t-test against target value"""
    t_stat, p_value = stats.ttest_1samp(data, target)

    mean_val = np.mean(data)
    sem = stats.sem(data)
    n = len(data)

    ci = stats.t.interval(0.95, n - 1, loc=mean_val, scale=sem)

    return {
        'target': float(target),
        'n': n,
        'mean_value': round(float(mean_val), 2),
        'std_dev': round(float(np.std(data, ddof=1)), 3),
        't_stat': round(float(t_stat), 4),
        'p_value': float(p_value),
        'ci95_low': round(float(ci[0]), 3),
        'ci95_high': round(float(ci[1]), 3),
        'decision': 'reject_h0' if p_value < 0.05 else 'fail_to_reject_h0'
    }


def calculate_capability(data, lsl):
    """Calculate Cpk (process capability index) against LSL"""
    mean_val = np.mean(data)
    sigma = np.std(data, ddof=1)  # Sample std dev

    cpk = (mean_val - lsl) / (3 * sigma)

    return {
        'lsl': float(lsl),
        'mean': round(float(mean_val), 2),
        'std_dev_sample': round(float(sigma), 3),
        'cpk_lower': round(float(cpk), 4)
    }


def main():
    parser = argparse.ArgumentParser(description='DMAIC Analyze Phase Statistical Analysis')
    parser.add_argument('--input', required=True, help='Input CSV path')
    parser.add_argument('--baseline', type=float, required=True, help='Baseline value')
    parser.add_argument('--target', type=float, required=True, help='Target value')
    parser.add_argument('--lsl', type=float, required=True, help='Lower Specification Limit')
    parser.add_argument('--output-prefix', default='analyze', help='Output file prefix')
    parser.add_argument('--primary-days', type=int, default=40, help='Business days for primary analysis')
    parser.add_argument('--imr-days', type=int, default=35, help='Business days for I-MR chart')
    parser.add_argument('--metric-col', default='ResolvedAlerts', help='Metric column name')
    parser.add_argument('--primary-start', help='Primary window start date (YYYY-MM-DD)')
    parser.add_argument('--primary-end', help='Primary window end date (YYYY-MM-DD)')
    parser.add_argument('--imr-end', help='I-MR window end date (YYYY-MM-DD)')

    args = parser.parse_args()

    # Load and filter to business days
    df_raw = pd.read_csv(args.input)
    df = filter_business_days(df_raw)

    # Define analysis windows
    if args.primary_start and args.primary_end:
        # Use explicit date ranges
        primary_start = pd.to_datetime(args.primary_start)
        primary_end = pd.to_datetime(args.primary_end)
        primary_data = df[(df['Date'] >= primary_start) & (df['Date'] <= primary_end)].copy()
        
        if args.imr_end:
            imr_end = pd.to_datetime(args.imr_end)
            imr_data = df[(df['Date'] >= primary_start) & (df['Date'] <= imr_end)].copy()
        else:
            imr_data = primary_data.iloc[:args.imr_days].copy()
    else:
        # Use last N days approach
        primary_data = df.iloc[-args.primary_days:].copy()
        imr_data = primary_data.iloc[:args.imr_days].copy()

    metric = args.metric_col

    # Build results matching schema
    results = {
        'source_file': args.input,
        'filters': {
            'primary_analysis_window': {
                'start_date': primary_data['Date'].min().strftime('%Y-%m-%d'),
                'end_date': primary_data['Date'].max().strftime('%Y-%m-%d'),
                'business_days_only': True,
                'record_count': len(primary_data)
            },
            'imr_analysis_window': {
                'start_date': imr_data['Date'].min().strftime('%Y-%m-%d'),
                'end_date': imr_data['Date'].max().strftime('%Y-%m-%d'),
                'business_days_only': True,
                'record_count': len(imr_data)
            }
        },
        'record_counts': {
            'total_records_in_source': len(df_raw),
            'primary_window_records': len(primary_data),
            'imr_window_records': len(imr_data)
        },
        'charter_metrics': {
            'baseline_value': args.baseline,
            'target_value': args.target,
            'current_mean_value': round(float(primary_data[metric].mean()), 2)
        },
        'anova_by_weekday': calculate_anova(primary_data, metric),
        'imr_summary': calculate_imr(primary_data[metric], args.imr_days),
        'regression_day_index': calculate_regression(primary_data[metric]),
        'ttest_vs_target': calculate_ttest(primary_data[metric], args.target),
        'capability_against_lsl': calculate_capability(primary_data[metric], args.lsl)
    }

    # Write JSON
    json_path = f'{args.output_prefix}_metrics.json'
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)

    # Generate brief
    in_control = all(
        results['imr_summary']['lcl'] <= v <= results['imr_summary']['ucl']
        for v in imr_data[metric].values
    )

    brief = f"""# DMAIC Analyze Tollgate Brief

## Project Charter
| Metric | Value |
|---|---|
| **Baseline** | {args.baseline} |
| **Target** | {args.target} |
| **Current Mean** | {results['charter_metrics']['current_mean_value']} |

## Key Findings
- **ANOVA**: p = {results['anova_by_weekday']['p_value']:.4f} — {'Significant' if results['anova_by_weekday']['p_value'] < 0.05 else 'Not significant'} weekday effect.
  Highest: {results['anova_by_weekday']['highest_mean_day']}, Lowest: {results['anova_by_weekday']['lowest_mean_day']}
- **I-MR**: Process {'in control' if in_control else 'out of control'}. Centered at {results['imr_summary']['center_line']:.2f}.
- **Regression**: Slope = {results['regression_day_index']['slope']:.4f}/day, p = {results['regression_day_index']['p_value']:.4f}.
- **t-test**: t = {results['ttest_vs_target']['t_stat']:.2f}, p = {results['ttest_vs_target']['p_value']:.4f}. {results['ttest_vs_target']['decision'].replace('_', ' ').title()}.
- **Capability**: Cpk(lower) = {results['capability_against_lsl']['cpk_lower']:.3f}.

## Operational Impacts
1. [Impact 1 - describe based on findings]
2. [Impact 2]
3. [Impact 3]
4. [Impact 4]

## Next Steps
1. [Action 1] (Owner: [Name], Due: [Date])
2. [Action 2] (Owner: [Name], Due: [Date])
"""

    brief_path = f'{args.output_prefix}_brief.md'
    with open(brief_path, 'w') as f:
        f.write(brief)

    print(f"Analysis complete:")
    print(f"  JSON: {json_path}")
    print(f"  Brief: {brief_path}")
    print(f"  Primary window: {len(primary_data)} business days")
    print(f"  I-MR window: {len(imr_data)} business days")


if __name__ == '__main__':
    main()
