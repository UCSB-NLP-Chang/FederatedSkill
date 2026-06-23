#!/usr/bin/env python3
"""Validate SPC metrics JSON against the expected schema.

Run after compute_spc.py to catch schema mismatches before submission.
Exit code 0 = valid, 1 = errors found.
"""
import json
import sys

REQUIRED_TOP_KEYS = [
    "source_file", "filters", "record_counts", "charter_metrics",
    "anova_by_weekday", "imr_summary", "regression_day_index",
    "ttest_vs_target", "capability_against_lsl"
]

FILTERS_KEYS = [
    "primary_date_range", "imr_date_range", "business_days_only",
    "response_metric", "regression_predictor"
]

RECORD_COUNTS_KEYS = [
    "total_records", "primary_window_records",
    "primary_window_business_days", "imr_window_business_days"
]

CHARTER_KEYS = ["baseline_value", "target_value", "current_mean_value"]

ANOVA_KEYS = ["weekday_means", "f_statistic", "p_value", "highest_mean_day", "lowest_mean_day"]

IMR_KEYS = ["points", "center_line", "ucl", "lcl", "mr_bar", "mr_ucl"]

REGRESSION_KEYS = ["slope", "intercept", "r_value", "r_squared", "p_value", "n_observations"]

TTEST_KEYS = ["n", "mean_value", "t_stat", "p_value", "ci95_low", "ci95_high", "decision"]

CAPABILITY_KEYS = ["lsl", "std_dev_sample", "cpk_lower"]

WRONG_KEY_MAP = {
    "response_variable": "response_metric",
    "total_rows": "total_records",
    "primary_window_rows": "primary_window_records",
    "date_range_primary": "primary_date_range",
}


def validate(path):
    errors = []
    with open(path) as f:
        data = json.load(f)

    # Check top-level keys
    for k in REQUIRED_TOP_KEYS:
        if k not in data:
            errors.append(f"Missing top-level key: {k}")

    # Check for common wrong key names at any level
    def check_wrong_keys(obj, prefix=""):
        if isinstance(obj, dict):
            for k in obj:
                if k in WRONG_KEY_MAP:
                    errors.append(f"{prefix}{k} should be {WRONG_KEY_MAP[k]}")

    check_wrong_keys(data)
    check_wrong_keys(data.get("filters", {}), "filters.")
    check_wrong_keys(data.get("record_counts", {}), "record_counts.")

    # Check filters
    filters = data.get("filters", {})
    for k in FILTERS_KEYS:
        if k not in filters:
            errors.append(f"Missing filters key: {k}")

    # Date ranges must be strings, not arrays
    pdr = filters.get("primary_date_range")
    if isinstance(pdr, list):
        errors.append("filters.primary_date_range must be a string like 'YYYY-MM-DD to YYYY-MM-DD (inclusive)', not an array")
    idr = filters.get("imr_date_range")
    if isinstance(idr, list):
        errors.append("filters.imr_date_range must be a string like 'YYYY-MM-DD to YYYY-MM-DD (inclusive)', not an array")

    # Check record_counts
    rc = data.get("record_counts", {})
    for k in RECORD_COUNTS_KEYS:
        if k not in rc:
            errors.append(f"Missing record_counts key: {k}")

    # Check charter_metrics
    for k in CHARTER_KEYS:
        if k not in data.get("charter_metrics", {}):
            errors.append(f"Missing charter_metrics key: {k}")

    # Check anova_by_weekday
    anova = data.get("anova_by_weekday", {})
    for k in ANOVA_KEYS:
        if k not in anova:
            errors.append(f"Missing anova_by_weekday key: {k}")

    # Check imr_summary
    imr = data.get("imr_summary", {})
    for k in IMR_KEYS:
        if k not in imr:
            errors.append(f"Missing imr_summary key: {k}")
    pts = imr.get("points")
    if isinstance(pts, list):
        errors.append("imr_summary.points must be an integer count, not an array of point objects")
    elif pts is not None and not isinstance(pts, (int,)):
        errors.append(f"imr_summary.points must be an integer, got {type(pts).__name__}")

    # Check regression_day_index
    reg = data.get("regression_day_index", {})
    for k in REGRESSION_KEYS:
        if k not in reg:
            errors.append(f"Missing regression_day_index key: {k}")

    # Check ttest_vs_target
    tt = data.get("ttest_vs_target", {})
    for k in TTEST_KEYS:
        if k not in tt:
            errors.append(f"Missing ttest_vs_target key: {k}")
    decision = tt.get("decision")
    if decision and decision not in ("reject_h0", "fail_to_reject_h0"):
        errors.append(f"ttest_vs_target.decision must be 'reject_h0' or 'fail_to_reject_h0', got '{decision}'")

    # Check capability_against_lsl
    for k in CAPABILITY_KEYS:
        if k not in data.get("capability_against_lsl", {}):
            errors.append(f"Missing capability_against_lsl key: {k}")

    # Check p-values are in (0, 1) exclusive
    for section, obj in [
        ("anova_by_weekday", anova),
        ("regression_day_index", reg),
        ("ttest_vs_target", tt),
    ]:
        pv = obj.get("p_value")
        if pv is not None:
            if pv <= 0.0 or pv >= 1.0:
                errors.append(f"{section}.p_value must be in (0,1) exclusive, got {pv}")

    return errors


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 validate_schema.py <json_path>")
        sys.exit(1)
    path = sys.argv[1]
    errors = validate(path)
    if errors:
        print("SCHEMA VALIDATION FAILED:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("Schema validation passed.")
        sys.exit(0)
