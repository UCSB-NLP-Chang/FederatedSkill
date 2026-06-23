#!/usr/bin/env python3
"""Validate JSON output against required schema for pipeline performance analysis.

Usage: python3 validate_output.py <json_file>
"""

import sys
import json


REQUIRED_KEYS = [
    'build_duration',
    'bug_rate',
    'deployment_failures',
    'variability_ranking',
    'highest_variability_process',
    'improvement_plan'
]

METRIC_KEYS = ['mean', 'std', 'cv', 'slope', 't_stat', 'stability']
BUG_RATE_KEYS = ['overall_rate_pct', 'wilson_ci_lower', 'wilson_ci_upper', 'capability_vs_target']


def validate_json(data: dict) -> list:
    """Validate JSON structure. Returns list of errors."""
    errors = []

    # Check top-level keys
    for key in REQUIRED_KEYS:
        if key not in data:
            errors.append(f"Missing required key: {key}")

    # Check metric keys
    for metric in ['build_duration', 'deployment_failures']:
        if metric in data:
            for key in METRIC_KEYS:
                if key not in data[metric]:
                    errors.append(f"Missing key in {metric}: {key}")

    # Check bug_rate keys
    if 'bug_rate' in data:
        for key in BUG_RATE_KEYS:
            if key not in data['bug_rate']:
                errors.append(f"Missing key in bug_rate: {key}")

    # Check variability_ranking is list
    if 'variability_ranking' in data:
        if not isinstance(data['variability_ranking'], list):
            errors.append("variability_ranking must be a list")

    # Check improvement_plan
    if 'improvement_plan' in data:
        plan = data['improvement_plan']
        for key in ['project_codename', 'milestones_30_days', 'milestones_60_days', 'milestones_90_days']:
            if key not in plan:
                errors.append(f"Missing key in improvement_plan: {key}")

    return errors


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 validate_output.py <json_file>")
        sys.exit(1)

    json_path = sys.argv[1]

    with open(json_path, 'r') as f:
        data = json.load(f)

    errors = validate_json(data)

    if errors:
        print("VALIDATION FAILED:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("VALIDATION PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
