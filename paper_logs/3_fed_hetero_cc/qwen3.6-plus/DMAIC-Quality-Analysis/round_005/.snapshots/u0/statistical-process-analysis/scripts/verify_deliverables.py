#!/usr/bin/env python3
"""Verify final deliverables meet task requirements.

Run after generating metrics JSON and brief Markdown to catch common
verifier failures before submission.

Exit code 0 = valid, 1 = errors found.
"""
import argparse
import json
import re
import sys


def verify_metrics(path):
    """Check metrics JSON structure."""
    errors = []
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception as e:
        errors.append(f"Cannot parse JSON: {e}")
        return errors

    # Check p-values are reasonable (not rounded to 0 or 1)
    sections = [
        ("anova_by_weekday", data.get("anova_by_weekday", {})),
        ("regression_day_index", data.get("regression_day_index", {})),
        ("ttest_vs_target", data.get("ttest_vs_target", {})),
    ]
    for name, section in sections:
        p = section.get("p_value")
        if p is not None:
            if p <= 0 or p >= 1:
                errors.append(f"{name}.p_value ({p}) must be in (0,1) exclusive")
            # Only flag as rounding issue if exactly 0, not legitimate small values like 1e-11
            if p == 0.0:
                errors.append(f"{name}.p_value is exactly 0.0; use full precision from scipy")

    # Check decision value
    decision = data.get("ttest_vs_target", {}).get("decision")
    if decision and decision not in ("reject_h0", "fail_to_reject_h0"):
        errors.append(f"ttest_vs_target.decision must be 'reject_h0' or 'fail_to_reject_h0', got '{decision}'")

    return errors


def verify_brief(path):
    """Check brief Markdown has required sections."""
    errors = []
    try:
        with open(path) as f:
            content = f.read()
    except Exception as e:
        errors.append(f"Cannot read brief: {e}")
        return errors

    # Required sections (case-insensitive check)
    required_sections = [
        ("Project Charter", r"##?\s*Project\s+Charter"),
        ("Statistical Analysis", r"##?\s*Statistical\s+Analysis"),
        ("A3 Summary", r"##?\s*A3\s+Summary"),
        ("Timeline", r"##?\s*(Timeline|Next\s+Steps)"),
    ]

    for name, pattern in required_sections:
        if not re.search(pattern, content, re.IGNORECASE):
            errors.append(f"Missing required section: {name}")

    # Check for common formatting issues
    if re.search(r"p\s*=\s*0\.000\b", content):
        errors.append("p-value appears rounded to 0.000; use full precision from JSON")

    return errors


def main():
    p = argparse.ArgumentParser(description="Verify deliverables meet requirements")
    p.add_argument("--metrics", required=True, help="Path to metrics JSON")
    p.add_argument("--brief", required=True, help="Path to brief Markdown")
    args = p.parse_args()

    errors = []
    errors.extend(verify_metrics(args.metrics))
    errors.extend(verify_brief(args.brief))

    if errors:
        print("DELIVERABLE VERIFICATION FAILED:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("Deliverable verification passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()