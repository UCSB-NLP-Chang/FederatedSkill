#!/usr/bin/env python3
"""
Computes healthcare process variability metrics from multi-sheet Excel data.
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
from datetime import datetime
import numpy as np
import pandas as pd
from scipy import stats


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True, help='Excel file path')
    p.add_argument('--output-json', default='report.json')
    p.add_argument('--output-md', default='brief.md')
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
    """Linear regression trend analysis. Returns dict with slope, t_stat, p_value, etc."""
    n = len(x)
    slope, intercept, r_val, p_val, std_err = stats.linregress(x, y)
    t_stat = slope / std_err if std_err != 0 else 0.0
    stability = "Stable" if p_val >= 0.05 else "Unstable"
    return {
        "slope": float(slope),
        "intercept": float(intercept),
        "t_statistic": float(t_stat),
        "p_value": float(p_val) if p_val >= 1e-10 else 1e-15,
        "r_squared": float(r_val**2),
        "stability": stability,
        "n_observations": n
    }


def analyze_wait_times(df):
    """Analyze wait times time series."""
    values = df.iloc[:, 1].astype(float).values
    mean_val = float(np.mean(values))
    std_val = float(np.std(values, ddof=1))
    cv = std_val / mean_val if mean_val != 0 else 0.0

    x = np.arange(1, len(values) + 1)
    trend = compute_trend(x, values)

    return {
        "mean": mean_val,
        "sample_std": std_val,
        "cv": cv,
        "n": len(values),
        "trend": trend,
        "values": values.tolist()
    }


def analyze_medication_errors(df, target_rate_pct=2.0):
    """Analyze medication errors with varying denominators."""
    prescriptions = df.iloc[:, 1].astype(float).values
    errors = df.iloc[:, 2].astype(float).values

    total_errors = int(np.sum(errors))
    total_prescriptions = int(np.sum(prescriptions))
    overall_rate = total_errors / total_prescriptions if total_prescriptions > 0 else 0.0
    overall_rate_pct = overall_rate * 100

    proportions = errors / prescriptions
    mean_prop = float(np.mean(proportions))
    std_prop = float(np.std(proportions, ddof=1))
    cv = std_prop / mean_prop if mean_prop != 0 else 0.0

    ci_low, ci_high = wilson_interval(total_errors, total_prescriptions)

    x = np.arange(1, len(proportions) + 1)
    trend = compute_trend(x, proportions)

    capability = "Capable" if overall_rate_pct < target_rate_pct else "Not Capable"

    return {
        "total_errors": total_errors,
        "total_prescriptions_filled": total_prescriptions,
        "overall_rate_percent": float(overall_rate_pct),
        "wilson_95_ci": {
            "lower": float(ci_low * 100),
            "upper": float(ci_high * 100)
        },
        "mean_of_per_point_proportions": float(mean_prop),
        "sample_std_of_per_point_proportions": float(std_prop),
        "cv": float(cv),
        "uses_varying_denominators": True,
        "target_rate_pct": float(target_rate_pct),
        "capability_vs_target": capability,
        "trend": trend,
        "proportions": proportions.tolist()
    }


def analyze_readmission_rates(df):
    """Analyze readmission rates time series."""
    values = df.iloc[:, 1].astype(float).values
    mean_val = float(np.mean(values))
    std_val = float(np.std(values, ddof=1))
    cv = std_val / mean_val if mean_val != 0 else 0.0

    x = np.arange(1, len(values) + 1)
    trend = compute_trend(x, values)

    return {
        "mean": mean_val,
        "sample_std": std_val,
        "cv": cv,
        "n": len(values),
        "trend": trend,
        "values": values.tolist()
    }


def generate_monitoring_plan(highest_process):
    """Generate monitoring plan structure."""
    return {
        "process_to_be_monitored": highest_process,
        "inputs": ["Daily operational data", "Incident reports", "Staffing levels"],
        "outputs": ["Daily metric report", "Trend analysis", "Alert notifications"],
        "key_performance_indicators": ["Coefficient of Variation", "Trend stability", "Mean performance"],
        "frequency_of_monitoring": "Daily",
        "observation_format": "Time-series data collection with business day alignment",
        "roles": {
            "data_collector": "Department Manager",
            "analyst": "Quality Improvement Specialist",
            "reviewer": "Clinical Director"
        },
        "reporting_format": "Weekly dashboard with statistical process control charts",
        "corrective_action_process": "Trigger review if trend p-value < 0.05 or CV increases >10%",
        "benchmarks": {
            "wait_times": "< 45 minutes average",
            "medication_errors": "< 2.0% error rate",
            "readmission_rates": "< 10% rate"
        },
        "prioritized_actions": [
            "Implement daily huddles for highest variability process",
            "Review and standardize high-variation procedures",
            "Enhance data collection accuracy",
            "Staff training on process standardization"
        ],
        "checklist": [
            "Data collection completeness verified",
            "Statistical calculations validated",
            "Trend direction confirmed over minimum 20 data points",
            "Outlier investigation completed",
            "Stakeholder notification sent",
            "Corrective action plan documented",
            "Follow-up date scheduled",
            "Responsibility assignments confirmed"
        ]
    }


def main():
    args = parse_args()

    xl = pd.ExcelFile(args.input)

    results = {}
    for sheet in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sheet)
        sheet_lower = sheet.lower().replace(' ', '_')

        if 'wait' in sheet_lower:
            results['wait_times'] = analyze_wait_times(df)
        elif 'medication' in sheet_lower or 'error' in sheet_lower:
            results['medication_errors'] = analyze_medication_errors(df)
        elif 'readmission' in sheet_lower:
            results['readmission_rates'] = analyze_readmission_rates(df)

    ranking = []
    for process, data in results.items():
        ranking.append({
            "process": process.replace('_', ' ').title().replace('Cv', 'CV'),
            "cv": data["cv"]
        })

    ranking.sort(key=lambda x: x["cv"], reverse=True)
    for i, item in enumerate(ranking, 1):
        item["rank"] = i

    highest_process = ranking[0]["process"] if ranking else "Unknown"

    output = {
        "wait_times": {
            "mean": results["wait_times"]["mean"],
            "sample_std": results["wait_times"]["sample_std"],
            "cv": results["wait_times"]["cv"],
            "n": results["wait_times"]["n"],
            "trend": results["wait_times"]["trend"]
        },
        "medication_errors": {
            "total_errors": results["medication_errors"]["total_errors"],
            "total_prescriptions_filled": results["medication_errors"]["total_prescriptions_filled"],
            "overall_rate_percent": results["medication_errors"]["overall_rate_percent"],
            "wilson_95_ci": results["medication_errors"]["wilson_95_ci"],
            "mean_of_per_point_proportions": results["medication_errors"]["mean_of_per_point_proportions"],
            "sample_std_of_per_point_proportions": results["medication_errors"]["sample_std_of_per_point_proportions"],
            "cv": results["medication_errors"]["cv"],
            "uses_varying_denominators": results["medication_errors"]["uses_varying_denominators"],
            "target_rate_pct": results["medication_errors"]["target_rate_pct"],
            "capability_vs_target": results["medication_errors"]["capability_vs_target"],
            "trend": results["medication_errors"]["trend"]
        },
        "readmission_rates": {
            "mean": results["readmission_rates"]["mean"],
            "sample_std": results["readmission_rates"]["sample_std"],
            "cv": results["readmission_rates"]["cv"],
            "n": results["readmission_rates"]["n"],
            "trend": results["readmission_rates"]["trend"]
        },
        "variability_ranking": ranking,
        "highest_variability_process": highest_process,
        "highest_risk_statement": f"{highest_process} is the highest-risk department.",
        "monitoring_plan": generate_monitoring_plan(highest_process),
        "extended_analysis": {
            "wait_times_per_point": results["wait_times"]["values"],
            "medication_errors_per_point_proportions": results["medication_errors"]["proportions"],
            "readmission_rates_per_point": results["readmission_rates"]["values"]
        }
    }

    with open(args.output_json, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"JSON report written to {args.output_json}")
    print(f"Highest variability process: {highest_process} (CV={ranking[0]['cv']:.4f})")


if __name__ == '__main__':
    main()
