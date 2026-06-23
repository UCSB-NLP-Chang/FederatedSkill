#!/usr/bin/env python3
"""Compute SPC and statistical metrics from a time-series CSV.

Uses scipy for all hypothesis tests to avoid arithmetic errors.
Outputs full-precision values; do not round JSON output.
"""
import argparse
import csv
import json
from datetime import datetime
from collections import defaultdict
import numpy as np
from scipy import stats


# Machine epsilon for p-value clamping
EPS = np.finfo(float).eps


def clamp_pvalue(p):
    """Clamp p-value to avoid exactly 0.0 or 1.0, which indicate errors."""
    return max(EPS, min(1.0 - EPS, float(p)))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--date-col", default="Date")
    p.add_argument("--value-col", default="ResolvedAlerts")
    p.add_argument("--target", type=float, required=True)
    p.add_argument("--baseline", type=float, required=True)
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--imr-end", default=None)
    p.add_argument("--output", default="spc_metrics.json")
    args = p.parse_args()

    start = datetime.strptime(args.start, "%Y-%m-%d")
    end = datetime.strptime(args.end, "%Y-%m-%d")
    imr_end = datetime.strptime(args.imr_end, "%Y-%m-%d") if args.imr_end else end

    rows = []
    with open(args.input) as f:
        reader = csv.DictReader(f)
        for r in reader:
            dt = datetime.strptime(r[args.date_col], "%Y-%m-%d")
            rows.append({"date": dt, "value": float(r[args.value_col])})

    def is_biz(dt):
        return dt.weekday() < 5

    primary = [r for r in rows if start <= r["date"] <= end and is_biz(r["date"])]
    imr = [r for r in rows if start <= r["date"] <= imr_end and is_biz(r["date"])]

    vals = [r["value"] for r in primary]
    n = len(vals)
    if n == 0:
        raise ValueError("No business-day records found in primary window.")

    vals_arr = np.array(vals)
    mean_val = float(np.mean(vals_arr))
    std_val = float(np.std(vals_arr, ddof=1)) if n > 1 else 0.0

    # ANOVA by weekday using scipy
    weekday_vals = defaultdict(list)
    for r in primary:
        weekday_vals[r["date"].strftime("%A")].append(r["value"])
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    day_means = {}
    anova_groups = []
    for d in days:
        if d in weekday_vals:
            day_means[d] = float(np.mean(weekday_vals[d]))
            anova_groups.append(weekday_vals[d])

    if len(anova_groups) >= 2:
        f_stat, anova_p = stats.f_oneway(*anova_groups)
        f_stat = float(f_stat)
        anova_p = clamp_pvalue(anova_p)
    else:
        f_stat, anova_p = 0.0, 1.0

    # I-MR control chart
    imr_vals = [r["value"] for r in imr]
    mr = [abs(imr_vals[i] - imr_vals[i - 1]) for i in range(1, len(imr_vals))]
    mr_bar = float(np.mean(mr)) if mr else 0.0
    cl = float(np.mean(imr_vals))
    ucl = cl + 2.66 * mr_bar
    lcl = cl - 2.66 * mr_bar
    mr_ucl = 3.267 * mr_bar

    # Linear regression using scipy
    x = np.arange(n)
    y = vals_arr
    slope, intercept, r_value, reg_p, std_err = stats.linregress(x, y)
    slope = float(slope)
    intercept = float(intercept)
    r_value = float(r_value)
    reg_p = clamp_pvalue(reg_p)
    r2 = float(r_value ** 2)

    # t-test vs target using scipy
    t_stat, t_p = stats.ttest_1samp(vals_arr, args.target)
    t_stat = float(t_stat)
    t_p = clamp_pvalue(t_p)

    # 95% CI using t-distribution
    se_mean = std_val / np.sqrt(n) if n > 0 else 0.0
    ci_low, ci_high = stats.t.interval(0.95, df=n - 1, loc=mean_val, scale=se_mean)
    ci_low = float(ci_low)
    ci_high = float(ci_high)

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
            "weekday_means": day_means,
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