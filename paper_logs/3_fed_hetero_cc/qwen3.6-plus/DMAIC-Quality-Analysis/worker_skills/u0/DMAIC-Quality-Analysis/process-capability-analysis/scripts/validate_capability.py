#!/usr/bin/env python3
"""Validate JSON output against required schema for process capability analysis.

Usage: python3 validate_capability.py <json_file>
"""

import sys
import json


REQUIRED_TOP_KEYS = [
    'variability_ranking',
    'highest_variability_process',
    'highest_risk_statement',
    'monitoring_plan'
]

METRIC_KEYS = ['mean', 'sample_std', 'cv']

RATE_KEYS = [
    'overall_rate_pct',
    'wilson_95_ci_pct',
    'total_failures',
    'total_units_processed',
    'capability_vs_target'
]

MONITORING_KEYS = [
    'process_to_be_monitored',
    'inputs',
    'outputs',
    'key_performance_indicators',
    'frequency_of_monitoring',
    'observation_format',
    'roles',
    'reporting_format',
    'corrective_action_process',
    'benchmarks',
    'checklist',
    'momentum_plan_30_60_90',
    'project_codename'
]


def validate_json(data: dict) -> list:
    """Validate JSON structure. Returns list of errors."""
    errors = []

    for key in REQUIRED_TOP_KEYS:
        if key not in data:
            errors.append(f"Missing required key: {key}")

    if 'variability_ranking' in data:
        if not isinstance(data['variability_ranking'], list):
            errors.append("variability_ranking must be a list")
        else:
            for item in data['variability_ranking']:
                if 'process' not in item or 'cv' not in item:
                    errors.append("variability_ranking items must have 'process' and 'cv'")

    if 'monitoring_plan' in data:
        plan = data['monitoring_plan']
        for key in MONITORING_KEYS:
            if key not in plan:
                errors.append(f"Missing key in monitoring_plan: {key}")

        if 'checklist' in plan:
            if not isinstance(plan['checklist'], list):
                errors.append("checklist must be a list")
            elif len(plan['checklist']) != 7:
                errors.append("checklist must have exactly 7 items")

        if 'momentum_plan_30_60_90' in plan:
            mp = plan['momentum_plan_30_60_90']
            for key in ['30_day', '60_day', '90_day']:
                if key not in mp:
                    errors.append(f"Missing key in momentum_plan: {key}")

    return errors


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 validate_capability.py <json_file>")
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
