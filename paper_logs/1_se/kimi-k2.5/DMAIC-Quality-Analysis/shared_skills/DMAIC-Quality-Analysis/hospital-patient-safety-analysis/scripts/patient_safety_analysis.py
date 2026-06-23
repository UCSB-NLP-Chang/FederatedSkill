#!/usr/bin/env python3
"""
Hospital Patient Safety Analysis Script
Calculates CV, trend analysis, and Wilson CI for hospital metrics.

Usage:
    python patient_safety_analysis.py <input.xlsx> --output-json <path> --output-brief <path>
"""

import json
import math
import statistics
import argparse
import pandas as pd
from datetime import datetime

def calculate_wilson_ci(k, n, confidence=0.95):
    """Calculate Wilson score interval for proportion."""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    z = 1.96 if confidence == 0.95 else 2.576  # 95% or 99%
    
    denominator = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denominator
    
    return centre - margin, centre + margin

def calculate_trend_tstat(values, dates=None):
    """Calculate linear regression slope and t-statistic."""
    n = len(values)
    if n < 2:
        return 0.0, 0.0
    
    x = list(range(n))  # day index
    y = values
    
    x_mean = statistics.mean(x)
    y_mean = statistics.mean(y)
    
    numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
    denominator = sum((xi - x_mean) ** 2 for xi in x)
    
    if denominator == 0:
        return 0.0, 0.0
    
    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    
    # Calculate residuals and standard error
    predictions = [intercept + slope * xi for xi in x]
    residuals = [yi - pi for yi, pi in zip(y, predictions)]
    mse = sum(r**2 for r in residuals) / (n - 2) if n > 2 else 0
    se_slope = math.sqrt(mse / denominator) if denominator > 0 else 0
    
    t_stat = slope / se_slope if se_slope > 0 else 0
    
    return slope, t_stat

def analyze_wait_times(df):
    """Analyze wait time data (continuous)."""
    values = df['Patient Wait Time (min)'].tolist()
    
    mean_val = statistics.mean(values)
    std_val = statistics.stdev(values) if len(values) > 1 else 0
    cv = std_val / mean_val if mean_val != 0 else 0
    
    slope, t_stat = calculate_trend_tstat(values)
    stability = "Unstable" if abs(t_stat) > 2.0 else "Stable"
    
    return {
        "mean": round(mean_val, 5),
        "sample_std": std_val,
        "cv": cv,
        "trend_slope": slope,
        "t_statistic": t_stat,
        "stability": stability
    }

def analyze_medication_errors(df, target_rate_pct=2.0):
    """Analyze medication error data (proportion with varying denominators)."""
    total_prescriptions = df['Prescriptions Filled'].sum()
    total_errors = df['Errors'].sum()
    overall_rate = (total_errors / total_prescriptions * 100) if total_prescriptions > 0 else 0
    
    # Wilson CI for overall rate
    wilson_lower, wilson_upper = calculate_wilson_ci(total_errors, total_prescriptions)
    
    # Daily proportions for CV calculation
    daily_rates = (df['Errors'] / df['Prescriptions Filled']).tolist()
    proportions_mean = statistics.mean(daily_rates) * 100  # as percentage
    proportions_std = statistics.stdev(daily_rates) if len(daily_rates) > 1 else 0
    proportions_cv = proportions_std / statistics.mean(daily_rates) if statistics.mean(daily_rates) != 0 else 0
    
    # Trend on error counts (not rates)
    error_values = df['Errors'].tolist()
    slope, t_stat = calculate_trend_tstat(error_values)
    stability = "Unstable" if abs(t_stat) > 2.0 else "Stable"
    
    capability = "Capable" if overall_rate < target_rate_pct else "Not Capable"
    
    return {
        "total_prescriptions": int(total_prescriptions),
        "total_errors": int(total_errors),
        "overall_rate_percent": overall_rate,
        "wilson_95_ci_lower": wilson_lower * 100,
        "wilson_95_ci_upper": wilson_upper * 100,
        "proportions_mean": proportions_mean,
        "proportions_cv": proportions_cv,
        "trend_slope": slope,
        "t_statistic": t_stat,
        "stability": stability,
        "uses_varying_denominators": True,
        "target_rate_pct": target_rate_pct,
        "capability_vs_target": capability
    }

def analyze_readmission_rates(df):
    """Analyze readmission rate data (rates/proportions)."""
    values = df['Readmission Rate'].tolist()
    
    mean_val = statistics.mean(values)
    std_val = statistics.stdev(values) if len(values) > 1 else 0
    cv = std_val / mean_val if mean_val != 0 else 0
    
    slope, t_stat = calculate_trend_tstat(values)
    stability = "Unstable" if abs(t_stat) > 2.0 else "Stable"
    
    return {
        "mean": mean_val,
        "sample_std": std_val,
        "cv": cv,
        "trend_slope": slope,
        "t_statistic": t_stat,
        "stability": stability
    }

def generate_monitoring_plan(highest_risk_process):
    """Generate monitoring plan for highest risk process."""
    templates = {
        "Readmission Rates": {
            "process_to_be_monitored": "Readmission Rates",
            "inputs": [
                "Daily admission and readmission counts",
                "Patient demographic data",
                "Primary diagnosis codes",
                "Discharge disposition information"
            ],
            "outputs": [
                "Daily readmission rate percentage",
                "Trend analysis reports",
                "Risk-stratified readmission data",
                "30-day rolling average"
            ],
            "key_performance_indicators": [
                "Readmission Rate (target: <8%)",
                "Time between readmissions",
                "High-risk patient identification rate",
                "Discharge planning completion rate"
            ],
            "frequency_of_monitoring": "Daily data collection with weekly trend review and monthly statistical analysis",
            "observation_format": "Standardized data collection form with automated entry into quality management system",
            "roles": {
                "data_collector": "Quality Improvement Coordinator",
                "analyst": "Data Analyst",
                "reviewer": "Patient Safety Officer",
                "decision_maker": "Chief Medical Officer"
            },
            "reporting_format": "Weekly dashboard with trend charts, monthly statistical report",
            "corrective_action_process": "Trigger review when trend t-statistic > 2.0 or rate exceeds 10%",
            "benchmarks": [
                "National average: 8-10%",
                "Top quartile: <6%",
                "Internal target: <8%"
            ],
            "prioritized_actions": [
                "Implement enhanced discharge planning for high-risk patients",
                "Establish post-discharge follow-up within 48 hours",
                "Review cases with readmission within 7 days for process gaps"
            ],
            "checklist": [
                "Daily data validation complete",
                "Weekly trend calculated",
                "Monthly statistical review scheduled",
                "Corrective actions documented",
                "Benchmark comparison updated"
            ]
        },
        "Medication Errors": {
            "process_to_be_monitored": "Medication Errors",
            "inputs": [
                "Daily prescription counts",
                "Error incident reports",
                "Near-miss reports",
                "Pharmacy verification logs"
            ],
            "outputs": [
                "Daily error rate percentage",
                "Error trend analysis",
                "Root cause analysis reports",
                "Process improvement metrics"
            ],
            "key_performance_indicators": [
                "Medication Error Rate (target: <2.0%)",
                "High-alert medication error rate",
                "Barcode scanning compliance",
                "Pharmacist verification rate"
            ],
            "frequency_of_monitoring": "Daily data collection with weekly statistical review",
            "observation_format": "Electronic health record extraction with pharmacy system integration",
            "roles": {
                "data_collector": "Pharmacy Quality Coordinator",
                "analyst": "Patient Safety Analyst",
                "reviewer": "Pharmacy Director",
                "decision_maker": "Chief Pharmacy Officer"
            },
            "reporting_format": "Weekly error rate dashboard, monthly comprehensive analysis",
            "corrective_action_process": "Immediate review of errors >2.0% or any serious adverse event",
            "benchmarks": [
                "Internal target: <2.0%",
                "Best practice: <1.5%",
                "Alert threshold: >2.5%"
            ],
            "prioritized_actions": [
                "Enhance barcode medication administration compliance",
                "Implement double-check for high-alert medications",
                "Standardize prescription verification workflows"
            ],
            "checklist": [
                "Daily prescription count verified",
                "Errors logged and categorized",
                "Weekly trend analysis complete",
                "Root cause analysis for significant errors",
                "Staff education updates current"
            ]
        },
        "Wait Times": {
            "process_to_be_monitored": "Patient Wait Times",
            "inputs": [
                "Arrival timestamps",
                "Treatment start timestamps",
                "Patient acuity scores",
                "Staffing levels"
            ],
            "outputs": [
                "Average wait time by hour/day",
                "Wait time distribution charts",
                "Capacity analysis reports"
            ],
            "key_performance_indicators": [
                "Average wait time (target: <45 min)",
                "95th percentile wait time",
                "Patients waiting >60 minutes",
                "Left without being seen rate"
            ],
            "frequency_of_monitoring": "Real-time dashboard with daily summary reports",
            "observation_format": "Automated timestamp extraction from registration system",
            "roles": {
                "data_collector": "Registration Staff",
                "analyst": "Operations Analyst",
                "reviewer": "Department Manager",
                "decision_maker": "Operations Director"
            },
            "reporting_format": "Real-time dashboard, daily operational report",
            "corrective_action_process": "Alert when average wait exceeds 45 minutes or 95th percentile exceeds 90 minutes",
            "benchmarks": [
                "Target average: <45 minutes",
                "Best practice: <30 minutes",
                "Critical threshold: >60 minutes"
            ],
            "prioritized_actions": [
                "Optimize triage workflow",
                "Implement fast-track for low-acuity patients",
                "Adjust staffing based on volume patterns"
            ],
            "checklist": [
                "Timestamp accuracy verified",
                "Hourly averages calculated",
                "Daily summary generated",
                "Staffing adjustments reviewed",
                "Patient feedback collected"
            ]
        }
    }
    
    return templates.get(highest_risk_process, templates["Readmission Rates"])

def generate_brief(results, output_path):
    """Generate markdown brief."""
    wt = results["wait_times"]
    me = results["medication_errors"]
    rr = results["readmission_rates"]
    highest = results["highest_variability_process"]
    
    brief = f"""# Patient Safety Brief

## Summary of Findings

| Process | CV | Stability | Assessment |
|---------|-----|-----------|------------|
| **{highest}** | **{results['variability_ranking'][0]['cv']:.3f}** | **{rr['stability'] if highest == 'Readmission Rates' else (me['stability'] if highest == 'Medication Errors' else wt['stability'])}** | Highest risk |
| Medication Errors | {me['proportions_cv']:.3f} | {me['stability']} | {'Capable' if me['capability_vs_target'] == 'Capable' else 'Not Capable'} ({me['overall_rate_percent']:.2f}% vs {me['target_rate_pct']}% target) |
| Wait Times | {wt['cv']:.3f} | {wt['stability']} | Well controlled |

## Most Significant Risks

{results['highest_risk_statement']}

{results['extended_analysis']['summary']}

Key findings:
- {results['extended_analysis']['key_findings'][0]}
- {results['extended_analysis']['key_findings'][1]}
- {results['extended_analysis']['key_findings'][2]}
- {results['extended_analysis']['key_findings'][3]}

## Prioritized Corrective Actions

"""
    
    for i, action in enumerate(results['monitoring_plan']['prioritized_actions'], 1):
        brief += f"{i}. {action}\n"
    
    brief += f"""
## Monitoring Plan

### Process to be Monitored
{results['monitoring_plan']['process_to_be_monitored']}

### Inputs
"""
    for inp in results['monitoring_plan']['inputs']:
        brief += f"- {inp}\n"
    
    brief += "\n### Outputs\n"
    for out in results['monitoring_plan']['outputs']:
        brief += f"- {out}\n"
    
    brief += "\n### Key Performance Indicators (KPIs)\n"
    for kpi in results['monitoring_plan']['key_performance_indicators']:
        brief += f"- {kpi}\n"
    
    brief += f"\n### Frequency of Monitoring\n{results['monitoring_plan']['frequency_of_monitoring']}\n"
    brief += f"\n### Observation Format\n{results['monitoring_plan']['observation_format']}\n"
    
    brief += "\n### Roles\n"
    for role, person in results['monitoring_plan']['roles'].items():
        brief += f"- **{role.replace('_', ' ').title()}**: {person}\n"
    
    brief += f"\n### Reporting Format\n{results['monitoring_plan']['reporting_format']}\n"
    brief += f"\n### Corrective Action Process\n{results['monitoring_plan']['corrective_action_process']}\n"
    
    brief += "\n### Benchmarks\n"
    for bench in results['monitoring_plan']['benchmarks']:
        brief += f"- {bench}\n"
    
    with open(output_path, 'w') as f:
        f.write(brief)

def main():
    parser = argparse.ArgumentParser(description='Hospital Patient Safety Analysis')
    parser.add_argument('input_xlsx', help='Input Excel file with Wait Times, Medication Errors, Readmission Rates sheets')
    parser.add_argument('--output-json', required=True, help='Output JSON file path')
    parser.add_argument('--output-brief', required=True, help='Output Markdown brief path')
    parser.add_argument('--medication-target', type=float, default=2.0, help='Target rate % for medication errors')
    args = parser.parse_args()
    
    # Read Excel
    xl = pd.ExcelFile(args.input_xlsx)
    
    # Analyze each sheet
    wait_times = analyze_wait_times(pd.read_excel(xl, 'Wait Times'))
    medication_errors = analyze_medication_errors(pd.read_excel(xl, 'Medication Errors'), args.medication_target)
    readmission_rates = analyze_readmission_rates(pd.read_excel(xl, 'Readmission Rates'))
    
    # Rank by CV
    cv_ranking = [
        ("Readmission Rates", readmission_rates["cv"]),
        ("Medication Errors", medication_errors["proportions_cv"]),
        ("Wait Times", wait_times["cv"])
    ]
    cv_ranking.sort(key=lambda x: x[1], reverse=True)
    
    highest_variability = cv_ranking[0][0]
    highest_risk_statement = f"{highest_variability} is the highest-risk department."
    
    # Extended analysis
    extended = {
        "summary": f"{highest_variability} exhibits the highest variability (CV={cv_ranking[0][1]:.3f}) and requires priority attention.",
        "key_findings": [
            f"{cv_ranking[0][0]} CV ({cv_ranking[0][1]:.3f}) > {cv_ranking[1][0]} CV ({cv_ranking[1][1]:.3f}) > {cv_ranking[2][0]} CV ({cv_ranking[2][1]:.3f})",
            f"Stability: Readmission Rates ({readmission_rates['stability']}), Medication Errors ({medication_errors['stability']}), Wait Times ({wait_times['stability']})",
            f"Medication Errors rate ({medication_errors['overall_rate_percent']:.2f}%) is {'below' if medication_errors['overall_rate_percent'] < args.medication_target else 'above'} target ({args.medication_target}%)",
            f"Wilson 95% CI for medication errors: [{medication_errors['wilson_95_ci_lower']:.2f}%, {medication_errors['wilson_95_ci_upper']:.2f}%]"
        ]
    }
    
    # Generate monitoring plan
    monitoring_plan = generate_monitoring_plan(highest_variability)
    
    # Compile results
    results = {
        "wait_times": wait_times,
        "medication_errors": medication_errors,
        "readmission_rates": readmission_rates,
        "variability_ranking": [{"process": p, "cv": cv} for p, cv in cv_ranking],
        "highest_variability_process": highest_variability,
        "highest_risk_statement": highest_risk_statement,
        "extended_analysis": extended,
        "monitoring_plan": monitoring_plan
    }
    
    # Write JSON
    with open(args.output_json, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"JSON report created: {args.output_json}")
    
    # Generate brief
    generate_brief(results, args.output_brief)
    print(f"Brief created: {args.output_brief}")
    
    # Summary
    print(f"\nHighest variability process: {highest_variability} (CV={cv_ranking[0][1]:.3f})")
    print(f"Stability threshold: |t| > 2.0 indicates unstable")

if __name__ == '__main__':
    main()
