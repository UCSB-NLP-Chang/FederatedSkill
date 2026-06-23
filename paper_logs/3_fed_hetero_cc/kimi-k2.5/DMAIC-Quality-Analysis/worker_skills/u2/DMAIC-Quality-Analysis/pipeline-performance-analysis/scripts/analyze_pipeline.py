#!/usr/bin/env python3
"""Analyze pipeline performance metrics from multi-sheet Excel file.

Usage:
    python3 analyze_pipeline.py <excel_path> [--output stats.json]
    python3 analyze_pipeline.py --validate stats.json

Pure numpy implementation - no scipy dependency.
"""
import sys
import json
import math
import pandas as pd
import numpy as np

Z_95 = 1.959963984540054


def wilson_ci(successes, trials, confidence=0.95):
    """Wilson score confidence interval for proportions. Returns (lower, upper) as floats in [0,1]."""
    if trials == 0:
        return 0.0, 1.0
    z = Z_95
    p = successes / trials
    denom = 1 + z**2 / trials
    center = (p + z**2 / (2 * trials)) / denom
    margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * trials)) / trials) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def compute_trend(series):
    """Compute slope, t-statistic, and stability for time series."""
    n = len(series)
    if n < 2:
        return 0.0, 0.0, "Insufficient data"
    x = np.arange(n)
    y = np.asarray(series)
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    slope = np.sum((x - x_mean) * (y - y_mean)) / np.sum((x - x_mean)**2)
    y_pred = slope * x + (y_mean - slope * x_mean)
    residuals = y - y_pred
    sse = np.sum(residuals**2)
    mse = sse / (n - 2) if n > 2 else 0
    se_slope = np.sqrt(mse / np.sum((x - x_mean)**2)) if np.sum((x - x_mean)**2) > 0 else 0
    t_stat = slope / se_slope if se_slope > 0 else 0.0
    stability = "Stable" if abs(t_stat) < 2.0 else "Unstable"
    return float(slope), float(t_stat), stability


def analyze_metric(series):
    """Compute basic stats for a metric series."""
    mean = float(np.mean(series))
    std = float(np.std(series, ddof=1)) if len(series) > 1 else 0.0
    cv = std / mean if mean != 0 else 0.0
    slope, t_stat, stability = compute_trend(series)
    return {
        "mean": mean,
        "sample_std": std,
        "cv": cv,
        "trend_slope": slope,
        "t_statistic": t_stat,
        "stability": stability
    }


def analyze_bug_rate(df, bugs_col="Bugs Found", lines_col="Lines Reviewed"):
    """Analyze bug rate with Wilson CI for varying denominators."""
    bugs = df[bugs_col].values
    lines = df[lines_col].values
    total_bugs = int(np.sum(bugs))
    total_lines = int(np.sum(lines))
    if total_lines == 0:
        return {"error": "No lines data"}
    overall_rate = total_bugs / total_lines
    ci_lower, ci_upper = wilson_ci(total_bugs, total_lines)
    proportions = bugs / lines
    mean_prop = float(np.mean(proportions))
    std_prop = float(np.std(proportions, ddof=1)) if len(proportions) > 1 else 0.0
    cv = std_prop / mean_prop if mean_prop > 0 else 0.0
    slope, t_stat, stability = compute_trend(proportions)
    return {
        "total_bugs": total_bugs,
        "total_lines": total_lines,
        "overall_rate_pct": overall_rate * 100,
        "wilson_ci_95": [ci_lower * 100, ci_upper * 100],
        "cv": cv,
        "trend_slope": slope,
        "t_statistic": t_stat,
        "stability": stability,
        "uses_varying_denominators": bool(not np.all(lines == lines[0]))
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_pipeline.py <excel_path> [--output stats.json]")
        print("       python3 analyze_pipeline.py --validate stats.json")
        sys.exit(1)

    if sys.argv[1] == "--validate" and len(sys.argv) >= 3:
        json_path = sys.argv[2]
        with open(json_path) as f:
            data = json.load(f)
        required = ["build_duration", "bug_rate", "deployment_failures", "variability_ranking"]
        missing = [k for k in required if k not in data]
        if missing:
            print(f"MISSING KEYS: {missing}")
            sys.exit(1)
        print("VALID")
        sys.exit(0)

    excel_path = sys.argv[1]
    xls = pd.ExcelFile(excel_path)
    results = {}

    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        if sheet == "bug_rate":
            results[sheet] = analyze_bug_rate(df)
        else:
            numeric_cols = df.select_dtypes(include='number').columns
            if len(numeric_cols) == 0:
                continue
            metric_col = numeric_cols[0]
            series = df[metric_col].dropna().values
            results[sheet] = analyze_metric(series)

    ranking = sorted(results.items(), key=lambda x: x[1].get("cv", 0), reverse=True)
    results["variability_ranking"] = [{"process": k, "cv": v.get("cv", 0)} for k, v in ranking]
    results["highest_variability_process"] = ranking[0][0] if ranking else None

    output = json.dumps(results, indent=2)
    print(output)

    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            with open(sys.argv[idx + 1], "w") as f:
                f.write(output)


if __name__ == "__main__":
    main()
