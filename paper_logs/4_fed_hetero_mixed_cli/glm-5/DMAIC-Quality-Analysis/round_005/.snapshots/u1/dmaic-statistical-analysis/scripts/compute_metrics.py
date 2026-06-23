#!/usr/bin/env python3
"""
Computes DMAIC Analyze phase metrics from time-series CSV or Excel data.
Requires: scipy, pandas, numpy, openpyxl (for Excel)
Usage: python3 compute_metrics.py --input data.csv --input-format csv \
  --primary-start 2025-01-04 --primary-end 2025-03-01 \
  --imr-start 2025-01-04 --imr-end 2025-02-21 \
  --target 560 --lsl 560 --baseline 500 \
  --metric-col ResolvedAlerts \
  --output-json metrics.json --output-md brief.md

For Excel files: --input data.xlsx --input-format excel
"""
import argparse
import csv
import json
import math
from datetime import datetime, date
from scipy import stats

def parse_date(s):
    if isinstance(s, date):
        return s
    if isinstance(s, datetime):
        return s.date()
    return datetime.strptime(str(s).strip(), '%Y-%m-%d').date()

def safe_p(p):
    """Prevents 0.0 rounding for highly significant p-values."""
    if p == 0.0 or p < 1e-10:
        return 1e-15
    return round(p, 6)

def load_csv(path, metric_col):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            rows.append({
                'date': parse_date(r['Date']),
                'stage': r['Stage'].strip(),
                'day': r['Day'].strip(),
                'val': float(r[metric_col])
            })
    return rows

def load_excel(path, metric_col):
    try:
        import openpyxl
    except ImportError:
        raise ImportError("openpyxl required for Excel input: pip install openpyxl")
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    rows = []
    header = None
    for row in ws.iter_rows(values_only=True):
        if header is None:
            header = [str(c).strip() if c else '' for c in row]
            continue
        if len(row) < 4:
            continue
        rec = dict(zip(header, row))
        date_val = rec.get('Date')
        stage_val = rec.get('Stage', '')
        day_val = rec.get('Day', '')
        metric_val = rec.get(metric_col)
        if date_val is None or metric_val is None:
            continue
        rows.append({
            'date': parse_date(date_val),
            'stage': str(stage_val).strip(),
            'day': str(day_val).strip(),
            'val': float(metric_val)
        })
    return rows

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True, help='Path to CSV or Excel file')
    p.add_argument('--input-format', choices=['csv', 'excel'], default='csv',
                   help='Input file format (default: csv)')
    p.add_argument('--primary-start', required=True)
    p.add_argument('--primary-end', required=True)
    p.add_argument('--imr-start', required=True)
    p.add_argument('--imr-end', required=True)
    p.add_argument('--target', type=float, required=True)
    p.add_argument('--lsl', type=float, required=True)
    p.add_argument('--baseline', type=float, default=500.0)
    p.add_argument('--metric-col', default='ResolvedAlerts', help='Column name for metric values')
    p.add_argument('--output-json', default='metrics.json')
    p.add_argument('--output-md', default='brief.md')
    args = p.parse_args()

    if args.input_format == 'excel':
        rows = load_excel(args.input, args.metric_col)
    else:
        rows = load_csv(args.input, args.metric_col)

    ps, pe = parse_date(args.primary_start), parse_date(args.primary_end)
    ims, ime = parse_date(args.imr_start), parse_date(args.imr_end)

    primary = [r for r in rows if ps <= r['date'] <= pe]
    primary_biz = [r for r in primary if r['date'].weekday() < 5]
    imr_biz = [r for r in primary if ims <= r['date'] <= ime and r['date'].weekday() < 5]

    vals = [r['val'] for r in primary_biz]
    imr_vals = [r['val'] for r in imr_biz]
    n = len(vals)
    if n == 0:
        raise ValueError("No business days in primary window")
    mean_val = sum(vals) / n

    # ANOVA by weekday
    wd_groups = {i: [] for i in range(5)}
    wd_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    for r in primary_biz:
        wd_groups[r['date'].weekday()].append(r['val'])
    wd_means = {}
    for i in range(5):
        if wd_groups[i]:
            wd_means[wd_names[i]] = round(sum(wd_groups[i]) / len(wd_groups[i]), 4)

    valid_groups = [wd_groups[i] for i in range(5) if wd_groups[i]]
    if len(valid_groups) >= 2:
        f_stat, anova_p = stats.f_oneway(*valid_groups)
    else:
        f_stat, anova_p = 0.0, 1.0

    highest_day = max(wd_means, key=wd_means.get) if wd_means else None
    lowest_day = min(wd_means, key=wd_means.get) if wd_means else None

    # I-MR Control Chart
    mr = [abs(imr_vals[i] - imr_vals[i-1]) for i in range(1, len(imr_vals))]
    mr_bar = sum(mr) / len(mr) if mr else 0.0
    cl = sum(imr_vals) / len(imr_vals) if imr_vals else 0.0
    sigma_est = mr_bar / 1.128  # d2 for n=2
    ucl = cl + 3 * sigma_est
    lcl = cl - 3 * sigma_est
    mr_ucl = 3.267 * mr_bar

    # Linear Regression (day index vs metric)
    x = list(range(1, n + 1))
    slope, intercept, r_val, p_val_reg, _ = stats.linregress(x, vals)

    # One-sample t-test vs Target
    t_stat, p_val_t = stats.ttest_1samp(vals, args.target)
    sem = stats.sem(vals)
    ci_low, ci_high = stats.t.interval(0.95, n-1, loc=mean_val, scale=sem)
    decision = "reject_h0" if p_val_t < 0.05 else "fail_to_reject_h0"

    # Process Capability (Cpk lower)
    var = sum((v - mean_val)**2 for v in vals) / (n - 1)
    std_dev = math.sqrt(var)
    cpk_lower = (mean_val - args.lsl) / (3 * std_dev)

    out = {
        "source_file": args.input,
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
            "total_records_in_source": len(rows),
            "primary_window_records": n,
            "imr_window_records": len(imr_vals)
        },
        "charter_metrics": {
            "baseline_value": args.baseline,
            "target_value": args.target,
            "current_mean_value": round(mean_val, 4)
        },
        "anova_by_weekday": {
            "weekday_means": wd_means,
            "p_value": safe_p(anova_p),
            "f_statistic": round(f_stat, 4),
            "highest_mean_day": highest_day,
            "lowest_mean_day": lowest_day
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
            "intercept": round(intercept, 4),
            "r_value": round(r_val, 4),
            "r_squared": round(r_val**2, 4),
            "p_value": safe_p(p_val_reg),
            "n_observations": n
        },
        "ttest_vs_target": {
            "target": args.target,
            "n": n,
            "mean_value": round(mean_val, 4),
            "std_dev": round(std_dev, 4),
            "t_stat": round(t_stat, 4),
            "p_value": safe_p(p_val_t),
            "ci95_low": round(ci_low, 4),
            "ci95_high": round(ci_high, 4),
            "decision": decision
        },
        "capability_against_lsl": {
            "lsl": args.lsl,
            "mean": round(mean_val, 4),
            "std_dev_sample": round(std_dev, 4),
            "cpk_lower": round(cpk_lower, 4)
        }
    }

    with open(args.output_json, 'w') as f:
        json.dump(out, f, indent=2)

    in_control = all(lcl <= v <= ucl for v in imr_vals)
    brief = f"""# DMAIC Analyze Tollgate Brief

## Project Charter
| Metric | Value |
|---|---|
| **Baseline** | {args.baseline} |
| **Target** | {args.target} |
| **Current Mean** | {round(mean_val, 2)} |

## Key Findings
- **ANOVA**: p = {safe_p(anova_p)} — {'Significant' if anova_p < 0.05 else 'Not significant'} weekday effect. Highest: {highest_day}, Lowest: {lowest_day}.
- **I-MR**: Process {'in control' if in_control else 'out of control'}. Centered at {round(cl, 2)}.
- **Regression**: Slope = {round(slope, 4)}/day, p = {safe_p(p_val_reg)}. {'Positive trend' if slope > 0 else 'Negative trend'}.
- **t-test**: t = {round(t_stat, 2)}, p = {safe_p(p_val_t)}. {decision.replace('_', ' ').title()}. Mean is {'below' if mean_val < args.target else 'above'} target.
- **Capability**: Cpk(lower) = {round(cpk_lower, 3)}. {'Process capable' if cpk_lower >= 1.33 else 'Process not capable'}.

## Operational Impacts
1. [Impact 1 - TBD]
2. [Impact 2 - TBD]
3. [Impact 3 - TBD]
4. [Impact 4 - TBD]

## Next Steps
1. [Action 1 - TBD] (Owner: [Name], Due: [Date])
2. [Action 2 - TBD] (Owner: [Name], Due: [Date])
"""
    with open(args.output_md, 'w') as f:
        f.write(brief)
    print(f"Metrics written to {args.output_json}")
    print(f"Brief written to {args.output_md}")

if __name__ == '__main__':
    main()
