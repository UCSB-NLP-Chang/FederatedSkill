#!/usr/bin/env python3
"""
DMAIC Analyze Phase Statistical Calculation Script

Computes Six Sigma / process control metrics from a time-series CSV.
Requires: scipy

Usage:
  python3 spc_calculations.py \
    --csv data.csv \
    --primary-start 2025-01-04 --primary-end 2025-03-01 \
    --imr-start 2025-01-04 --imr-end 2025-02-21 \
    --target 560 --lsl 560 --baseline 500 \
    --output-json metrics.json --output-md brief.md

CRITICAL: The I-MR window (--imr-start to --imr-end) must end BEFORE Analyze phase data begins.
The primary window contains all analysis data; the I-MR window is a subset for stability analysis.
"""
import argparse
import csv
import json
import math
from datetime import datetime, date
from scipy import stats


def parse_date(s):
    return datetime.strptime(s, '%Y-%m-%d').date()


def safe_p_value(p):
    """Prevents 0.0 rounding for highly significant p-values."""
    if p < 1e-10:
        return 1e-15
    return round(p, 10)


def main():
    p = argparse.ArgumentParser(description='DMAIC Analyze Phase Statistical Analysis')
    p.add_argument('--csv', required=True, help='Input CSV path')
    p.add_argument('--primary-start', required=True, help='Primary window start date (YYYY-MM-DD)')
    p.add_argument('--primary-end', required=True, help='Primary window end date (YYYY-MM-DD)')
    p.add_argument('--imr-start', required=True, help='I-MR window start date (YYYY-MM-DD)')
    p.add_argument('--imr-end', required=True, help='I-MR window end date - MUST end before Analyze phase')
    p.add_argument('--target', type=float, required=True, help='Target value for t-test')
    p.add_argument('--lsl', type=float, required=True, help='Lower Specification Limit for Cpk')
    p.add_argument('--baseline', type=float, default=500.0, help='Baseline value')
    p.add_argument('--metric-col', default='ResolvedAlerts', help='Metric column name')
    p.add_argument('--output-json', default='metrics.json')
    p.add_argument('--output-md', default='brief.md')
    args = p.parse_args()

    # Load data
    rows = []
    with open(args.csv) as f:
        for r in csv.DictReader(f):
            rows.append({
                'date': parse_date(r['Date']),
                'stage': r['Stage'],
                'day': r['Day'],
                'val': float(r[args.metric_col])
            })

    # Parse date windows
    ps, pe = parse_date(args.primary_start), parse_date(args.primary_end)
    ims, ime = parse_date(args.imr_start), parse_date(args.imr_end)

    # Filter to primary window (business days only)
    primary = [r for r in rows if ps <= r['date'] <= pe]
    primary_biz = [r for r in primary if r['date'].weekday() < 5]

    # Filter to I-MR window (business days only) - MUST end before Analyze phase
    imr_biz = [r for r in primary if ims <= r['date'] <= ime and r['date'].weekday() < 5]

    vals = [r['val'] for r in primary_biz]
    imr_vals = [r['val'] for r in imr_biz]
    n = len(vals)
    mean_val = sum(vals) / n

    # ANOVA by weekday
    wd_groups = {i: [] for i in range(5)}
    wd_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    for r in primary_biz:
        wd_groups[r['date'].weekday()].append(r['val'])
    f_stat, anova_p = stats.f_oneway(*[wd_groups[i] for i in range(5)])
    wd_means = {wd_names[i]: round(sum(wd_groups[i]) / len(wd_groups[i]), 3) if wd_groups[i] else 0.0 for i in range(5)}

    # I-MR Control Chart (on stability window)
    mr = [abs(imr_vals[i] - imr_vals[i - 1]) for i in range(1, len(imr_vals))]
    mr_bar = sum(mr) / len(mr) if mr else 0.0
    cl = sum(imr_vals) / len(imr_vals)
    ucl = cl + 2.667 * mr_bar
    lcl = cl - 2.667 * mr_bar
    mr_ucl = 3.267 * mr_bar

    # Linear Regression (day index vs metric)
    x = list(range(1, n + 1))
    slope, intercept, r_val, p_val_reg, _ = stats.linregress(x, vals)

    # One-sample t-test vs target
    t_stat, p_val_t = stats.ttest_1samp(vals, args.target)
    ci_low, ci_high = stats.t.interval(0.95, n - 1, loc=mean_val, scale=stats.sem(vals))
    decision = "reject_h0" if p_val_t < 0.05 else "fail_to_reject_h0"

    # Process Capability (Cpk)
    var = sum((v - mean_val) ** 2 for v in vals) / (n - 1)
    std_dev = math.sqrt(var)
    cpk_lower = (mean_val - args.lsl) / (3 * std_dev)

    # Build output JSON
    out = {
        "source_file": args.csv,
        "filters": {
            "primary_analysis_window": {
                "start_date": args.primary_start,
                "end_date": args.primary_end,
                "business_days_only": True,
                "record_count": n
            },
            "imr_analysis_window": {
                "start_date": args.imr_start,
                "end_date": args.imr_end,
                "business_days_only": True,
                "record_count": len(imr_vals)
            }
        },
        "record_counts": {
            "total_rows": len(rows),
            "primary_window_all_days": len(primary),
            "primary_window_business_days": n,
            "imr_window_business_days": len(imr_vals)
        },
        "charter_metrics": {
            "baseline_value": args.baseline,
            "target_value": args.target,
            "current_mean_value": round(mean_val, 4)
        },
        "anova_by_weekday": {
            "weekday_means": wd_means,
            "p_value": safe_p_value(anova_p),
            "f_statistic": round(f_stat, 4),
            "highest_mean_day": max(wd_means, key=wd_means.get),
            "lowest_mean_day": min(wd_means, key=wd_means.get)
        },
        "imr_summary": {
            "points": len(imr_vals),
            "center_line": round(cl, 4),
            "ucl": round(ucl, 4),
            "lcl": round(lcl, 4),
            "mr_bar": round(mr_bar, 4),
            "mr_ucl": round(mr_ucl, 4)
        },
        "regression_day_index": {
            "slope": round(slope, 6),
            "intercept": round(intercept, 3),
            "r_value": round(r_val, 4),
            "r_squared": round(r_val ** 2, 4),
            "p_value": safe_p_value(p_val_reg),
            "n_observations": n
        },
        "ttest_vs_target": {
            "target": args.target,
            "n": n,
            "mean_value": round(mean_val, 3),
            "std_dev": round(std_dev, 3),
            "t_stat": round(t_stat, 4),
            "p_value": safe_p_value(p_val_t),
            "ci95_low": round(ci_low, 3),
            "ci95_high": round(ci_high, 3),
            "decision": decision
        },
        "capability_against_lsl": {
            "lsl": args.lsl,
            "mean": round(mean_val, 3),
            "std_dev_sample": round(std_dev, 3),
            "cpk_lower": round(cpk_lower, 4)
        }
    }

    with open(args.output_json, 'w') as f:
        json.dump(out, f, indent=2)

    # Generate Markdown brief
    in_control = all(lcl <= v <= ucl for v in imr_vals)
    brief = f"""# DMAIC Analyze Tollgate Brief

## Project Charter
| Metric | Value |
|---|---|
| **Baseline** | {args.baseline} |
| **Target** | {args.target} |
| **Current Mean** | {round(mean_val, 2)} |

## Key Findings
- **ANOVA**: p = {safe_p_value(anova_p):.6f} — {'Significant' if anova_p < 0.05 else 'Not significant'} weekday effect. Highest: {max(wd_means, key=wd_means.get)}, Lowest: {min(wd_means, key=wd_means.get)}.
- **I-MR**: Process {'in control' if in_control else 'out of control'}. Centered at {round(cl, 2)}.
- **Regression**: Slope = {round(slope, 4)}/day, p = {safe_p_value(p_val_reg):.6f}. {'Positive trend' if slope > 0 else 'Negative trend'}.
- **t-test**: t = {round(t_stat, 2)}, p = {safe_p_value(p_val_t):.6f}. {decision.replace('_', ' ').title()}. Mean is {'below' if mean_val < args.target else 'above'} target.
- **Capability**: Cpk(lower) = {round(cpk_lower, 4)}. {'Process capable' if cpk_lower >= 1.33 else 'Process not capable'}.

## Operational Impacts
1. [Impact 1]
2. [Impact 2]
3. [Impact 3]
4. [Impact 4]

## Next Steps
1. [Action 1] (Owner: [Name], Due: [Date])
2. [Action 2] (Owner: [Name], Due: [Date])
"""
    with open(args.output_md, 'w') as f:
        f.write(brief)

    print(f"Analysis complete. JSON: {args.output_json}, Brief: {args.output_md}")
    print(f"Primary window: {n} business days")
    print(f"I-MR window: {len(imr_vals)} business days")


if __name__ == '__main__':
    main()
