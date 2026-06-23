#!/usr/bin/env python3
"""
Computes process capability metrics from multi-sheet Excel data.
Analyzes Task Duration, Failure Rate, and System Errors.

Usage:
  python3 compute_capability_metrics.py \
    --input process_capability_data.xlsx \
    --output-json report.json \
    --output-md brief.md \
    --project-name "Your Project Name" \
    --target-rate 1.0

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
    p.add_argument('--project-name', default='Process Capability',
                   help='Project codename for monitoring plan (derive from task context)')
    p.add_argument('--target-rate', type=float, default=1.0,
                   help='Target failure rate percentage (default 1.0)')
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


def analyze_task_duration(df):
    """Analyze task duration time series.
    Expects columns: Date/Index, Duration values (minutes)
    """
    values = df.iloc[:, 1].astype(float).values
    mean_val = float(np.mean(values))
    std_val = float(np.std(values, ddof=1))  # Sample std
    cv = std_val / mean_val if mean_val != 0 else 0.0

    x = np.arange(1, len(values) + 1)
    slope, t_stat, p_val, stability = compute_trend(x, values)

    return {
        "mean_min": mean_val,
        "sample_std_min": std_val,
        "cv": cv,
        "trend_slope": slope,
        "trend_t_stat": t_stat,
        "trend_p_value": p_val,
        "stability": stability,
        "n": len(values)
    }


def analyze_failure_rate(df, target_rate_pct=1.0):
    """Analyze failure rate with varying denominators.
    Expects columns: Date/Index, Units processed, Failures
    """
    units = df.iloc[:, 1].astype(float).values
    failures = df.iloc[:, 2].astype(float).values

    total_failures = int(np.sum(failures))
    total_units = int(np.sum(units))
    overall_rate = total_failures / total_units if total_units > 0 else 0.0
    overall_rate_pct = overall_rate * 100

    # Per-point proportions for CV
    proportions = failures / units
    mean_prop = float(np.mean(proportions))
    std_prop = float(np.std(proportions, ddof=1))
    cv = std_prop / mean_prop if mean_prop != 0 else 0.0

    # Wilson CI for overall rate
    ci_low, ci_high = wilson_interval(total_failures, total_units)

    # Trend on proportions
    x = np.arange(1, len(proportions) + 1)
    slope, t_stat, p_val, stability = compute_trend(x, proportions)

    capability = "Capable" if overall_rate_pct <= target_rate_pct else "Not Capable"

    return {
        "total_failures": total_failures,
        "total_units_processed": total_units,
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


def analyze_system_errors(df):
    """Analyze system errors time series.
    Expects columns: Date/Index, Error Rate values
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


def generate_monitoring_plan(highest_process, results, project_name):
    """Generate monitoring plan structure with checklist and momentum plan."""
    return {
        "process_to_be_monitored": highest_process,
        "inputs": ["Daily operational data", "Error logs", "Process metrics", "System performance indicators"],
        "outputs": ["Daily rate (%)", "Trend analysis", "Variability assessment (CV)", "Stability classification"],
        "key_performance_indicators": ["Rate (%)", "Coefficient of Variation (CV)", "Trend slope", "Trend significance"],
        "frequency_of_monitoring": "Daily",
        "observation_format": "Time-series data collection with continuous monitoring",
        "roles": ["Process Owner", "Quality Engineer", "Data Analyst", "Operations Manager"],
        "reporting_format": "Daily dashboard report with trend charts and statistical summaries",
        "corrective_action_process": "PDCA cycle (Plan-Do-Check-Act) with root cause analysis for out-of-control points",
        "benchmarks": {
            "target_rate_pct": results.get("failure_rate", {}).get("target_rate_pct", 1.0),
            "max_acceptable_cv": 0.15,
            "stability_threshold_t_stat": 2.0
        },
        "prioritized_actions": [
            {"priority": 1, "action": f"Investigate root causes of high {highest_process} variability", "owner": "Process Owner", "timeline": "30 days"},
            {"priority": 2, "action": "Implement process controls and monitoring", "owner": "Quality Engineer", "timeline": "45 days"},
            {"priority": 3, "action": "Establish continuous improvement feedback loop", "owner": "Operations Manager", "timeline": "60 days"}
        ],
        "checklist": [
            "Verify data collection completeness and accuracy",
            "Review trend stability and control chart signals",
            "Assess capability against target thresholds",
            "Document root causes for any out-of-control points",
            "Validate corrective action effectiveness",
            "Update monitoring parameters if process changes",
            "Review and adjust benchmarks quarterly"
        ],
        "momentum_plan_30_60_90": {
            "30_days": "Baseline stabilization and root cause identification",
            "60_days": "Process control implementation and automation",
            "90_days": "Continuous improvement and capability expansion"
        },
        "project_codename": project_name
    }


def generate_extended_analysis(td_results, fr_results, se_results):
    """Generate extended analysis with per-process counts."""
    return {
        "task_duration": {"n": td_results.get("n", 0)},
        "failure_rate": {
            "total_failures": fr_results.get("total_failures", 0),
            "total_units_processed": fr_results.get("total_units_processed", 0),
            "n": fr_results.get("n", 0)
        },
        "system_errors": {"n": se_results.get("n", 0)}
    }


def generate_brief(results, highest_process, project_name):
    """Generate markdown brief with parameterized project name."""
    td = results.get("task_duration", {})
    fr = results.get("failure_rate", {})
    se = results.get("system_errors", {})

    brief = f"""# {project_name} — Process Capability Brief

## Summary of Findings

This assessment analyzes process capability across three critical areas: Task Duration, Failure Rate, and System Errors.

| Process | Mean/Rate | CV | Stability |
|---------|-----------|-----|-----------|
| Task Duration | {td.get('mean_min', 0):.2f} min | {td.get('cv', 0):.4f} | {td.get('stability', 'Unknown')} |
| Failure Rate | {fr.get('overall_rate_pct', 0):.4f}% | {fr.get('cv', 0):.4f} | {fr.get('stability', 'Unknown')} |
| System Errors | {se.get('mean_rate', 0):.4f} | {se.get('cv', 0):.4f} | {se.get('stability', 'Unknown')} |

### Variability Ranking (Highest to Lowest CV)

| Rank | Process | CV |
|------|---------|-----|
| 1 | {highest_process} | {max(td.get('cv', 0), fr.get('cv', 0), se.get('cv', 0)):.4f} |

## Most Significant Risks

{highest_process} is the highest-risk process.

Key risk indicators:
- Task duration: {td.get('stability', 'Unknown')} trend (slope = {td.get('trend_slope', 0):.6f})
- Failure rate: {fr.get('stability', 'Unknown')} (rate = {fr.get('overall_rate_pct', 0):.4f}%, target = {fr.get('target_rate_pct', 1.0)}%)
- System errors: {se.get('stability', 'Unknown')} (CV = {se.get('cv', 0):.4f})

## Prioritized Corrective Actions

| Priority | Action | Owner | Timeline |
|----------|--------|-------|----------|
| 1 | Investigate root causes of high {highest_process} variability | Process Owner | 30 days |
| 2 | Implement process controls and monitoring | Quality Engineer | 45 days |
| 3 | Establish continuous improvement feedback loop | Operations Manager | 60 days |

## Monitoring Plan

### Process to be Monitored
{highest_process}

### Inputs
- Daily operational data
- Error logs
- Process metrics
- System performance indicators

### Outputs
- Daily rate (%)
- Trend analysis
- Variability assessment (CV)
- Stability classification

### Key Performance Indicators (KPIs)
- Rate (%)
- Coefficient of Variation (CV)
- Trend slope
- Trend significance

### Frequency of Monitoring
Daily

### Observation Format
Time-series data collection with continuous monitoring

### Roles
- Process Owner
- Quality Engineer
- Data Analyst
- Operations Manager

### Reporting Format
Daily dashboard report with trend charts and statistical summaries

### Corrective Action Process
PDCA cycle (Plan-Do-Check-Act) with root cause analysis for out-of-control points

### Benchmarks
- **target_rate_pct:** {fr.get('target_rate_pct', 1.0)}
- **max_acceptable_cv:** 0.15
- **stability_threshold_t_stat:** 2.0

### Project Codename
{project_name}

### 30/60/90 Day Momentum Plan
- **30 Days:** Baseline stabilization and root cause identification
- **60 Days:** Process control implementation and automation
- **90 Days:** Continuous improvement and capability expansion

---
*Generated by Process Capability Analysis. All metrics computed using sample standard deviation (ddof=1) and standard trend analysis.*
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

        if 'task' in sheet_lower or 'duration' in sheet_lower:
            results['task_duration'] = analyze_task_duration(df)
        elif 'failure' in sheet_lower or 'fail' in sheet_lower:
            results['failure_rate'] = analyze_failure_rate(df, args.target_rate)
        elif 'error' in sheet_lower or 'system' in sheet_lower:
            results['system_errors'] = analyze_system_errors(df)

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
        "task_duration": results.get("task_duration", {}),
        "failure_rate": results.get("failure_rate", {}),
        "system_errors": results.get("system_errors", {}),
        "variability_ranking": ranking,
        "highest_variability_process": highest_process,
        "highest_risk_statement": f"{highest_process} is the highest-risk process.",
        "extended_analysis": generate_extended_analysis(
            results.get("task_duration", {}),
            results.get("failure_rate", {}),
            results.get("system_errors", {})
        ),
        "monitoring_plan": generate_monitoring_plan(highest_process, results, args.project_name)
    }

    with open(args.output_json, 'w') as f:
        json.dump(output, f, indent=2)

    brief = generate_brief(output, highest_process, args.project_name)
    with open(args.output_md, 'w') as f:
        f.write(brief)

    print(f"JSON report written to {args.output_json}")
    print(f"Brief written to {args.output_md}")
    print(f"Highest variability process: {highest_process} (CV={ranking[0]['cv']:.4f})")
    print(f"Project codename: {args.project_name}")


if __name__ == '__main__':
    main()
