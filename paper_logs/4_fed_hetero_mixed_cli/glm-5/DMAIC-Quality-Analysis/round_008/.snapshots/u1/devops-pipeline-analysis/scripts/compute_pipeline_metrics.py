#!/usr/bin/env python3
"""
Computes DevOps pipeline metrics from multi-sheet Excel data.
Analyzes Build Duration, Bug Rate, and Deployment Failures.

Usage:
  python3 compute_pipeline_metrics.py \
    --input pipeline_data.xlsx \
    --output-json report.json \
    --output-md brief.md \
    --project-name "Pipeline Optimization"

Requires: pandas, numpy, scipy, openpyxl
"""
import argparse
import json
import math
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True, help='Excel file path')
    p.add_argument('--output-json', default='report.json')
    p.add_argument('--output-md', default='brief.md')
    p.add_argument('--target-rate', type=float, default=3.0,
                   help='Target bug rate percentage (default 3.0)')
    p.add_argument('--project-name', default=None,
                   help='Project name for improvement_plan.project_codename (default: derived from input filename)')
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
    """Linear regression trend analysis."""
    if len(x) < 2:
        return (0.0, 0.0, 1.0, "Stable")
    slope, intercept, r_val, p_val, std_err = stats.linregress(x, y)
    t_stat = slope / std_err if std_err != 0 else 0.0
    if p_val < 1e-10:
        p_val = 1e-15
    stability = "Stable" if abs(t_stat) < 2.0 else "Unstable"
    return (slope, t_stat, p_val, stability)


def analyze_build_duration(df):
    values = df.iloc[:, 1].astype(float).values
    mean_val = float(np.mean(values))
    std_val = float(np.std(values, ddof=1))
    cv = std_val / mean_val if mean_val != 0 else 0.0
    x = np.arange(1, len(values) + 1)
    slope, t_stat, p_val, stability = compute_trend(x, values)
    return {
        "mean_sec": mean_val,
        "sample_std_sec": std_val,
        "cv": cv,
        "trend_slope": slope,
        "trend_t_stat": t_stat,
        "trend_p_value": p_val,
        "stability": stability,
        "n": len(values)
    }


def analyze_bug_rate(df, target_rate_pct=3.0):
    lines = df.iloc[:, 1].astype(float).values
    bugs = df.iloc[:, 2].astype(float).values
    total_bugs = int(np.sum(bugs))
    total_lines = int(np.sum(lines))
    overall_rate = total_bugs / total_lines if total_lines > 0 else 0.0
    overall_rate_pct = overall_rate * 100
    proportions = bugs / lines
    mean_prop = float(np.mean(proportions))
    std_prop = float(np.std(proportions, ddof=1))
    cv = std_prop / mean_prop if mean_prop != 0 else 0.0
    ci_low, ci_high = wilson_interval(total_bugs, total_lines)
    x = np.arange(1, len(proportions) + 1)
    slope, t_stat, p_val, stability = compute_trend(x, proportions)
    capability = "Capable" if overall_rate_pct <= target_rate_pct else "Not Capable"
    return {
        "total_bugs": total_bugs,
        "total_lines_reviewed": total_lines,
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


def analyze_deployment_failures(df):
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


def generate_improvement_plan(highest_process, results, project_name):
    return {
        "process": highest_process,
        "methodology": "Lean Six Sigma DMAIC with Agile retrospectives",
        "root_cause_approach": "5 Whys and Fishbone diagram analysis for out-of-control points",
        "incident_response_plan": "Automated rollback triggers and post-incident blameless reviews",
        "technical_debt_assessment": "Quarterly code quality audits and refactoring sprints",
        "prioritized_actions": [
            {"priority": 1, "action": f"Stabilize {highest_process} variability through process controls", "owner": "DevOps Lead", "timeline": "30 days"},
            {"priority": 2, "action": "Implement automated quality gates and monitoring", "owner": "QA Engineering", "timeline": "45 days"},
            {"priority": 3, "action": "Establish continuous feedback loops and training", "owner": "Engineering Managers", "timeline": "60 days"}
        ],
        "project_codename": project_name,
        "momentum_plan_30_60_90": {
            "30_days": "Baseline stabilization and root cause identification",
            "60_days": "Process control implementation and automation",
            "90_days": "Continuous improvement and capability expansion"
        }
    }


def generate_extended_analysis(bd_results, br_results, df_results):
    return {
        "build_duration": {"n": bd_results.get("n", 0)},
        "bug_rate": {
            "total_bugs": br_results.get("total_bugs", 0),
            "total_lines_reviewed": br_results.get("total_lines_reviewed", 0),
            "n": br_results.get("n", 0)
        },
        "deployment_failures": {"n": df_results.get("n", 0)}
    }


def generate_brief(results, highest_process, project_name):
    bd = results.get("build_duration", {})
    br = results.get("bug_rate", {})
    df = results.get("deployment_failures", {})
    brief = f"""# {project_name} — DevOps Pipeline Performance Brief

## Summary of Findings

This assessment analyzes pipeline performance across three critical stages: Build Duration, Bug Rate, and Deployment Failures.

| Process | Mean/Rate | CV | Stability |
|---------|-----------|-----|-----------|
| Build Duration | {bd.get('mean_sec', 0):.2f} sec | {bd.get('cv', 0):.4f} | {bd.get('stability', 'Unknown')} |
| Bug Rate | {br.get('overall_rate_pct', 0):.4f}% | {br.get('cv', 0):.4f} | {br.get('stability', 'Unknown')} |
| Deployment Failures | {df.get('mean_rate', 0):.4f} | {df.get('cv', 0):.4f} | {df.get('stability', 'Unknown')} |

### Variability Ranking (Highest to Lowest CV)

| Rank | Process | CV |
|------|---------|-----|
| 1 | {highest_process} | {max(bd.get('cv', 0), br.get('cv', 0), df.get('cv', 0)):.4f} |

## Most Significant Risks

{highest_process} is the highest-risk stage.

Key risk indicators:
- Build duration: {bd.get('stability', 'Unknown')} trend (slope = {bd.get('trend_slope', 0):.6f})
- Bug rate: {br.get('stability', 'Unknown')} (rate = {br.get('overall_rate_pct', 0):.4f}%, target = {br.get('target_rate_pct', 3.0)}%)
- Deployment failures: {df.get('stability', 'Unknown')} (CV = {df.get('cv', 0):.4f})

## Improvement Plan

Process: {highest_process}
Methodology: Lean Six Sigma DMAIC with Agile retrospectives
Project Codename: {project_name}

### Prioritized Actions
| Priority | Action | Owner | Timeline |
|----------|--------|-------|----------|
| 1 | Stabilize {highest_process} variability through process controls | DevOps Lead | 30 days |
| 2 | Implement automated quality gates and monitoring | QA Engineering | 45 days |
| 3 | Establish continuous feedback loops and training | Engineering Managers | 60 days |

### 30/60/90 Day Momentum Plan
- **30 Days:** Baseline stabilization and root cause identification
- **60 Days:** Process control implementation and automation
- **90 Days:** Continuous improvement and capability expansion

---
*Generated by DevOps Pipeline Analysis. All metrics computed using sample standard deviation (ddof=1) and standard trend analysis.*
"""
    return brief


def main():
    # Pre-flight scipy check
    try:
        from scipy import stats as _stats
    except ImportError:
        print("ERROR: scipy is not available.", file=sys.stderr)
        print("Install with: pip install scipy", file=sys.stderr)
        sys.exit(1)

    args = parse_args()

    # Derive project name from input file if not provided
    project_name = args.project_name
    if project_name is None:
        base_name = os.path.splitext(os.path.basename(args.input))[0]
        # Convert filename to title case project name
        project_name = base_name.replace('_', ' ').replace('-', ' ').title()
        if not project_name:
            project_name = "Pipeline Optimization"

    xl = pd.ExcelFile(args.input)
    results = {}

    for sheet in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sheet)
        sheet_lower = sheet.lower()
        if 'build' in sheet_lower:
            results['build_duration'] = analyze_build_duration(df)
        elif 'bug' in sheet_lower:
            results['bug_rate'] = analyze_bug_rate(df, args.target_rate)
        elif 'deploy' in sheet_lower or 'failure' in sheet_lower:
            results['deployment_failures'] = analyze_deployment_failures(df)

    ranking = []
    for process, data in results.items():
        ranking.append({"process": process.replace('_', ' ').title(), "cv": data.get("cv", 0.0)})
    ranking.sort(key=lambda x: x["cv"], reverse=True)
    for i, item in enumerate(ranking, 1):
        item["rank"] = i

    highest_process = ranking[0]["process"] if ranking else "Unknown"

    output = {
        "build_duration": results.get("build_duration", {}),
        "bug_rate": results.get("bug_rate", {}),
        "deployment_failures": results.get("deployment_failures", {}),
        "variability_ranking": ranking,
        "highest_variability_process": highest_process,
        "highest_risk_statement": f"{highest_process} is the highest-risk stage.",
        "extended_analysis": generate_extended_analysis(
            results.get("build_duration", {}),
            results.get("bug_rate", {}),
            results.get("deployment_failures", {})
        ),
        "improvement_plan": generate_improvement_plan(highest_process, results, project_name)
    }

    with open(args.output_json, 'w') as f:
        json.dump(output, f, indent=2)

    brief = generate_brief(output, highest_process, project_name)
    with open(args.output_md, 'w') as f:
        f.write(brief)

    print(f"JSON report written to {args.output_json}")
    print(f"Brief written to {args.output_md}")
    print(f"Highest variability process: {highest_process} (CV={ranking[0]['cv']:.4f})")


if __name__ == '__main__':
    main()
