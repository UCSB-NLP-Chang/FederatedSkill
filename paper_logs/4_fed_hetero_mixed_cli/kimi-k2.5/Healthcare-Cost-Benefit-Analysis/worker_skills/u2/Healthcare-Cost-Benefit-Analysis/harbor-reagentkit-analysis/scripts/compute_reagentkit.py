#!/usr/bin/env python3
"""Compute Harbor Reagent Kit analysis and generate JSON/MD outputs."""
import csv
import json
import sys
import os
from datetime import datetime

def main():
    base_dir = sys.argv[1] if len(sys.argv) > 1 else "/root"
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 7000.0

    # Load assay manifest
    with open(os.path.join(base_dir, "assay_manifest.json")) as f:
        manifest = json.load(f)

    assays = {}
    alias_map = {}
    for region in manifest.get("regions", []):
        for assay in region.get("assays", []):
            if assay.get("in_scope", False):
                code = assay["assay_id"]
                assays[code] = assay
                # Map aliases for billing resolution
                alias_map[assay["assay_name"]] = code
                for alias in assay.get("aliases", []):
                    alias_map[alias] = code

    # Load carrier costs
    carrier_costs = {}
    with open(os.path.join(base_dir, "carrier_cost.csv")) as f:
        for row in csv.DictReader(f):
            carrier_costs[row["carrier_type"]] = float(row["carrier_cost_usd"])

    # Load billing data (latest active effective_month per assay)
    payments = {}
    billing_rows = []
    with open(os.path.join(base_dir, "billing.csv")) as f:
        for row in csv.DictReader(f):
            label = row["assay_label"]
            if label in alias_map:
                code = alias_map[label]
                is_active = row.get("is_active", "true").lower() == "true"
                if is_active:
                    effective = datetime.strptime(row["effective_month"], "%Y-%m")
                    billing_rows.append((code, effective, float(row["payment_per_run_per_lab_usd"])))
    
    # Select latest effective month per assay
    latest_payment = {}
    for code, effective, payment in billing_rows:
        if code not in latest_payment or effective > latest_payment[code][0]:
            latest_payment[code] = (effective, payment)
    for code, (_, payment) in latest_payment.items():
        payments[code] = payment

    # Load lab overrides (highest approved revision per assay_id)
    labs = {}
    with open(os.path.join(base_dir, "lab_overrides.csv")) as f:
        for row in csv.DictReader(f):
            code = row["assay_id"]
            if code in assays and row["status"] == "approved":
                rev = int(row["revision"])
                if code not in labs or rev > labs[code]["revision"]:
                    labs[code] = {"revision": rev, "active_labs": int(row["active_labs"])}

    # Constants
    RUNS_SMALL = 24
    RUNS_BULK = 12

    results = []
    for code in sorted(assays.keys()):
        assay = assays[code]
        
        # Resolve active labs
        if code in labs:
            active_labs = labs[code]["active_labs"]
        else:
            active_labs = assay["default_active_labs"]
        
        price_per_1000 = assay["reagent_price_per_1000_tests_usd"]
        carrier_type = assay["carrier_type"]
        carrier_cost = carrier_costs[carrier_type]
        payment = payments[code]
        
        tests_small = assay["tests_per_lab_per_run_small"]
        tests_bulk = assay["tests_per_lab_per_run_bulk"]
        
        # Annual reagent cost (identical for both due to balanced test volumes)
        annual_reagent = (tests_small * RUNS_SMALL * active_labs / 1000) * price_per_1000
        
        # Carrier costs
        carrier_small = carrier_cost * RUNS_SMALL * active_labs
        carrier_bulk = carrier_cost * RUNS_BULK * active_labs
        
        # Revenue
        rev_small = payment * RUNS_SMALL * active_labs
        rev_bulk = payment * RUNS_BULK * active_labs
        
        # Margins
        margin_small = rev_small - annual_reagent - carrier_small
        margin_bulk = rev_bulk - annual_reagent - carrier_bulk
        diff = margin_bulk - margin_small
        
        results.append({
            "assay_id": code,
            "assay_name": assay["assay_name"],
            "active_labs": active_labs,
            "reagent_price_per_1000_tests_usd": round(price_per_1000, 2),
            "carrier_type": carrier_type,
            "carrier_cost_usd": round(carrier_cost, 2),
            "payment_per_run_per_lab_usd": round(payment, 2),
            "tests_per_lab_per_run_small": tests_small,
            "tests_per_lab_per_run_bulk": tests_bulk,
            "annual_reagent_cost_small_kit_usd": round(annual_reagent, 2),
            "annual_reagent_cost_bulk_kit_usd": round(annual_reagent, 2),
            "annual_carrier_cost_small_kit_usd": round(carrier_small, 2),
            "annual_carrier_cost_bulk_kit_usd": round(carrier_bulk, 2),
            "annual_revenue_small_kit_usd": round(rev_small, 2),
            "annual_revenue_bulk_kit_usd": round(rev_bulk, 2),
            "annual_margin_small_kit_usd": round(margin_small, 2),
            "annual_margin_bulk_kit_usd": round(margin_bulk, 2),
            "annual_margin_difference_bulk_minus_small_usd": round(diff, 2)
        })

    total_margin_small = round(sum(r["annual_margin_small_kit_usd"] for r in results), 2)
    total_margin_bulk = round(sum(r["annual_margin_bulk_kit_usd"] for r in results), 2)
    total_diff = round(total_margin_bulk - total_margin_small, 2)
    abs_total_diff = round(abs(total_diff), 2)
    
    decision = "adopt_bulk_kit" if abs_total_diff < threshold else "keep_small_kit"

    output = {
        "metadata": {
            "request_id": "KIT-2026-11",
            "generated_for": "Regional Pathology Ops"
        },
        "analysis": {
            "assumptions": {
                "runs_per_year_small_kit": RUNS_SMALL,
                "runs_per_year_bulk_kit": RUNS_BULK,
                "switch_threshold_usd": threshold,
                "lab_override_rule": "highest approved revision per assay_id, else default_active_labs",
                "billing_rule": "latest active effective_month per assay (matched by assay_name or aliases)"
            },
            "assays": results,
            "totals": {
                "total_annual_margin_small_kit_usd": total_margin_small,
                "total_annual_margin_bulk_kit_usd": total_margin_bulk,
                "total_annual_margin_difference_bulk_minus_small_usd": total_diff,
                "absolute_total_margin_difference_usd": abs_total_diff
            },
            "recommendation": {
                "decision": decision,
                "justification": f"The absolute total margin difference (${abs_total_diff:,.2f}) is {'below' if abs_total_diff < threshold else 'above or equal to'} the threshold of ${threshold:,.2f}, making the bulk-kit policy {'financially viable' if decision == 'adopt_bulk_kit' else 'not recommended'}."
            }
        }
    }

    json_path = os.path.join(base_dir, "reagent_policy_report.json")
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)

    summary_path = os.path.join(base_dir, "reagent_policy_summary.md")
    with open(summary_path, "w") as f:
        f.write("# Reagent Policy Analysis Summary\n\n")
        f.write(f"**Total Annual Margin - Small-Kit Policy:** ${total_margin_small:,.2f} USD\n")
        f.write(f"**Total Annual Margin - Bulk-Kit Policy:** ${total_margin_bulk:,.2f} USD\n")
        f.write(f"**Absolute Margin Difference:** ${abs_total_diff:,.2f} USD\n\n")
        f.write(f"Since the absolute difference (${abs_total_diff:,.2f}) is {'below' if abs_total_diff < threshold else 'above or equal to'} the ${threshold:,.2f} threshold, the recommended decision is to **{decision}**.\n")

    print(f"Generated {json_path} and {summary_path}")

if __name__ == "__main__":
    main()
