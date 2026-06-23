#!/usr/bin/env python3
"""
Transform base multi-metric analysis outputs to process capability format.

Usage:
    python transform_to_capability_format.py <base_json> <base_brief> --output-json <path> --output-brief <path> --target-rate <pct>
"""

import json
import argparse
import re

def transform_json(base_data, target_rate_pct=1.0):
    """Transform base analysis to process capability JSON structure."""
    
    # Map process names from base format to capability format
    process_map = {
        "wait_times": "task_duration",
        "medication_errors": "failure_rate", 
        "readmission_rates": "system_errors"
    }
    
    result = {}
    
    # Transform each process section
    for base_name, cap_name in process_map.items():
        if base_name not in base_data:
            continue
        base = base_data[base_name]
        
        if cap_name == "failure_rate":
            result[cap_name] = {
                "uses_varying_denominators": True,
                "target_rate_pct": target_rate_pct,
                "overall_rate_pct": round(base.get("overall_rate_percent", 0), 3),
                "sample_std": round(base.get("proportions_std", base.get("sample_std", 0)), 4),
                "cv": round(base.get("proportions_cv", base.get("cv", 0)), 3),
                "wilson_95_ci_pct": {
                    "lower": round(base.get("wilson_95_ci_lower", 0), 3),
                    "upper": round(base.get("wilson_95_ci_upper", 0), 3)
                },
                "capability_vs_target": base.get("capability_vs_target", "Capable"),
                "trend": {
                    "slope": round(base.get("trend_slope", 0), 6),
                    "t_stat": round(base.get("t_statistic", 0), 3),
                    "stability": base.get("stability", "Stable")
                }
            }
        else:
            result[cap_name] = {
                "mean": round(base.get("mean", 0), 3),
                "sample_std": round(base.get("sample_std", 0), 4),
                "cv": round(base.get("cv", 0), 3),
                "trend": {
                    "slope": round(base.get("trend_slope", 0), 6),
                    "t_stat": round(base.get("t_statistic", 0), 3),
                    "stability": base.get("stability", "Stable")
                }
            }
    
    # Copy ranking and risk identification
    result["variability_ranking"] = base_data.get("variability_ranking", [])
    result["highest_variability_process"] = base_data.get("highest_variability_process", "")
    
    # Transform risk statement to capability format
    base_statement = base_data.get("highest_risk_statement", "")
    # Replace "department" with "process"
    cap_statement = re.sub(r'(is the highest-risk)\s+department\.?', r'\1 process.', base_statement)
    if not cap_statement.endswith("process."):
        cap_statement = f"{result['highest_variability_process']} is the highest-risk process."
    result["highest_risk_statement"] = cap_statement
    
    # Transform extended analysis
    result["extended_analysis"] = {
        "summary": base_data.get("extended_analysis", {}).get("summary", ""),
        "key_findings": base_data.get("extended_analysis", {}).get("key_findings", [])
    }
    
    # Generate capability-specific monitoring plan
    highest = result["highest_variability_process"]
    result["monitoring_plan"] = generate_monitoring_plan(highest, target_rate_pct)
    
    return result

def generate_monitoring_plan(highest_risk_process, target_rate_pct):
    """Generate process capability monitoring plan."""
    return {
        "process_to_be_monitored": highest_risk_process,
        "inputs": [
            "Real-time transaction data from all workstations",
            "Error logs and rework case records",
            "Workstation performance metrics",
            "Time-stamped processing data"
        ],
        "outputs": [
            "Daily error rate reports",
            "Trend analysis dashboards",
            "Workstation performance rankings",
            "Alert notifications for anomaly detection"
        ],
        "key_performance_indicators": [
            f"Error Rate (target: < {target_rate_pct}%)",
            "Coefficient of Variation (target: < 1.0)",
            "Trend stability (t-statistic < 2.0)",
            "Rework cases per transaction batch",
            "Workstation-level error variance"
        ],
        "frequency_of_monitoring": "Continuous real-time monitoring with daily summary reports",
        "observation_format": "Automated data collection via system logs with structured CSV exports for analysis",
        "roles": {
            "process_owner": "Industrial Engineering Manager",
            "data_analyst": "Quality Assurance Analyst",
            "operators": "Processing Center Staff",
            "management": "Operations Director"
        },
        "reporting_format": "Weekly executive dashboard + Monthly detailed statistical report",
        "corrective_action_process": f"Trigger review when error rate exceeds {target_rate_pct * 1.5}% or CV > 2.0",
        "benchmarks": [
            f"Target error rate: < {target_rate_pct}%",
            "Best practice CV: < 0.5",
            "Stability threshold: |t-statistic| < 2.0"
        ],
        "prioritized_actions": [
            f"Deploy real-time monitoring for {highest_risk_process} process",
            "Investigate and address workstation-specific issues with highest error rates",
            "Implement standardized error prevention procedures across all workstations",
            "Continuous improvement program targeting CV reduction below 1.0"
        ],
        "checklist": [
            "Daily data validation complete",
            "Weekly trend calculated and reviewed",
            "Monthly statistical review scheduled",
            "Corrective actions documented",
            "Benchmark comparison updated",
            "Workstation performance ranked",
            "Alert thresholds verified"
        ],
        "momentum_plan_30_60_90": {
            "30_day": "Deploy real-time error monitoring dashboard and establish baseline metrics for all workstations",
            "60_day": "Complete workstation audits for top 5 highest error-rate stations and implement corrective actions",
            "90_day": f"Achieve target error rate below {target_rate_pct}% across all workstations with documented SOPs"
        },
        "project_codename": "Project Error-Free Operations (EFO)"
    }

def transform_brief(base_brief_text, transformed_json, target_rate_pct):
    """Transform base brief to process capability format."""
    
    highest = transformed_json["highest_variability_process"]
    td = transformed_json["task_duration"]
    fr = transformed_json["failure_rate"]
    se = transformed_json["system_errors"]
    mp = transformed_json["monitoring_plan"]
    
    brief = f"""# Process Capability Assessment Brief
## Brightland Processing Center

---

## Summary of Findings

This analysis evaluated three critical process metrics: Task Duration, Failure Rate, and System Errors.

**Key Metrics:**

| Process | Mean | Std Dev | CV | Trend Stability |
|---------|------|---------|-----|-----------------|
| Task Duration | {td['mean']:.2f} min | {td['sample_std']:.2f} | {td['cv']:.4f} | {td['trend']['stability']} |
| Failure Rate | {fr['overall_rate_pct']:.2f}% | {fr['sample_std']:.4f} | {fr['cv']:.4f} | {fr['trend']['stability']} |
| System Errors | {se['mean']:.2f}% | {se['sample_std']:.2f} | {se['cv']:.4f} | {se['trend']['stability']} |

**Overall Failure Rate:** {fr['overall_rate_pct']:.2f}% (95% CI: {fr['wilson_95_ci_pct']['lower']:.2f}% - {fr['wilson_95_ci_pct']['upper']:.2f}%)

**Capability vs Target ({target_rate_pct}%):** {fr['capability_vs_target']}

---

## Most Significant Risks

**Variability Ranking (by Coefficient of Variation - highest to lowest):**

"""
    
    for i, item in enumerate(transformed_json['variability_ranking'], 1):
        brief += f"{i}. **{item['process']}** (CV = {item['cv']:.4f})\n"
    
    brief += f"\n{transformed_json['highest_risk_statement']}\n\n"
    brief += f"**Risk Factors:**\n"
    brief += f"- {highest} shows the highest variability (CV = {transformed_json['variability_ranking'][0]['cv']:.4f})\n"
    brief += f"- Overall failure rate of {fr['overall_rate_pct']:.2f}% is {'below' if fr['capability_vs_target'] == 'Capable' else 'above'} target\n"
    brief += f"- Trend analysis shows {se['trend']['stability'].lower()} behavior for System Errors\n"
    
    brief += f"\n---\n\n## Prioritized Corrective Actions\n\n"
    for i, action in enumerate(mp['prioritized_actions'], 1):
        brief += f"{i}. **{['Immediate (Week 1)', 'Short-term (Weeks 2-4)', 'Medium-term (Months 2-3)', 'Long-term (Months 3-6)'][i-1]}:** {action}\n"
    
    brief += f"""
---

## Monitoring Plan

### Process to be Monitored
**{mp['process_to_be_monitored']}** - prioritized due to highest coefficient of variation.

### Inputs
"""
    for inp in mp['inputs']:
        brief += f"- {inp}\n"
    
    brief += "\n### Outputs\n"
    for out in mp['outputs']:
        brief += f"- {out}\n"
    
    brief += "\n### Key Performance Indicators (KPIs)\n"
    for kpi in mp['key_performance_indicators']:
        brief += f"- {kpi}\n"
    
    brief += f"\n### Frequency of Monitoring\n{mp['frequency_of_monitoring']}\n"
    brief += f"\n### Observation Format\n{mp['observation_format']}\n"
    
    brief += "\n### Roles\n| Role | Responsibility |\n|------|----------------|\n"
    for role, resp in mp['roles'].items():
        brief += f"| {role.replace('_', ' ').title()} | {resp} |\n"
    
    brief += f"\n### Reporting Format\n{mp['reporting_format']}\n"
    brief += f"\n### Corrective Action Process\n{mp['corrective_action_process']}\n"
    
    brief += "\n### Benchmarks\n"
    for bench in mp['benchmarks']:
        brief += f"- {bench}\n"
    
    brief += f"""
---

## Implementation Timeline

### 30-Day Momentum Milestone
{mp['momentum_plan_30_60_90']['30_day']}

### 60-Day Momentum Milestone
{mp['momentum_plan_30_60_90']['60_day']}

### 90-Day Momentum Milestone
{mp['momentum_plan_30_60_90']['90_day']}

---

## Checklist

"""
    for item in mp['checklist']:
        brief += f"- [ ] {item}\n"
    
    brief += f"\n---\n\n**Project Codename:** {mp['project_codename']}\n"
    
    return brief

def main():
    parser = argparse.ArgumentParser(description='Transform base analysis to process capability format')
    parser.add_argument('base_json', help='Base analysis JSON from patient_safety_analysis.py')
    parser.add_argument('base_brief', help='Base brief Markdown from patient_safety_analysis.py')
    parser.add_argument('--output-json', required=True, help='Output JSON file path')
    parser.add_argument('--output-brief', required=True, help='Output brief file path')
    parser.add_argument('--target-rate', type=float, default=1.0, help='Target rate percentage')
    args = parser.parse_args()
    
    # Read base JSON
    with open(args.base_json) as f:
        base_data = json.load(f)
    
    # Read base brief
    with open(args.base_brief) as f:
        base_brief = f.read()
    
    # Transform
    transformed = transform_json(base_data, args.target_rate)
    brief = transform_brief(base_brief, transformed, args.target_rate)
    
    # Write outputs
    with open(args.output_json, 'w') as f:
        json.dump(transformed, f, indent=2)
    print(f"JSON report created: {args.output_json}")
    
    with open(args.output_brief, 'w') as f:
        f.write(brief)
    print(f"Brief created: {args.output_brief}")

if __name__ == '__main__':
    main()
