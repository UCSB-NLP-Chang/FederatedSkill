#!/usr/bin/env python3
"""Calculate process capability indices (Cp, Cpk, Pp, Ppk) from Excel data.

Usage:
    python3 calculate_capability.py <excel_path> [--specs specs.json] [--output report.json]

Specs JSON format:
    {
        "sheet_name": {"usl": 60.0, "lsl": 30.0, "target": 45.0},
        "failure_rate": {"target_rate_pct": 1.0}
    }
"""
import sys
import json
import math
import pandas as pd
import numpy as np


def sample_std(series):
    """Sample standard deviation with Bessel's correction."""
    arr = np.asarray(series, dtype=float)
    n = len(arr)
    return float(np.std(arr, ddof=1)) if n > 1 else 0.0


def calculate_cp_cpk(series, usl, lsl):
    """Calculate Cp and Cpk for continuous data with spec limits."""
    arr = np.asarray(series, dtype=float)
    mean = float(np.mean(arr))
    std = sample_std(arr)
    
    if std == 0:
        return {"cp": None, "cpk": None, "mean": mean, "std": std}
    
    cp = (usl - lsl) / (6 * std)
    cpu = (usl - mean) / (3 * std)
    cpl = (mean - lsl) / (3 * std)
    cpk = min(cpu, cpl)
    
    return {
        "cp": float(cp),
        "cpk": float(cpk),
        "cpu": float(cpu),
        "cpl": float(cpl),
        "mean": mean,
        "sample_std": std,
        "cv": std / mean if mean != 0 else 0.0
    }


def classify_capability(cpk):
    """Classify process capability based on Cpk."""
    if cpk is None:
        return "Unknown"
    if cpk >= 1.33:
        return "Capable"
    if cpk >= 1.0:
        return "Marginal"
    return "Not Capable"


def analyze_task_duration(df, spec_col="Process Duration (min)", usl=None, lsl=None):
    """Analyze task duration with optional spec limits."""
    numeric_cols = df.select_dtypes(include='number').columns
    metric_col = None
    for col in numeric_cols:
        if "duration" in col.lower() or "time" in col.lower():
            metric_col = col
            break
    if metric_col is None and len(numeric_cols) > 0:
        metric_col = numeric_cols[0]
    
    series = df[metric_col].dropna().values
    
    result = {
        "mean": float(np.mean(series)),
        "sample_std": sample_std(series),
        "n": len(series),
        "cv": sample_std(series) / float(np.mean(series)) if float(np.mean(series)) != 0 else 0.0
    }
    
    if usl is not None and lsl is not None:
        cap = calculate_cp_cpk(series, usl, lsl)
        result.update(cap)
        result["capability_classification"] = classify_capability(cap.get("cpk"))
    
    return result


def wilson_ci(successes, trials, confidence=0.95):
    """Wilson score CI for proportions. Returns (lower, upper) in proportions."""
    if trials == 0:
        return 0.0, 1.0
    z = 1.959963984540054
    p = successes / trials
    denom = 1 + z**2 / trials
    center = (p + z**2 / (2 * trials)) / denom
    margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * trials)) / trials) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def analyze_rate_capability(df, bugs_col="Failures", lines_col="Units processed", target_rate_pct=None):
    """Analyze rate-based capability using Wilson CI vs target."""
    bugs = df[bugs_col].values
    lines = df[lines_col].values
    total_bugs = int(np.sum(bugs))
    total_lines = int(np.sum(lines))
    
    if total_lines == 0:
        return {"error": "No denominator data"}
    
    overall_rate = total_bugs / total_lines
    ci_lower, ci_upper = wilson_ci(total_bugs, total_lines)
    
    # Per-point proportions for CV
    proportions = bugs / lines
    mean_prop = float(np.mean(proportions))
    std_prop = sample_std(proportions)
    cv = std_prop / mean_prop if mean_prop > 0 else 0.0
    
    result = {
        "total_events": total_bugs,
        "total_opportunities": total_lines,
        "overall_rate_percent": overall_rate * 100,
        "wilson_ci_95_lower": ci_lower * 100,
        "wilson_ci_95_upper": ci_upper * 100,
        "sample_mean_per_point": mean_prop,
        "sample_std": std_prop,
        "cv": cv
    }
    
    if target_rate_pct is not None:
        target = target_rate_pct / 100
        result["target_rate_pct"] = target_rate_pct
        
        # Classify based on Wilson CI vs target
        if ci_lower > target:
            result["capability_classification"] = "Not Capable"
            result["capability_reason"] = "95% CI entirely above target"
        elif ci_upper < target:
            result["capability_classification"] = "Capable"
            result["capability_reason"] = "95% CI entirely below target"
        else:
            result["capability_classification"] = "Marginal"
            result["capability_reason"] = "Target falls within 95% CI"
    
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 calculate_capability.py <excel_path> [--specs specs.json] [--output report.json]")
        sys.exit(1)
    
    excel_path = sys.argv[1]
    specs_path = None
    output_path = None
    
    if "--specs" in sys.argv:
        idx = sys.argv.index("--specs")
        specs_path = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None
    
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        output_path = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None
    
    specs = {}
    if specs_path:
        with open(specs_path) as f:
            specs = json.load(f)
    
    xls = pd.ExcelFile(excel_path)
    results = {}
    
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        sheet_specs = specs.get(sheet, {})
        
        if "usl" in sheet_specs and "lsl" in sheet_specs:
            # Continuous with specs
            numeric_cols = df.select_dtypes(include='number').columns
            if len(numeric_cols) == 0:
                continue
            metric_col = numeric_cols[0]
            series = df[metric_col].dropna().values
            results[sheet] = calculate_cp_cpk(series, sheet_specs["usl"], sheet_specs["lsl"])
            results[sheet]["capability_classification"] = classify_capability(results[sheet].get("cpk"))
        elif "target_rate_pct" in sheet_specs or "rate" in sheet.lower() or "fail" in sheet.lower():
            # Rate-based capability
            cols = df.columns.tolist()
            events_col = None
            opps_col = None
            for c in cols:
                lc = c.lower()
                if any(x in lc for x in ["fail", "bug", "error", "defect", "event"]):
                    events_col = c
                if any(x in lc for x in ["unit", "line", "opportunit", "sample", "processed"]):
                    opps_col = c
            if events_col and opps_col:
                results[sheet] = analyze_rate_capability(df, events_col, opps_col, 
                                                         sheet_specs.get("target_rate_pct"))
        else:
            # Continuous without specs - basic stats only
            numeric_cols = df.select_dtypes(include='number').columns
            if len(numeric_cols) == 0:
                continue
            metric_col = numeric_cols[0]
            series = df[metric_col].dropna().values
            results[sheet] = {
                "mean": float(np.mean(series)),
                "sample_std": sample_std(series),
                "cv": sample_std(series) / float(np.mean(series)) if float(np.mean(series)) != 0 else 0.0,
                "note": "No spec limits provided - capability indices not calculated"
            }
    
    # Variability ranking by CV
    ranking = [(k, v.get("cv", 0)) for k, v in results.items() if isinstance(v, dict) and "cv" in v]
    ranking.sort(key=lambda x: x[1], reverse=True)
    
    results["variability_ranking"] = [{"process": k, "cv": v} for k, v in ranking]
    if ranking:
        results["highest_variability_process"] = ranking[0][0]
    
    output = json.dumps(results, indent=2)
    print(output)
    
    if output_path:
        with open(output_path, "w") as f:
            f.write(output)


if __name__ == "__main__":
    main()
