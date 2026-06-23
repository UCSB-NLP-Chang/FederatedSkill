#!/usr/bin/env python3
"""
Deterministic pipeline performance metrics calculator.
Outputs JSON to stdout matching references/output_schema.md.
Usage: python3 compute_pipeline_metrics.py <data_path> <target_error_rate_pct>
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
        print("Usage: compute_pipeline_metrics.py <data_path> <target_error_rate_pct>", file=sys.stderr)
        sys.exit(1)
        
    data_path = sys.argv[1]
    target_rate = float(sys.argv[2]) / 100.0
    
    if data_path.lower().endswith('.csv'):
        df = pd.read_csv(data_path)
        data_sources = [("Data", df)]
    else:
        xls = pd.ExcelFile(data_path)
        data_sources = [(name, pd.read_excel(xls, sheet_name=name)) for name in xls.sheet_names]
        
    result = {"extended_analysis": {}}
    cv_ranking = []
    
    for name, data in data_sources:
        data.columns = data.columns.str.strip()
        date_col = next((c for c in data.columns if 'date' in c.lower()), None)
        metric_cols = [c for c in data.columns if c != date_col and pd.api.types.is_numeric_dtype(data[c])]
        
        key = name.lower().replace(" ", "_")
        
        # Check for proportion structure (e.g., Bugs Found / Lines Reviewed)
        is_proportion = False
        num_col, den_col = None, None
        if len(metric_cols) == 2:
            c1, c2 = metric_cols
            if any(k in c1.lower() for k in ['bugs', 'num', 'error']) and any(k in c2.lower() for k in ['lines', 'denom', 'review']):
                num_col, den_col = c1, c2
                is_proportion = True
            elif any(k in c2.lower() for k in ['bugs', 'num', 'error']) and any(k in c1.lower() for k in ['lines', 'denom', 'review']):
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
            
            x = list(range(1, n + 1))
            slope, _, _, p_val, _ = stats.linregress(x, daily_props)
            t_stat = slope / (std_v / math.sqrt(n)) if std_v > 0 else 0.0
            stability = "Unstable" if abs(t_stat) > 2.0 else "Stable"
            
            result[key] = {
                "mean_proportion": round(mean_v, 6),
                "sample_std_proportion": round(std_v, 6),
                "coefficient_of_variation": round(cv, 4),
                "overall_rate_percent": round(overall_rate * 100, 4),
                "overall_bugs_found": int(total_errors),
                "overall_lines_reviewed": int(total_trials),
                "wilson_ci_lower_pct": round(ci_low * 100, 4),
                "wilson_ci_upper_pct": round(ci_high * 100, 4),
                "trend_slope": round(slope, 6),
                "trend_t_stat": round(t_stat, 4),
                "stability": stability,
                "n_observations": n,
                "uses_varying_denominators": True,
                "target_rate_pct": target_rate * 100,
                "capability_vs_target": "Capable" if overall_rate < target_rate else "Not Capable"
            }
            result["extended_analysis"][key] = {
                "min_value": round(daily_props.min(), 4),
                "max_value": round(daily_props.max(), 4),
                "range": round(daily_props.max() - daily_props.min(), 4),
                "median": round(daily_props.median(), 4),
                "trend_direction": "increasing" if slope > 0 else ("decreasing" if slope < 0 else "stable")
            }
            cv_ranking.append((name, cv, key))
        else:
            vals = data[metric_cols[0]].dropna().astype(float) if metric_cols else pd.Series([])
            n = len(vals)
            if n < 2: continue
            
            mean_v = vals.mean()
            std_v = vals.std(ddof=1)
            cv = std_v / mean_v if mean_v != 0 else 0.0
            
            x = list(range(1, n + 1))
            slope, _, _, p_val, _ = stats.linregress(x, vals)
            t_stat = slope / (std_v / math.sqrt(n)) if std_v > 0 else 0.0
            stability = "Unstable" if abs(t_stat) > 2.0 else "Stable"
            
            result[key] = {
                "mean": round(mean_v, 4),
                "sample_std": round(std_v, 4),
                "coefficient_of_variation": round(cv, 4),
                "trend_slope": round(slope, 6),
                "trend_t_stat": round(t_stat, 4),
                "stability": stability,
                "n_observations": n
            }
            result["extended_analysis"][key] = {
                "min_value": round(vals.min(), 4),
                "max_value": round(vals.max(), 4),
                "range": round(vals.max() - vals.min(), 4),
                "median": round(vals.median(), 4),
                "trend_direction": "increasing" if slope > 0 else ("decreasing" if slope < 0 else "stable")
            }
            cv_ranking.append((name, cv, key))
            
    cv_ranking.sort(key=lambda x: x[1], reverse=True)
    highest_risk = cv_ranking[0][0] if cv_ranking else "Unknown"
    
    result["variability_ranking"] = [
        {"process": name, "coefficient_of_variation": round(cv, 4), "rank": i+1}
        for i, (name, cv, _) in enumerate(cv_ranking)
    ]
    result["highest_variability_process"] = highest_risk
    result["highest_risk_statement"] = f"{highest_risk} is the highest-risk stage."
    result["improvement_plan"] = {
        "process": "CI/CD Pipeline Performance",
        "methodology": "Statistical Process Control (SPC) combined with Six Sigma DMAIC framework for continuous pipeline quality improvement",
        "root_cause_approach": "Ishikawa fishbone analysis and 5-Why investigation targeting the top variability drivers, with correlation analysis against all metric series",
        "incident_response_plan": "Automated circuit-breaker thresholds: halt deployments when rolling 5-point failure rate exceeds mean + 2*std, auto-rollback on consecutive failures, and escalation for SLO breaches",
        "technical_debt_assessment": "Evaluate build cache efficiency, dependency layer optimization, and test suite flakiness to reduce baseline variability",
        "milestones_30_60_90_days": {
            "30_days": "Stabilize highest variability process and implement daily tracking",
            "60_days": "Deploy real-time monitoring dashboard with SPC control charts",
            "90_days": "Conduct architecture review and retire accumulated technical debt"
        },
        "codename": "Project ForgeSteady",
        "success_criteria": "Reduce CV of highest-risk process by 20% and maintain capability vs target for 3 consecutive months"
    }
    
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
