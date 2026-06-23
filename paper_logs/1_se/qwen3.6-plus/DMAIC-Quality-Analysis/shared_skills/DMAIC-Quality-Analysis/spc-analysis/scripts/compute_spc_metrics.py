#!/usr/bin/env python3
"""
Deterministic SPC calculator for time-series CSV or Excel data.
Outputs JSON to stdout matching references/output_schema.md.
Usage: python3 compute_spc_metrics.py <data_path> <target_value> [metric_column]
"""
import json
import sys
import math
from collections import defaultdict
import pandas as pd
from scipy import stats

def main():
    if len(sys.argv) < 3:
        print("Usage: compute_spc_metrics.py <data_path> <target_value> [metric_column]", file=sys.stderr)
        sys.exit(1)
        
    data_path = sys.argv[1]
    target = float(sys.argv[2])
    metric_col = sys.argv[3] if len(sys.argv) > 3 else None
    
    # Load data (supports .csv and .xlsx)
    if data_path.lower().endswith('.csv'):
        df = pd.read_csv(data_path)
    else:
        df = pd.read_excel(data_path)
        
    # Normalize column names (strip whitespace)
    df.columns = df.columns.str.strip()
    
    if "Date" not in df.columns:
        raise ValueError("Data file must contain a 'Date' column.")
        
    if metric_col is None:
        # Auto-detect metric column: first numeric column that isn't Date or Stage
        for col in df.columns:
            if col.lower() not in ("date", "stage", "day") and pd.api.types.is_numeric_dtype(df[col]):
                metric_col = col
                break
    if metric_col is None:
        raise ValueError("Could not detect metric column. Provide it explicitly.")
        
    df["Date"] = pd.to_datetime(df["Date"])
    total_rows = len(df)
    
    # Filter business days
    biz_df = df[df["Date"].dt.weekday < 5].copy()
    biz_df = biz_df.sort_values("Date").reset_index(drop=True)
    
    if len(biz_df) == 0:
        raise ValueError("No business day rows found.")
        
    values = biz_df[metric_col].astype(float).tolist()
    n = len(values)
    mean_val = sum(values) / n
    std_val = (sum((v - mean_val)**2 for v in values) / (n - 1))**0.5
    
    # Baseline calculation
    baseline_vals = []
    if "Stage" in df.columns:
        baseline_mask = df["Stage"].astype(str).str.strip().str.lower() == "baseline"
        baseline_df = df[baseline_mask & (df["Date"].dt.weekday < 5)]
        if len(baseline_df) > 0:
            baseline_vals = baseline_df[metric_col].astype(float).tolist()
    baseline_val = sum(baseline_vals)/len(baseline_vals) if baseline_vals else 0.0
    
    # ANOVA by weekday
    weekday_vals = defaultdict(list)
    for _, row in biz_df.iterrows():
        day_name = row["Date"].strftime("%A")
        weekday_vals[day_name].append(row[metric_col])
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    groups = [weekday_vals[d] for d in days if d in weekday_vals]
    f_stat, anova_p = stats.f_oneway(*groups)
    day_means = {d: sum(weekday_vals[d])/len(weekday_vals[d]) for d in weekday_vals}
    highest = max(day_means, key=day_means.get)
    lowest = min(day_means, key=day_means.get)
    df_between = len(groups) - 1
    df_within = n - len(groups)
    
    # I-MR Chart
    mr = [abs(values[i] - values[i-1]) for i in range(1, n)]
    mr_bar = sum(mr) / len(mr)
    cl = mean_val
    ucl = cl + 2.66 * mr_bar
    lcl = cl - 2.66 * mr_bar
    mr_ucl = 3.267 * mr_bar
    
    # Regression
    x = list(range(1, n + 1))
    slope, intercept, r_val, p_reg, _ = stats.linregress(x, values)
    
    # t-test vs target
    t_stat, p_ttest = stats.ttest_1samp(values, target)
    ci_low = mean_val - 1.96 * (std_val / math.sqrt(n))
    ci_high = mean_val + 1.96 * (std_val / math.sqrt(n))
    
    # Cpk (lower)
    cpk_lower = (mean_val - target) / (3 * std_val)
    
    result = {
        "source_file": data_path,
        "filters": {
            "date_range_primary": {"start": biz_df["Date"].iloc[0].strftime("%Y-%m-%d"), "end": biz_df["Date"].iloc[-1].strftime("%Y-%m-%d")},
            "date_range_imr": {"start": biz_df["Date"].iloc[0].strftime("%Y-%m-%d"), "end": biz_df["Date"].iloc[-1].strftime("%Y-%m-%d")},
            "business_days_only": True,
            "response_metric": metric_col
        },
        "record_counts": {
            "total_rows_in_file": total_rows,
            "primary_window_all_days": total_rows,
            "primary_window_business_days": n,
            "imr_window_business_days": n
        },
        "charter_metrics": {
            "baseline_value": round(baseline_val, 4),
            "target_value": target,
            "current_mean_value": round(mean_val, 4)
        },
        "anova_by_weekday": {
            "weekday_means": {k: round(v, 4) for k, v in day_means.items()},
            "p_value": round(anova_p, 6),
            "highest_mean_day": highest,
            "lowest_mean_day": lowest,
            "f_statistic": round(f_stat, 4),
            "df_between": df_between,
            "df_within": df_within
        },
        "imr_summary": {
            "points": n,
            "center_line": round(cl, 4),
            "ucl": round(ucl, 4),
            "lcl": round(lcl, 4),
            "mr_bar": round(mr_bar, 4),
            "mr_ucl": round(mr_ucl, 4)
        },
        "regression_day_index": {
            "slope": round(slope, 6),
            "intercept": round(intercept, 4),
            "r_value": round(r_val, 6),
            "p_value": float(f"{p_reg:.2e}") if p_reg < 0.0001 else round(p_reg, 6),
            "n": n
        },
        "ttest_vs_target": {
            "n": n,
            "mean_value": round(mean_val, 4),
            "t_stat": round(t_stat, 4),
            "p_value": float(f"{p_ttest:.2e}") if p_ttest < 0.0001 else round(p_ttest, 6),
            "ci95_low": round(ci_low, 4),
            "ci95_high": round(ci_high, 4),
            "decision": "reject_h0" if p_ttest < 0.05 else "fail_to_reject_h0"
        },
        "capability_against_lsl": {
            "lsl": target,
            "std_dev_sample": round(std_val, 4),
            "cpk_lower": round(cpk_lower, 4)
        }
    }
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
