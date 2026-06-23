#!/usr/bin/env python3
"""
Computes logistics reliability metrics from multi-sheet Excel data.
Analyzes Delivery Times, Damage Rates, and Order Accuracy.

Usage:
  python3 compute_logistics_metrics.py \
    --input logistics_data.xlsx \
    --output-json report.json \
    --output-md brief.md \
    --project-name "Project Name" \
    --target-rate 1.5

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
    p.add_argument('--project-name', default='Logistics Reliability',
                   help='Project name for action plan (derive from task context)')
    p.add_argument('--target-rate', type=float, default=1.5,
                   help='Target damage rate percentage (default 1.5)')
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
    if p_val < 1e-10:
        p_val = 1e-15
    stability = "Stable" if abs(t_stat) < 2.0 else "Unstable"
    return (slope, t_stat, p_val, stability)


def analyze_delivery_times(df):
    """Analyze delivery times time series.
    Expects columns: Date, Delivery Time (hrs)
    """
    values = df.iloc[:, 1].astype(float).values
    mean_val = float(np.mean(values))
    std_val = float(np.std(values, ddof=1))
    cv = std_val / mean_val if mean_val != 0 else 0.0

    x = np.arange(1, len(values) + 1)
    slope, t_stat, p_val, stability = compute_trend(x, values)

    return {
        "mean_hrs": mean_val,
        "sample_std_hrs": std_val,
        "cv": cv,
        "trend_slope": slope,
        "trend_t_stat": t_stat,
        "trend_p_value": p_val,
        "stability": stability,
        "n": len(values)
    }


def analyze_damage_rates(df, target_rate_pct=1.5):
    """Analyze damage rates with varying denominators.
    Expects columns: Date, Shipments, Damaged
    """
    shipments = df.iloc[:, 1].astype(float).values
    damaged = df.iloc[:, 2].astype(float).values

    total_damaged = int(np.sum(damaged))
    total_shipments = int(np.sum(shipments))
    overall_rate = total_damaged / total_shipments if total_shipments > 0 else 0.0
    overall_rate_pct = overall_rate * 100

    proportions = damaged / shipments
    mean_prop = float(np.mean(proportions))
    std_prop = float(np.std(proportions, ddof=1))
    cv = std_prop / mean_prop if mean_prop != 0 else 0.0

    ci_low, ci_high = wilson_interval(total_damaged, total_shipments)

    x = np.arange(1, len(proportions) + 1)
    slope, t_stat, p_val, stability = compute_trend(x, proportions)

    capability = "Capable" if overall_rate_pct <= target_rate_pct else "Not Capable"

    return {
        "total_damaged": total_damaged,
        "total_shipments": total_shipments,
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


def analyze_order_accuracy(df):
    """Analyze order accuracy error rates time series.
    Expects columns: Date, Error Rate
    """
    values = df.iloc[:, 1].astype(float).values
    mean_val = float(np.mean(values))
    std_val = float(np.std(values, ddof=1))
    cv = std_val / mean_val if mean_val != 0 else 0.0

    x = np.arange(1, len(values) + 1)
    slope, t_stat, p_val, stability = compute_trend(x, values)

    return {
        "mean_error_rate": mean_val,
        "sample_std": std_val,
        "cv": cv,
        "trend_slope": slope,
        "trend_t_stat": t_stat,
        "trend_p_value": p_val,
        "stability": stability,
        "n": len(values)
    }


def generate_action_plan(highest_process, results, project_name):
    """Generate action plan structure with parameterized project name."""
    return {
        "process": highest_process,
        "prioritized_actions": [
            {"priority": 1, "action": f"Stabilize {highest_process} variability through process controls", "owner": "Operations Lead", "timeline": "30 days"},
            {"priority": 2, "action": "Implement automated quality gates and monitoring", "owner": "Quality Engineering", "timeline": "45 days"},
            {"priority": 3, "action": "Establish continuous feedback loops and training", "owner": "Supply Chain Managers", "timeline": "60 days"}
        ],
        "project_codename": project_name,
        "momentum_plan_30_60_90": {
            "30_days": "Baseline stabilization and root cause identification",
            "60_days": "Process control implementation and automation",
            "90_days": "Continuous improvement and capability expansion"
        }
    }


def generate_extended_analysis(dt_results, dr_results, oa_results):
    """Generate extended analysis with per-process counts."""
    return {
        "delivery_times": {"n": dt_results.get("n", 0)},
        "damage_rates": {
            "total_damaged": dr_results.get("total_damaged", 0),
            "total_shipments": dr_results.get("total_shipments", 0),
            "n": dr_results.get("n", 0)
        },
        "order_accuracy": {"n": oa_results.get("n", 0)}
    }


def generate_brief(results, highest_process, project_name):
    """Generate markdown brief with parameterized project name."""
    dt = results.get("delivery_times", {})
    dr = results.get("damage_rates", {})
    oa = results.get("order_accuracy", {})
    ap = results.get("action_plan", {})

    brief = f"""# {project_name} — Logistics Reliability Brief

## Summary of Findings

This assessment analyzes logistics reliability across three critical processes: Delivery Times, Damage Rates, and Order Accuracy.

| Process | Mean/Rate | CV | Stability |
|---------|-----------|-----|-----------|
| Delivery Times | {dt.get('mean_hrs', 0)} hrs | {dt.get('cv', 0)} | {dt.get('stability', 'Unknown')} |
| Damage Rates | {dr.get('overall_rate_pct', 0)}% | {dr.get('cv', 0)} | {dr.get('stability', 'Unknown')} |
| Order Accuracy | {oa.get('mean_error_rate', 0)} | {oa.get('cv', 0)} | {oa.get('stability', 'Unknown')} |

### Variability Ranking (Highest to Lowest CV)

| Rank | Process | CV |
|------|---------|-----|
| 1 | {highest_process} | {max(dt.get('cv', 0), dr.get('cv', 0), oa.get('cv', 0))} |

## Most Significant Risks

{highest_process} is the highest-risk process.

Key risk indicators:
- Delivery times: {dt.get('stability', 'Unknown')} trend (slope = {dt.get('trend_slope', 0)})
- Damage rates: {dr.get('stability', 'Unknown')} (rate = {dr.get('overall_rate_pct', 0)}%, target = {dr.get('target_rate_pct', 1.5)}%)
- Order accuracy: {oa.get('stability', 'Unknown')} (CV = {oa.get('cv', 0)})

## Action Plan

Process: {highest_process}
Project Codename: {project_name}

### Prioritized Actions
| Priority | Action | Owner | Timeline |
|----------|--------|-------|----------|
| 1 | {ap.get('prioritized_actions', [{}])[0].get('action', 'Stabilize variability')} | {ap.get('prioritized_actions', [{}])[0].get('owner', 'Operations Lead')} | {ap.get('prioritized_actions', [{}])[0].get('timeline', '30 days')} |
| 2 | {ap.get('prioritized_actions', [{}, {}])[1].get('action', 'Implement quality gates')} | {ap.get('prioritized_actions', [{}, {}])[1].get('owner', 'Quality Engineering')} | {ap.get('prioritized_actions', [{}, {}])[1].get('timeline', '45 days')} |
| 3 | {ap.get('prioritized_actions', [{}, {}, {}])[2].get('action', 'Continuous feedback loops')} | {ap.get('prioritized_actions', [{}, {}, {}])[2].get('owner', 'Supply Chain Managers')} | {ap.get('prioritized_actions', [{}, {}, {}])[2].get('timeline', '60 days')} |

### 30/60/90 Day Momentum Plan
- **30 Days:** {ap.get('momentum_plan_30_60_90', {}).get('30_days', 'Baseline stabilization')}
- **60 Days:** {ap.get('momentum_plan_30_60_90', {}).get('60_days', 'Process control implementation')}
- **90 Days:** {ap.get('momentum_plan_30_60_90', {}).get('90_days', 'Continuous improvement')}

---
*Generated by Logistics Reliability Analysis. All metrics computed using sample standard deviation (ddof=1) and t-statistic stability threshold (|t| < 2.0).*
"""
    return brief


def main():
    try:
        from scipy import stats as _stats
    except ImportError:
        print("ERROR: scipy is not available. Install with: pip install scipy", file=sys.stderr)
        sys.exit(1)

    args = parse_args()

    xl = pd.ExcelFile(args.input)

    results = {}

    for sheet in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sheet)
        sheet_lower = sheet.lower()

        if 'delivery' in sheet_lower or 'time' in sheet_lower:
            results['delivery_times'] = analyze_delivery_times(df)
        elif 'damage' in sheet_lower:
            results['damage_rates'] = analyze_damage_rates(df, args.target_rate)
        elif 'order' in sheet_lower or 'accuracy' in sheet_lower:
            results['order_accuracy'] = analyze_order_accuracy(df)

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
        "delivery_times": results.get("delivery_times", {}),
        "damage_rates": results.get("damage_rates", {}),
        "order_accuracy": results.get("order_accuracy", {}),
        "variability_ranking": ranking,
        "highest_variability_process": highest_process,
        "highest_risk_statement": f"{highest_process} is the highest-risk process.",
        "extended_analysis": generate_extended_analysis(
            results.get("delivery_times", {}),
            results.get("damage_rates", {}),
            results.get("order_accuracy", {})
        ),
        "action_plan": generate_action_plan(highest_process, results, args.project_name)
    }

    with open(args.output_json, 'w') as f:
        json.dump(output, f, indent=2)

    brief = generate_brief(output, highest_process, args.project_name)
    with open(args.output_md, 'w') as f:
        f.write(brief)

    print(f"JSON report written to {args.output_json}")
    print(f"Brief written to {args.output_md}")
    print(f"Highest variability process: {highest_process} (CV={ranking[0]['cv']})")
    print(f"Project name: {args.project_name}")


if __name__ == '__main__':
    main()
