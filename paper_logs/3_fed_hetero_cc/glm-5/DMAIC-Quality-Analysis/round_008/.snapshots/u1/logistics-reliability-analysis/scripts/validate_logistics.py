#!/usr/bin/env python3
"""Validate JSON output for logistics reliability analysis.

Usage: python3 validate_logistics.py <json_file>
"""
import sys
import json

REQUIRED_TOP = ['damage_rates', 'variance_diagnostic', 'action_plan', 'variability_ranking', 'highest_variability_process', 'highest_risk_statement']
DAMAGE_KEYS = ['overall_rate_pct', 'wilson_ci_lower', 'wilson_ci_upper', 'capability_vs_target', 'uses_varying_denominators', 'target_rate_pct']
ACTION_KEYS = ['project_codename', 'milestones_30_days', 'milestones_60_days', 'milestones_90_days', 'checklist']

def validate(data):
    errs = []
    for k in REQUIRED_TOP:
        if k not in data:
            errs.append(f"Missing top-level key: {k}")
    if 'damage_rates' in data:
        for k in DAMAGE_KEYS:
            if k not in data['damage_rates']:
                errs.append(f"Missing in damage_rates: {k}")
    if 'action_plan' in data:
        for k in ACTION_KEYS:
            if k not in data['action_plan']:
                errs.append(f"Missing in action_plan: {k}")
        if isinstance(data['action_plan'].get('checklist'), list) and len(data['action_plan']['checklist']) != 7:
            errs.append("action_plan.checklist must have exactly 7 items")
    if 'variability_ranking' in data:
        if not isinstance(data['variability_ranking'], list):
            errs.append("variability_ranking must be a list")
    return errs

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 validate_logistics.py <json_file>")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        data = json.load(f)
    errs = validate(data)
    if errs:
        print("VALIDATION FAILED:")
        for e in errs:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("VALIDATION PASSED")
        sys.exit(0)