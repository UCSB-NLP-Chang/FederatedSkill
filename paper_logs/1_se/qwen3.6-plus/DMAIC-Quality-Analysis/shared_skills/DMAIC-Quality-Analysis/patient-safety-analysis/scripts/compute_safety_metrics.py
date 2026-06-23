#!/usr/bin/env python3
"""
Deterministic patient safety metrics calculator.
Outputs JSON to stdout matching references/schema_and_sections.md.
Usage: python3 compute_safety_metrics.py <data_path> <target_error_rate_pct>
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

def main():
    if len(sys.argv) < 3:
        print("Usage: compute_safety_metrics.py <data_path> <target_error_rate_pct>", file=sys.stderr)
        sys.exit(1)
        
    data_path = sys.argv[1]
    target_rate = float(sys.argv[2]) / 100.0
    
    if data_path.lower().endswith('.csv'):
        df = pd.read_csv(data_path)
        data_sources = [("Data", df)]
    else:
        xls = pd.ExcelFile(data_path)
        data_sources = [(name, pd.read_excel(xls, sheet_name=name)) for name in xls.sheet_names]
        
    process_metrics = {}
    cv_ranking = []
    
    for name, data in data_sources:
        data.columns = data.columns.str.strip()
        date_col = next((c for c in data.columns if 'date' in c.lower()), None)
        metric_cols = [c for c in data.columns if c != date_col and pd.api.types.is_numeric_dtype(data[c])]
        
        for m_col in metric_cols:
            vals = data[m_col].dropna().astype(float)
            n = len(vals)
            if n < 2: continue
            
            mean_v = vals.mean()
            std_v = vals.std(ddof=1)
            cv = std_v / mean_v if mean_v != 0 else 0.0
            
            x = list(range(1, n + 1))
            slope, _, _, p_val, _ = stats.linregress(x, vals)
            t_stat = slope / (std_v / math.sqrt(n)) if std_v > 0 else 0.0
            stability = "Unstable" if abs(t_stat) > 2.0 else "Stable"
            
            process_metrics[name] = {
                "mean": round(mean_v, 4),
                "std": round(std_v, 4),
                "cv": round(cv, 4),
                "slope": round(slope, 6),
                "t_stat": round(t_stat, 4),
                "stability": stability
            }
            cv_ranking.append((name, cv))
            
    cv_ranking.sort(key=lambda x: x[1], reverse=True)
    highest_risk = cv_ranking[0][0] if cv_ranking else "Unknown"
    
    med_sheet = next((v for k, v in data_sources if 'med' in k.lower()), None)
    med_metrics = {}
    if med_sheet is not None:
        med_sheet.columns = med_sheet.columns.str.strip()
        trials_col = next((c for c in med_sheet.columns if 'prescri' in c.lower() or 'filled' in c.lower() or 'denom' in c.lower()), None)
        errors_col = next((c for c in med_sheet.columns if 'error' in c.lower() or 'num' in c.lower()), None)
        
        if trials_col and errors_col:
            total_trials = med_sheet[trials_col].sum()
            total_errors = med_sheet[errors_col].sum()
            overall_rate = total_errors / total_trials if total_trials > 0 else 0.0
            ci_low, ci_high = wilson_ci(total_errors, total_trials)
            uses_varying = True
        else:
            rate_col = next((c for c in med_sheet.columns if 'rate' in c.lower()), None)
            rates = med_sheet[rate_col].dropna() if rate_col else pd.Series([])
            overall_rate = rates.mean() if len(rates) > 0 else 0.0
            ci_low = overall_rate - 1.96 * rates.std() / math.sqrt(len(rates)) if len(rates) > 1 else overall_rate
            ci_high = overall_rate + 1.96 * rates.std() / math.sqrt(len(rates)) if len(rates) > 1 else overall_rate
            uses_varying = False
            
        capability = "Capable" if overall_rate < target_rate else "Not Capable"
        med_metrics = {
            "overall_rate_pct": round(overall_rate * 100, 4),
            "wilson_ci_low_pct": round(ci_low * 100, 4),
            "wilson_ci_high_pct": round(ci_high * 100, 4),
            "uses_varying_denominators": uses_varying,
            "target_rate_pct": target_rate * 100,
            "capability": capability
        }
        
    result = {
        "process_metrics": process_metrics,
        "variability_ranking": [x[0] for x in cv_ranking],
        "highest_risk_statement": f"{highest_risk} is the highest-risk department.",
        "medication_errors": med_metrics,
        "monitoring_plan": {
            "process_to_be_monitored": highest_risk,
            "inputs": "Daily operational logs and incident reports",
            "outputs": "Weekly safety dashboard and monthly executive summary",
            "key_performance_indicators": ["CV", "Trend Slope", "Stability t-stat", "Error Rate"],
            "frequency_of_monitoring": "Weekly review, monthly deep-dive",
            "observation_format": "Control charts and run charts",
            "roles": "Quality Manager, Department Lead, Safety Officer",
            "reporting_format": "Standardized JSON + Markdown brief",
            "corrective_action_process": "Identify root cause, implement countermeasure, verify effectiveness in 30 days",
            "benchmarks": "Industry standard CV < 0.20, Error Rate < 2.0%",
            "checklist": [
                "Verify data completeness",
                "Check for missing values",
                "Validate date ranges",
                "Confirm metric calculations",
                "Review control limits",
                "Assess trend direction",
                "Evaluate capability vs target",
                "Document special causes",
                "Sign off by department lead"
            ],
            "prioritized_actions": [
                {"action": "Stabilize highest variability process", "owner": "Quality Manager", "due": "30 days"},
                {"action": "Implement daily error tracking", "owner": "Department Lead", "due": "14 days"},
                {"action": "Conduct root cause analysis for outliers", "owner": "Safety Officer", "due": "21 days"}
            ]
        }
    }
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
