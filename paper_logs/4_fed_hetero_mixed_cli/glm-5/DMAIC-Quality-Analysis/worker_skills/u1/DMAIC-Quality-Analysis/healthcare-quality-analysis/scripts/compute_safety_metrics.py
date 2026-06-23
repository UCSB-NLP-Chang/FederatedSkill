#!/usr/bin/env python3
"""
Computes healthcare quality metrics from Excel/CSV data.
Requires: pandas, numpy, scipy, openpyxl (for Excel)
"""
import argparse
import json
import math
import sys

import numpy as np
import pandas as pd
from scipy import stats

def compute_trend(x, y):
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    t_stat = slope / std_err if std_err != 0 else 0.0
    return round(slope, 6), round(t_stat, 4)

def wilson_ci(successes, trials, z=1.96):
    if trials == 0:
        return 0.0, 0.0
    p = successes / trials
    denom = 1 + z**2 / trials
    center = (p + z**2 / (2 * trials)) / denom
    spread = (z * math.sqrt((p * (1 - p) + z**2 / (4 * trials)) / trials)) / denom
    return round((center - spread) * 100, 4), round((center + spread) * 100, 4)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True)
    p.add_argument('--wait-col', required=True)
    p.add_argument('--med-err-col', required=True)
    p.add_argument('--med-denom-col', required=True)
    p.add_argument('--readm-col', required=True)
    p.add_argument('--target-rate', type=float, default=2.0)
    p.add_argument('--output-json', default='report.json')
    p.add_argument('--output-md', default='brief.md')
    args = p.parse_args()

    if args.input.endswith('.xlsx'):
        df = pd.read_excel(args.input)
    else:
        df = pd.read_csv(args.input)

    df = df.dropna(subset=[args.wait_col, args.med_err_col, args.med_denom_col, args.readm_col])
    n = len(df)
    x = np.arange(1, n + 1)

    wt = df[args.wait_col].astype(float)
    wt_mean = wt.mean()
    wt_std = wt.std(ddof=1)
    wt_cv = wt_std / wt_mean
    wt_slope, wt_t = compute_trend(x, wt.values)
    wt_stable = "Stable" if abs(wt_t) < 2.0 else "Unstable"

    med_err = df[args.med_err_col].astype(float)
    med_denom = df[args.med_denom_col].astype(float)
    med_prop = med_err / med_denom
    med_mean_prop = med_prop.mean()
    med_std_prop = med_prop.std(ddof=1)
    med_cv = med_std_prop / med_mean_prop
    total_err = med_err.sum()
    total_denom = med_denom.sum()
    overall_rate = (total_err / total_denom) * 100
    wilson_low, wilson_high = wilson_ci(total_err, total_denom)
    med_slope, med_t = compute_trend(x, med_prop.values)
    med_stable = "Stable" if abs(med_t) < 2.0 else "Unstable"
    med_capable = "Capable" if overall_rate <= args.target_rate else "Not Capable"

    rr = df[args.readm_col].astype(float)
    rr_mean = rr.mean()
    rr_std = rr.std(ddof=1)
    rr_cv = rr_std / rr_mean
    rr_slope, rr_t = compute_trend(x, rr.values)
    rr_stable = "Stable" if abs(rr_t) < 2.0 else "Unstable"

    processes = [
        ("Wait Times", wt_cv),
        ("Medication Errors", med_cv),
        ("Readmission Rates", rr_cv)
    ]
    processes.sort(key=lambda p: p[1], reverse=True)
    ranking = [{"process": p[0], "cv": round(p[1], 4)} for p in processes]
    highest_var = processes[0][0]
    risk_stmt = f"{highest_var} is the highest-risk department."

    out = {
        "wait_times": {
            "mean_minutes": round(wt_mean, 4),
            "sample_std_minutes": round(wt_std, 4),
            "cv": round(wt_cv, 4),
            "trend_slope": wt_slope,
            "trend_t_stat": wt_t,
            "stability": wt_stable
        },
        "medication_errors": {
            "mean_proportion": round(med_mean_prop, 6),
            "sample_std_proportion": round(med_std_prop, 6),
            "cv": round(med_cv, 4),
            "overall_rate_pct": round(overall_rate, 4),
            "wilson_ci_lower_pct": wilson_low,
            "wilson_ci_upper_pct": wilson_high,
            "trend_slope": med_slope,
            "trend_t_stat": med_t,
            "stability": med_stable,
            "uses_varying_denominators": True,
            "target_rate_pct": args.target_rate,
            "capability_vs_target": med_capable
        },
        "readmission_rates": {
            "mean_rate": round(rr_mean, 4),
            "sample_std_rate": round(rr_std, 4),
            "cv": round(rr_cv, 4),
            "trend_slope": rr_slope,
            "trend_t_stat": rr_t,
            "stability": rr_stable
        },
        "variability_ranking": ranking,
        "highest_variability_process": highest_var,
        "highest_risk_statement": risk_stmt,
        "extended_analysis": {
            "wait_times": {
                "data_points": n,
                "min_value": round(wt.min(), 4),
                "max_value": round(wt.max(), 4),
                "range": round(wt.max() - wt.min(), 4)
            },
            "medication_errors": {
                "total_errors": int(total_err),
                "total_prescriptions_filled": int(total_denom),
                "data_points": n,
                "min_proportion": round(med_prop.min(), 6),
                "max_proportion": round(med_prop.max(), 6)
            },
            "readmission_rates": {
                "data_points": n,
                "min_value": round(rr.min(), 4),
                "max_value": round(rr.max(), 4),
                "range": round(rr.max() - rr.min(), 4)
            }
        },
        "monitoring_plan": {
            "process_to_be_monitored": highest_var,
            "inputs": ["Monthly counts", "Total denominators", "Department breakdowns", "Risk factors"],
            "outputs": ["Monthly rate (%)", "Trend analysis", "Variability assessment (CV)", "Stability classification"],
            "key_performance_indicators": ["Rate (%)", "Coefficient of Variation (CV)", "Trend slope & significance", "Confidence interval bounds"],
            "frequency_of_monitoring": "Monthly",
            "observation_format": "Tabular data collection with department-level aggregation",
            "roles": ["Quality Improvement Manager", "Department Heads", "Data Analyst", "Chief Medical Officer"],
            "reporting_format": "Monthly dashboard report with trend charts and statistical summaries",
            "corrective_action_process": "PDCA cycle (Plan-Do-Check-Act) with root cause analysis for out-of-control points",
            "benchmarks": {
                "target_readmission_rate_pct": round(rr_mean, 6),
                "max_acceptable_cv": 0.15,
                "stability_threshold_t_stat": 2.0
            },
            "prioritized_actions": [
                {"priority": 1, "action": f"Investigate root causes of high {highest_var} variability", "owner": "Quality Improvement Manager", "timeline": "30 days"},
                {"priority": 2, "action": "Implement protocol review and staff training", "owner": "Department Heads", "timeline": "45 days"},
                {"priority": 3, "action": "Establish real-time tracking dashboard", "owner": "Data Analyst", "timeline": "60 days"}
            ]
        }
    }

    with open(args.output_json, 'w') as f:
        json.dump(out, f, indent=2)

    brief = f"""# [Hospital Name] — Patient Safety Brief

## Summary of Findings

This report presents a deterministic performance and risk assessment based on three key patient safety metrics.

### Wait Times
- **Mean Wait Time:** {round(wt_mean, 2)} minutes
- **Sample Std Dev:** {round(wt_std, 2)} minutes
- **Coefficient of Variation (CV):** {round(wt_cv, 4)}
- **Trend:** {wt_stable} (slope = {wt_slope}, t-stat = {wt_t})

### Medication Errors
- **Mean Proportion (Errors / Prescriptions Filled):** {round(med_mean_prop, 6)}
- **Overall Error Rate:** {round(overall_rate, 4)}%
- **Wilson 95% CI:** [{wilson_low}%, {wilson_high}%]
- **Target Rate:** {args.target_rate}%
- **Capability:** {med_capable}
- **Trend:** {med_stable} (slope = {med_slope}, t-stat = {med_t})
- **Varying Denominators:** Yes

### Readmission Rates
- **Mean Readmission Rate:** {round(rr_mean, 4)}
- **Sample Std Dev:** {round(rr_std, 4)}
- **Coefficient of Variation (CV):** {round(rr_cv, 4)}
- **Trend:** {rr_stable} (slope = {rr_slope}, t-stat = {rr_t})

### Variability Ranking (Highest to Lowest CV)
| Rank | Process | CV |
|------|---------|----|
| 1 | {ranking[0]['process']} | {ranking[0]['cv']} |
| 2 | {ranking[1]['process']} | {ranking[1]['cv']} |
| 3 | {ranking[2]['process']} | {ranking[2]['cv']} |

## Most Significant Risks

{risk_stmt}

The variability ranking shows **{highest_var}** has the highest coefficient of variation ({round(processes[0][1], 4)}), indicating the greatest relative variability in performance.

Key risk indicators:
- Wait times process is {wt_stable.lower()}, with a trend slope of {wt_slope}
- Medication errors process is {med_stable.lower()}, with overall rate at {round(overall_rate, 4)}% (target: {args.target_rate}%)
- Readmission rates process is **{rr_stable.lower()}**, with CV of {round(rr_cv, 4)}

## Prioritized Corrective Actions

| Priority | Action | Owner | Timeline |
|----------|--------|-------|----------|
| 1 | Investigate root causes of high {highest_var} variability | Quality Improvement Manager | 30 days |
| 2 | Implement protocol review and staff training | Department Heads | 45 days |
| 3 | Establish real-time tracking dashboard | Data Analyst | 60 days |

## Monitoring Plan

### Process to be Monitored

{highest_var}

### Inputs

- Monthly counts
- Total denominators
- Department breakdowns
- Risk factors

### Outputs

- Monthly rate (%)
- Trend analysis
- Variability assessment (CV)
- Stability classification

### Key Performance Indicators (KPIs)

- Rate (%)
- Coefficient of Variation (CV)
- Trend slope & significance
- Confidence interval bounds

### Frequency of Monitoring

Monthly

### Observation Format

Tabular data collection with department-level aggregation

### Roles

- Quality Improvement Manager
- Department Heads
- Data Analyst
- Chief Medical Officer

### Reporting Format

Monthly dashboard report with trend charts and statistical summaries

### Corrective Action Process

PDCA cycle (Plan-Do-Check-Act) with root cause analysis for out-of-control points

### Benchmarks

- **target_readmission_rate_pct:** {round(rr_mean, 6)}
- **max_acceptable_cv:** 0.15
- **stability_threshold_t_stat:** 2.0

---

*Report generated for [Hospital Name]. All metrics computed using sample standard deviation (ddof=1) and standard trend analysis.*
"""
    with open(args.output_md, 'w') as f:
        f.write(brief)
    print(f"Report written to {args.output_json}")
    print(f"Brief written to {args.output_md}")

if __name__ == '__main__':
    main()