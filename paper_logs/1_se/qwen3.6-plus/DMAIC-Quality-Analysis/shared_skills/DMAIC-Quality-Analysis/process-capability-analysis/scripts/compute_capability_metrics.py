#!/usr/bin/env python3
"""
Deterministic process capability metrics calculator.
Outputs JSON to stdout matching references/output_schema.md.
Usage: python3 compute_capability_metrics.py <data_path> <target_error_rate_pct>
"""
import json
import sys
import math
import pandas as pd
from scipy import stats

def wilson_ci(successes, trials, confidence=0.95):
    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    p_hat = successes / trials
    denom = 1 + z**2 / trials
    center = (p_hat + z**2 / (2 * trials)) / denom
    spread = (z * math.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * trials)) / trials)) / denom
    return center - spread, center + spread

def compute_trend(vals):
    n = len(vals)
    x = list(range(1, n + 1))
    slope, _, _, _, _ = stats.linregress(x, vals)
    std_v = vals.std(ddof=1)
    t_stat = slope / (std_v / math.sqrt(n)) if std_v > 0 else 0.0
    stability = "Unstable" if abs(t_stat) > 2.0 else "Stable"
    return round(slope, 8), round(t_stat, 6), stability

def main():
    if len(sys.argv) < 3:
        print("Usage: compute_capability_metrics.py <data_path> <target_error_rate_pct>", file=sys.stderr)
        sys.exit(1)
        
    data_path = sys.argv[1]
    target_rate = float(sys.argv[2]) / 100.0
    
    if data_path.lower().endswith('.csv'):
        df = pd.read_csv(data_path)
        data_sources = [("Data", df)]
    else:
        xls = pd.ExcelFile(data_path)
        data_sources = [(name, pd.read_excel(xls, sheet_name=name)) for name in xls.sheet_names]
        
    result = {}
    cv_ranking = []
    process_summaries = {}
    
    for name, data in data_sources:
        data.columns = data.columns.str.strip()
        date_col = next((c for c in data.columns if 'date' in c.lower()), None)
        metric_cols = [c for c in data.columns if c != date_col and pd.api.types.is_numeric_dtype(data[c])]
        
        key = name.lower().replace(" ", "_")
        
        # Detect proportion structure
        is_proportion = False
        num_col, den_col = None, None
        if len(metric_cols) == 2:
            c1, c2 = metric_cols
            if any(k in c1.lower() for k in ['damaged', 'error', 'num', 'fail', 'bugs']) and any(k in c2.lower() for k in ['shipment', 'denom', 'total', 'review', 'units', 'lines']):
                num_col, den_col = c1, c2
                is_proportion = True
            elif any(k in c2.lower() for k in ['damaged', 'error', 'num', 'fail', 'bugs']) and any(k in c1.lower() for k in ['shipment', 'denom', 'total', 'review', 'units', 'lines']):
                num_col, den_col = c2, c1
                is_proportion = True
                
        if is_proportion and num_col and den_col:
            total_trials = data[den_col].sum()
            total_errors = data[num_col].sum()
            overall_rate = total_errors / total_trials if total_trials > 0 else 0.0
            ci_low, ci_high = wilson_ci(total_errors, total_trials)
            
            daily_props = (data[num_col] / data[den_col]).dropna()
            n = len(daily_props)
            mean_v = daily_props.mean()
            std_v = daily_props.std(ddof=1)
            cv = std_v / mean_v if mean_v != 0 else 0.0
            slope, t_stat, stability = compute_trend(daily_props)
            
            result[key] = {
                "uses_varying_denominators": True,
                "total_trials": int(total_trials),
                "total_errors": int(total_errors),
                "overall_rate_pct": round(overall_rate * 100, 4),
                "wilson_ci_lower_pct": round(ci_low * 100, 4),
                "wilson_ci_upper_pct": round(ci_high * 100, 4),
                "mean_proportion": round(mean_v, 6),
                "sample_std_proportion": round(std_v, 6),
                "coefficient_of_variation": round(cv, 6),
                "trend": {"slope": slope, "t_stat": t_stat, "stability": stability},
                "target_rate_pct": target_rate * 100,
                "capability_vs_target": "Capable" if overall_rate < target_rate else "Not Capable"
            }
            process_summaries[key] = f"Overall {key.replace('_', ' ')} rate of {round(overall_rate*100, 4)}% against {target_rate*100}% target. Process is {'Capable' if overall_rate < target_rate else 'Not Capable'}. Trend is {stability} (t={t_stat})."
            cv_ranking.append((name, cv, key))
        else:
            vals = data[metric_cols[0]].dropna().astype(float) if metric_cols else pd.Series([])
            n = len(vals)
            if n < 2: continue
            
            mean_v = vals.mean()
            std_v = vals.std(ddof=1)
            cv = std_v / mean_v if mean_v != 0 else 0.0
            slope, t_stat, stability = compute_trend(vals)
            
            unit = "value"
            if any(k in metric_cols[0].lower() for k in ['time', 'hour', 'hr', 'duration']): unit = "minutes"
            elif any(k in metric_cols[0].lower() for k in ['rate', 'accuracy', 'error']): unit = "rate"
            
            result[key] = {
                f"mean_{unit}": round(mean_v, 4),
                f"sample_std_{unit}": round(std_v, 4),
                "coefficient_of_variation": round(cv, 6),
                "trend": {"slope": slope, "t_stat": t_stat, "stability": stability}
            }
            process_summaries[key] = f"Mean {key.replace('_', ' ')} of {round(mean_v, 4)} {unit} with CV of {round(cv, 4)}. Trend is {stability} (t={t_stat})."
            cv_ranking.append((name, cv, key))
            
    cv_ranking.sort(key=lambda x: x[1], reverse=True)
    highest_risk = cv_ranking[0][0] if cv_ranking else "Unknown"
    
    result["variability_ranking"] = [{"process": name, "cv": round(cv, 6)} for name, cv, _ in cv_ranking]
    result["highest_variability_process"] = highest_risk
    result["highest_risk_statement"] = f"{highest_risk} is the highest-risk process."
    
    result["extended_analysis"] = {f"{k}_summary": v for k, v in process_summaries.items()}
    result["extended_analysis"]["risk_assessment"] = f"{highest_risk} is the highest-risk process."
    
    result["monitoring_plan"] = {
        "process_to_be_monitored": highest_risk,
        "inputs": "Daily operational logs and incident reports",
        "outputs": "Weekly performance dashboard and monthly executive summary",
        "key_performance_indicators": ["CV", "Trend Slope", "Stability t-stat", "Error Rate"],
        "frequency_of_monitoring": "Weekly review, monthly deep-dive",
        "observation_format": "Control charts and run charts",
        "roles": "Quality Manager, Process Lead, Operations Officer",
        "reporting_format": "Standardized JSON + Markdown brief",
        "corrective_action_process": "Identify root cause, implement countermeasure, verify effectiveness in 30 days",
        "benchmarks": "Industry standard CV < 0.20, Error Rate < target",
        "checklist": [
            "Verify data completeness",
            "Check for missing values",
            "Validate date ranges",
            "Confirm metric calculations",
            "Review control limits",
            "Assess trend direction",
            "Evaluate capability vs target",
            "Sign off by process lead"
        ],
        "prioritized_actions": [
            {"rank": 1, "area": highest_risk, "action": f"Deploy real-time verification at {highest_risk.lower()} stations to reduce variability", "expected_impact": "Reduce CV by 30% within 60 days"},
            {"rank": 2, "area": cv_ranking[1][0] if len(cv_ranking) > 1 else "Secondary Process", "action": "Implement reinforced protocols and root-cause analysis", "expected_impact": "Bring rate below target"},
            {"rank": 3, "area": cv_ranking[2][0] if len(cv_ranking) > 2 else "Tertiary Process", "action": "Optimize scheduling and establish buffer SLA thresholds", "expected_impact": "Reduce std dev by 15%"}
        ],
        "milestones_30_60_90_days": {
            "30_days": "Complete baseline audit of all processes; deploy error-rate dashboards; begin root-cause analysis.",
            "60_days": "Roll out automated verification at pilot sites; implement reinforced protocols; review first improvement metrics.",
            "90_days": "Scale verification to all centers; achieve measurable CV reduction; validate rates below targets."
        },
        "project_codename": "Project Capability"
    }
    
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
