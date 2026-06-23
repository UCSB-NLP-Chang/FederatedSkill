#!/usr/bin/env python3
"""
Computes healthcare quality metrics from multi-sheet Excel data.
Analyzes Wait Times, Medication Errors, and Readmission Rates.

Usage:
  python3 compute_healthcare_metrics.py \
    --input hospital_data.xlsx \
    --output-json report.json \
    --output-md brief.md

Requires: pandas, numpy, scipy, openpyxl
"""
import argparse
import json
import math
import sys

import numpy as np
import pandas as pd
from scipy import stats


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True, help='Excel file path')
    p.add_argument('--output-json', default='report.json')
    p.add_argument('--output-md', default='brief.md')
    p.add_argument('--target-rate', type=float, default=2.0,
                   help='Target error rate percentage (default 2.0)')
    return p.parse_args()


def wilson_interval(successes, trials, confidence=0.95):
    """Wilson score interval for binomial proportion."""
    if trials == 0:
        return (0.0, 0.0)
    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    p = successes / trials
    denom = 1 + z**2 / trials
    centre = (p + z**2 / (2 * trials)) / denom
    half_width = z * math.sqrt((p * (1 - p) + z**2 / (4 * trials)) / trials) / denom
    return (centre - half_width, centre + half_width)


def compute_trend(x, y):
    """Linear regression trend analysis.

    Returns tuple: (slope, t_stat, p_value, stability)
    stability: "Stable" if |t_stat| < 2.0, else "Unstable"
    """
    if len(x) < 2:
        return (0.0, 0.0, 1.0, "Stable")
    slope, intercept, r_val, p_val, std_err = stats.linregress(x, y)
    t_stat = slope / std_err if std_err != 0 else 0.0
    # Prevent p-value rounding to 0.0
    if p_val < 1e-10:
        p_val = 1e-15
    stability = "Stable" if abs(t_stat) < 2.0 else "Unstable"
    return (slope, t_stat, p_val, stability)


def analyze_wait_times(df):
    """Analyze wait times time series.
    Expects columns: Date, metric values
    """
    # Second column is the metric
    values = df.iloc[:, 1].astype(float).values
    mean_val = float(np.mean(values))
    std_val = float(np.std(values, ddof=1))  # Sample std
    cv = std_val / mean_val if mean_val != 0 else 0.0

    x = np.arange(1, len(values) + 1)
    slope, t_stat, p_val, stability = compute_trend(x, values)

    return {
        "mean_minutes": mean_val,
        "sample_std_minutes": std_val,
        "cv": cv,
        "trend_slope": slope,
        "trend_t_stat": t_stat,
        "trend_p_value": p_val,
        "stability": stability,
        "n": len(values)
    }


def analyze_medication_errors(df, target_rate_pct=2.0):
    """Analyze medication errors with varying denominators.
    Expects columns: Date, Prescriptions Filled, Errors
    """
    prescriptions = df.iloc[:, 1].astype(float).values
    errors = df.iloc[:, 2].astype(float).values

    total_errors = int(np.sum(errors))
    total_prescriptions = int(np.sum(prescriptions))
    overall_rate = total_errors / total_prescriptions if total_prescriptions > 0 else 0.0
    overall_rate_pct = overall_rate * 100

    # Per-point proportions for CV
    proportions = errors / prescriptions
    mean_prop = float(np.mean(proportions))
    std_prop = float(np.std(proportions, ddof=1))
    cv = std_prop / mean_prop if mean_prop != 0 else 0.0

    # Wilson CI for overall rate
    ci_low, ci_high = wilson_interval(total_errors, total_prescriptions)

    # Trend on proportions
    x = np.arange(1, len(proportions) + 1)
    slope, t_stat, p_val, stability = compute_trend(x, proportions)

    capability = "Capable" if overall_rate_pct < target_rate_pct else "Not Capable"

    return {
        "total_errors": total_errors,
        "total_prescriptions_filled": total_prescriptions,
        "overall_rate_pct": overall_rate_pct,
        "wilson_ci_lower_pct": ci_low * 100,
        "wilson_ci_upper_pct": ci_high * 100,
        "mean_proportion": mean_prop,
        "sample_std_proportion": std_prop,
        "cv": cv,
        "trend_slope": slope,
        "trend_t_stat": t_stat,
        "trend_p_value": p_val,
        "stability": stability,
        "uses_varying_denominators": True,
        "target_rate_pct": target_rate_pct,
        "capability_vs_target": capability,
        "n": len(proportions)
    }


def analyze_readmission_rates(df):
    """Analyze readmission rates time series.
    Expects columns: Date, rate values
    """
    values = df.iloc[:, 1].astype(float).values
    mean_val = float(np.mean(values))
    std_val = float(np.std(values, ddof=1))
    cv = std_val / mean_val if mean_val != 0 else 0.0

    x = np.arange(1, len(values) + 1)
    slope, t_stat, p_val, stability = compute_trend(x, values)

    return {
        "mean_rate": mean_val,
        "sample_std_rate": std_val,
        "cv": cv,
        "trend_slope": slope,
        "trend_t_stat": t_stat,
        "trend_p_value": p_val,
        "stability": stability,
        "n": len(values)
    }


def generate_monitoring_plan(highest_process, results):
    """Generate monitoring plan structure."""
    return {
        "process_to_be_monitored": highest_process,
        "inputs": ["Monthly operational data", "Incident reports", "Staffing levels", "Department breakdowns"],
        "outputs": ["Monthly rate (%)", "Trend analysis", "Variability assessment (CV)", "Stability classification"],
        "key_performance_indicators": ["Rate (%)", "Coefficient of Variation (CV)", "Trend slope", "Trend significance"],
        "frequency_of_monitoring": "Monthly",
        "observation_format": "Time-series data collection with business day alignment",
        "roles": ["Quality Improvement Manager", "Department Heads", "Data Analyst", "Chief Medical Officer"],
        "reporting_format": "Monthly dashboard report with trend charts and statistical summaries",
        "corrective_action_process": "PDCA cycle (Plan-Do-Check-Act) with root cause analysis for out-of-control points",
        "benchmarks": {
            "target_rate_pct": results.get("medication_errors", {}).get("target_rate_pct", 2.0),
            "max_acceptable_cv": 0.15,
            "stability_threshold_t_stat": 2.0
        },
        "prioritized_actions": [
            {"priority": 1, "action": f"Investigate root causes of high {highest_process} variability", "owner": "Quality Improvement Manager", "timeline": "30 days"},
            {"priority": 2, "action": "Implement protocol review and staff training", "owner": "Department Heads", "timeline": "45 days"},
            {"priority": 3, "action": "Establish real-time tracking dashboard", "owner": "Data Analyst", "timeline": "60 days"}
        ]
    }


def generate_extended_analysis(wt_results, me_results, rr_results):
    """Generate extended analysis with per-point data."""
    return {
        "wait_times": {
            "n": wt_results.get("n", 0)
        },
        "medication_errors": {
            "total_errors": me_results.get("total_errors", 0),
            "total_prescriptions_filled": me_results.get("total_prescriptions_filled", 0),
            "n": me_results.get("n", 0)
        },
        "readmission_rates": {
            "n": rr_results.get("n", 0)
        }
    }


def generate_brief(results, highest_process):
    """Generate markdown brief."""
    wt = results.get("wait_times", {})
    me = results.get("medication_errors", {})
    rr = results.get("readmission_rates", {})

    brief = f"""# Patient Safety Performance and Risk Assessment

## Summary of Findings

This assessment analyzes patient safety data across three critical operational areas: Wait Times, Medication Errors, and Readmission Rates.

| Process | Mean/Rate | CV | Stability |
|---------|-----------|-----|-----------|
| Wait Times | {wt.get('mean_minutes', 0):.2f} min | {wt.get('cv', 0):.4f} | {wt.get('stability', 'Unknown')} |
| Medication Errors | {me.get('overall_rate_pct', 0):.4f}% | {me.get('cv', 0):.4f} | {me.get('stability', 'Unknown')} |
| Readmission Rates | {rr.get('mean_rate', 0):.4f} | {rr.get('cv', 0):.4f} | {rr.get('stability', 'Unknown')} |

### Variability Ranking (Highest to Lowest CV)

| Rank | Process | CV |
|------|---------|-----|
| 1 | {highest_process} | {max(wt.get('cv', 0), me.get('cv', 0), rr.get('cv', 0)):.4f} |

## Most Significant Risks

{highest_process} is the highest-risk department.

Key risk indicators:
- Wait times: {wt.get('stability', 'Unknown')} trend (slope = {wt.get('trend_slope', 0):.6f})
- Medication errors: {me.get('stability', 'Unknown')} (rate = {me.get('overall_rate_pct', 0):.4f}%, target = {me.get('target_rate_pct', 2.0)}%)
- Readmission rates: {rr.get('stability', 'Unknown')} (CV = {rr.get('cv', 0):.4f})

## Monitoring Plan

Process: {highest_process}
Frequency: Monthly
KPIs: Rate (%), CV, Trend slope

---
*Generated by Healthcare Quality Analysis*
"""
    return brief


def main():
    args = parse_args()

    # Check scipy availability
    try:
        from scipy import stats
    except ImportError:
        print("ERROR: scipy is not available. Install with: pip install scipy", file=sys.stderr)
        sys.exit(1)

    xl = pd.ExcelFile(args.input)

    results = {}

    for sheet in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sheet)
        sheet_lower = sheet.lower()

        if 'wait' in sheet_lower:
            results['wait_times'] = analyze_wait_times(df)
        elif 'medication' in sheet_lower or 'error' in sheet_lower:
            results['medication_errors'] = analyze_medication_errors(df, args.target_rate)
        elif 'readmission' in sheet_lower or 'readmit' in sheet_lower:
            results['readmission_rates'] = analyze_readmission_rates(df)

    # Build variability ranking
    ranking = []
    for process, data in results.items():
        ranking.append({
            "process": process.replace('_', ' ').title(),
            "cv": data.get("cv", 0.0)
        })

    ranking.sort(key=lambda x: x["cv"], reverse=True)
    for i, item in enumerate(ranking, 1):
        item["rank"] = i

    highest_process = ranking[0]["process"] if ranking else "Unknown"

    # Build output
    output = {
        "wait_times": results.get("wait_times", {}),
        "medication_errors": results.get("medication_errors", {}),
        "readmission_rates": results.get("readmission_rates", {}),
        "variability_ranking": ranking,
        "highest_variability_process": highest_process,
        "highest_risk_statement": f"{highest_process} is the highest-risk department.",
        "monitoring_plan": generate_monitoring_plan(highest_process, results),
        "extended_analysis": generate_extended_analysis(
            results.get("wait_times", {}),
            results.get("medication_errors", {}),
            results.get("readmission_rates", {})
        )
    }

    with open(args.output_json, 'w') as f:
        json.dump(output, f, indent=2)

    brief = generate_brief(output, highest_process)
    with open(args.output_md, 'w') as f:
        f.write(brief)

    print(f"JSON report written to {args.output_json}")
    print(f"Brief written to {args.output_md}")
    print(f"Highest variability process: {highest_process} (CV={ranking[0]['cv']:.4f})")


if __name__ == '__main__':
    main()
