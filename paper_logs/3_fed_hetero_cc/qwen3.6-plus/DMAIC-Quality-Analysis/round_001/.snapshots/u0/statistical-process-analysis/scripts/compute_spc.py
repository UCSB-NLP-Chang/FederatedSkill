#!/usr/bin/env python3
"""Compute SPC and statistical metrics from a time-series CSV.

Uses scipy.stats library functions for all statistical tests to ensure
numerical accuracy. Do NOT implement tests manually—p-values of 0.0 or 1.0
indicate calculation errors.
"""
import argparse
import csv
import json
import math
import statistics
from datetime import datetime
from collections import defaultdict
from scipy import stats


def main():
    p = argparse.ArgumentParser(description="Compute SPC metrics from time-series CSV")
    p.add_argument("--input", required=True, help="Path to input CSV")
    p.add_argument("--date-col", default="Date", help="Date column name")
    p.add_argument("--value-col", default="ResolvedAlerts", help="Metric column name")
    p.add_argument("--target", type=float, required=True, help="Target value for t-test/Cpk")
    p.add_argument("--baseline", type=float, required=True, help="Baseline value for charter")
    p.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    p.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    p.add_argument("--imr-end", default=None, help="I-MR window end date (optional)")
    p.add_argument("--output", default="spc_metrics.json", help="Output JSON path")
    args = p.parse_args()

    start = datetime.strptime(args.start, "%Y-%m-%d")
    end = datetime.strptime(args.end, "%Y-%m-%d")
    imr_end = datetime.strptime(args.imr_end, "%Y-%m-%d") if args.imr_end else end

    # Load data
    rows = []
    with open(args.input) as f:
        reader = csv.DictReader(f)
        for r in reader:
            dt = datetime.strptime(r[args.date_col], "%Y-%m-%d")
            rows.append({"date": dt, "value": float(r[args.value_col])})

    def is_biz(dt):
        return dt.weekday() < 5  # Mon-Fri

    primary = [r for r in rows if start <= r["date"] <= end and is_biz(r["date"])]
    imr = [r for r in rows if start <= r["date"] <= imr_end and is_biz(r["date"])]

    vals = [r["value"] for r in primary]
    n = len(vals)
    if n == 0:
        raise ValueError("No business-day records found in primary window.")

    mean_val = statistics.mean(vals)
    std_val = statistics.stdev(vals) if n > 1 else 0.0

    # ANOVA by weekday using scipy.stats.f_oneway
    weekday_vals = defaultdict(list)
    for r in primary:
        weekday_vals[r["date"].strftime("%A")].append(r["value"])
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    day_means = {d: statistics.mean(weekday_vals[d]) for d in days if d in weekday_vals and weekday_vals[d]}

    anova_groups = [weekday_vals[d] for d in days if d in weekday_vals and weekday_vals[d]]
    if len(anova_groups) >= 2:
        f_stat, anova_p = stats.f_oneway(*anova_groups)
    else:
        f_stat, anova_p = float("nan"), float("nan")

    # I-MR control chart (MR-based limits, not SD-based)
    imr_vals = [r["value"] for r in imr]
    mr = [abs(imr_vals[i] - imr_vals[i - 1]) for i in range(1, len(imr_vals))]
    mr_bar = statistics.mean(mr) if mr else 0.0
    cl = statistics.mean(imr_vals)
    ucl = cl + 2.66 * mr_bar
    lcl = cl - 2.66 * mr_bar
    mr_ucl = 3.267 * mr_bar

    # Linear regression using scipy.stats.linregress
    x = list(range(n))
    y = vals
    slope, intercept, r_value, reg_p, std_err = stats.linregress(x, y)
    r2 = r_value ** 2

    # One-sample t-test vs target using scipy.stats.ttest_1samp
    t_stat, t_p = stats.ttest_1samp(vals, args.target)

    # 95% CI using t-distribution (not z=1.96)
    se_mean = std_val / math.sqrt(n) if n > 0 else 0
    ci_low, ci_high = stats.t.interval(0.95, df=n - 1, loc=mean_val, scale=se_mean)

    # Cpk (target as LSL)
    cpk = (mean_val - args.target) / (3 * std_val) if std_val > 0 else 0.0

    out = {
        "source_file": args.input,
        "filters": {
            "primary_date_range": f"{args.start} to {args.end} (inclusive)",
            "business_days_only": True,
            "imr_date_range": f"{args.start} to {args.imr_end or args.end} (inclusive)",
            "response_metric": args.value_col,
            "regression_predictor": "day_index"
        },
        "record_counts": {
            "total_records": len(rows),
            "primary_window_records": len([r for r in rows if start <= r["date"] <= end]),
            "primary_window_business_days": n,
            "imr_window_business_days": len(imr)
        },
        "charter_metrics": {
            "baseline_value": args.baseline,
            "target_value": args.target,
            "current_mean_value": mean_val
        },
        "anova_by_weekday": {
            "weekday_means": {d: day_means[d] for d in day_means},
            "p_value": anova_p,
            "f_statistic": f_stat,
            "highest_mean_day": max(day_means, key=day_means.get) if day_means else None,
            "lowest_mean_day": min(day_means, key=day_means.get) if day_means else None
        },
        "imr_summary": {
            "points": len(imr),
            "center_line": cl,
            "ucl": ucl,
            "lcl": lcl,
            "mr_bar": mr_bar,
            "mr_ucl": mr_ucl
        },
        "regression_day_index": {
            "slope": slope,
            "intercept": intercept,
            "r_value": r_value,
            "r_squared": r2,
            "p_value": reg_p,
            "n_observations": n
        },
        "ttest_vs_target": {
            "n": n,
            "mean_value": mean_val,
            "t_stat": t_stat,
            "p_value": t_p,
            "ci95_low": ci_low,
            "ci95_high": ci_high,
            "decision": "reject_h0" if t_p < 0.05 else "fail_to_reject_h0"
        },
        "capability_against_lsl": {
            "lsl": args.target,
            "std_dev_sample": std_val,
            "cpk_lower": cpk
        }
    }

    with open(args.output, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Metrics written to {args.output}")


if __name__ == "__main__":
    main()
