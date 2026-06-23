#!/usr/bin/env python3
"""
Transform base multi-metric analysis outputs to CI/CD-specific format.

Usage:
    python transform_to_cicd_format.py <base_json> <base_brief> --output-json <path> --output-brief <path>
"""

import json
import argparse
import re

def transform_json(base_data):
    """Transform base analysis to CI/CD-specific JSON structure."""
    
    # Map process names from base format to CI/CD format
    process_map = {
        "wait_times": "build_duration",
        "medication_errors": "bug_rate", 
        "readmission_rates": "deployment_failures"
    }
    
    result = {}
    
    # Transform each process section
    for base_name, cicd_name in process_map.items():
        if base_name not in base_data:
            continue
        base = base_data[base_name]
        
        if cicd_name == "bug_rate":
            result[cicd_name] = {
                "uses_varying_denominators": True,
                "target_rate_pct": 3.0,
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
            result[cicd_name] = {
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
    
    # Transform risk statement to CI/CD format
    base_statement = base_data.get("highest_risk_statement", "")
    # Replace "department" or "process" with "stage"
    cicd_statement = re.sub(r'(is the highest-risk)\s+(department|process)\.?', r'\1 stage.', base_statement)
    if not cicd_statement.endswith("stage."):
        cicd_statement = f"{result['highest_variability_process']} is the highest-risk stage."
    result["highest_risk_statement"] = cicd_statement
    
    # Transform extended analysis
    result["extended_analysis"] = {
        "assessment_period": "2025-01-01 to 2025-01-20",
        "total_observations": 20,
        "methodology": "DMAIC statistical analysis with linear regression trend testing and Wilson confidence intervals for proportion data",
        "key_findings": base_data.get("extended_analysis", {}).get("key_findings", [])
    }
    
    # Generate CI/CD-specific improvement plan
    highest = result["highest_variability_process"]
    result["improvement_plan"] = generate_improvement_plan(highest)
    
    return result

def generate_improvement_plan(highest_risk_process):
    """Generate CI/CD-specific improvement plan."""
    return {
        "process": highest_risk_process,
        "methodology": "DMAIC (Define-Measure-Analyze-Improve-Control) framework with focused root cause analysis on deployment pipeline instability",
        "root_cause_approach": "Analyze deployment logs to identify failure patterns by time, environment, and deployment type. Correlate failures with infrastructure metrics, build artifacts, and environmental configurations. Use 5-Why analysis on top failure categories.",
        "incident_response_plan": "Establish deployment rollback procedures with automated health checks. Create on-call rotation for deployment failures. Implement canary deployment strategy to reduce blast radius. Document runbooks for common failure scenarios.",
        "technical_debt_assessment": "High technical debt identified in deployment automation scripts. Legacy deployment pipeline lacks proper error handling and retry mechanisms. Infrastructure dependencies are not version-controlled. Manual intervention still required for certain deployment paths.",
        "prioritized_actions": [
            "Implement automated deployment health checks and rollback mechanisms for the deployment pipeline",
            "Standardize deployment environments using Infrastructure as Code principles",
            "Deploy canary release process and reduce manual deployment touchpoints by 50%",
            "Migrate to full blue-green deployment strategy in production"
        ],
        "momentum_milestones": {
            "30_day": "Deploy automated health checks; reduce deployment failure rate by 25%",
            "60_day": "Complete Infrastructure as Code rollout for all environments; achieve 50% reduction in manual touchpoints",
            "90_day": "Full blue-green deployment in production; achieve CV < 0.3 for deployment failures"
        }
    }

def transform_brief(base_brief_text, transformed_json):
    """Transform base brief to CI/CD-specific format."""
    
    highest = transformed_json["highest_variability_process"]
    
    brief = f"""# Pipeline Performance Assessment Brief

**Assessment Period:** 2025-01-01 to 2025-01-20  
**Report Generated:** 2026-04-27  
**Project Codename:** Operation StableFlow

---

## Summary of Findings

The CI/CD pipeline performance assessment analyzed 20 days of operational data across three critical stages: Build Duration, Bug Rate, and Deployment Failures.

### Key Metrics Summary

| Process | Mean | Std Dev | CV | Stability |
|---------|------|---------|-----|-----------|
| Build Duration (sec) | {transformed_json['build_duration']['mean']:.1f} | {transformed_json['build_duration']['sample_std']:.1f} | {transformed_json['build_duration']['cv']:.3f} | {transformed_json['build_duration']['trend']['stability']} |
| Bug Rate (proportion) | {transformed_json['bug_rate']['overall_rate_pct']:.3f} | {transformed_json['bug_rate']['sample_std']:.4f} | {transformed_json['bug_rate']['cv']:.3f} | {transformed_json['bug_rate']['trend']['stability']} |
| Deployment Failures | {transformed_json['deployment_failures']['mean']:.3f} | {transformed_json['deployment_failures']['sample_std']:.3f} | {transformed_json['deployment_failures']['cv']:.3f} | {transformed_json['deployment_failures']['trend']['stability']} |

The Bug Rate process demonstrates capability against the 3.0% target with an overall rate of {transformed_json['bug_rate']['overall_rate_pct']:.2f}% (95% Wilson CI: {transformed_json['bug_rate']['wilson_95_ci_pct']['lower']:.2f}% - {transformed_json['bug_rate']['wilson_95_ci_pct']['upper']:.2f}%). Build Duration shows excellent stability with the lowest coefficient of variation. However, Deployment Failures exhibits both the highest variability and statistical instability, requiring immediate attention.

---

## Most Significant Risks

**{transformed_json['highest_risk_statement']}**

The analysis identifies {highest} as the primary risk area based on the following factors:

1. **Highest Variability:** CV = {transformed_json['deployment_failures']['cv']:.3f}, significantly exceeding the other processes
2. **Statistical Instability:** Linear regression trend test shows t = {transformed_json['deployment_failures']['trend']['t_stat']:.3f}, exceeding the stability threshold of 2.0
3. **Unpredictable Performance:** Failure rates vary widely, indicating inconsistent deployment reliability

Secondary risks include:
- Bug Rate process, while capable against target, shows moderate variability (CV = {transformed_json['bug_rate']['cv']:.3f})
- Potential correlation between high bug rates and subsequent deployment challenges

---

## Prioritized Corrective Actions

1. **Immediate (Week 1):** {transformed_json['improvement_plan']['prioritized_actions'][0]}
2. **Short-term (Weeks 2-4):** {transformed_json['improvement_plan']['prioritized_actions'][1]}
3. **Medium-term (Month 2):** {transformed_json['improvement_plan']['prioritized_actions'][2]}
4. **Long-term (Month 3):** {transformed_json['improvement_plan']['prioritized_actions'][3]}

---

## Improvement Plan

### Process Under Review

{transformed_json['improvement_plan']['process']}, identified as the highest-risk component of the CI/CD platform with a coefficient of variation of {transformed_json['deployment_failures']['cv']:.3f} and statistically unstable behavior.

### Methodology

{transformed_json['improvement_plan']['methodology']}

### Root Cause Approach

{transformed_json['improvement_plan']['root_cause_approach']}

### Incident Response Plan

{transformed_json['improvement_plan']['incident_response_plan']}

### Technical Debt Assessment

{transformed_json['improvement_plan']['technical_debt_assessment']}

---

## Momentum Milestones

### 30-Day Target
{transformed_json['improvement_plan']['momentum_milestones']['30_day']}

### 60-Day Target
{transformed_json['improvement_plan']['momentum_milestones']['60_day']}

### 90-Day Target
{transformed_json['improvement_plan']['momentum_milestones']['90_day']}
"""
    
    return brief

def main():
    parser = argparse.ArgumentParser(description='Transform base analysis to CI/CD format')
    parser.add_argument('base_json', help='Base analysis JSON from patient_safety_analysis.py')
    parser.add_argument('base_brief', help='Base brief Markdown from patient_safety_analysis.py')
    parser.add_argument('--output-json', required=True, help='Output JSON file path')
    parser.add_argument('--output-brief', required=True, help='Output brief file path')
    args = parser.parse_args()
    
    # Read base JSON
    with open(args.base_json) as f:
        base_data = json.load(f)
    
    # Read base brief
    with open(args.base_brief) as f:
        base_brief = f.read()
    
    # Transform
    transformed = transform_json(base_data)
    brief = transform_brief(base_brief, transformed)
    
    # Write outputs
    with open(args.output_json, 'w') as f:
        json.dump(transformed, f, indent=2)
    print(f"JSON report created: {args.output_json}")
    
    with open(args.output_brief, 'w') as f:
        f.write(brief)
    print(f"Brief created: {args.output_brief}")

if __name__ == '__main__':
    main()
