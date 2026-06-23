#!/usr/bin/env python3
"""Compute OncoCooler dispatch analysis and generate JSON/MD outputs."""
import csv
import json
import sys
import os

def main():
    base_dir = sys.argv[1] if len(sys.argv) > 1 else "/root"
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 10000.0

    # Load program catalog
    with open(os.path.join(base_dir, "program_catalog.json")) as f:
        catalog = json.load(f)

    programs = {}
    alias_map = {}
    for sg in catalog.get("service_groups", []):
        for p in sg.get("programs", []):
            if p.get("review_flag") == "review":
                code = p["program_code"]
                programs[code] = p
                # Map known_labels for payment matching
                for label in p.get("known_labels", []):
                    alias_map[label] = code
                # Also map program_name
                alias_map[p["program_name"]] = code

    # Load cooler costs
    cooler_costs = {}
    with open(os.path.join(base_dir, "cooler_cost.csv")) as f:
        for row in csv.DictReader(f):
            cooler_costs[row["cooler_type"]] = float(row["cooler_cost_usd"])

    # Load contract payments
    payments = {}
    with open(os.path.join(base_dir, "contract_payment.csv")) as f:
        for row in csv.DictReader(f):
            label = row["program_label"]
            if label in alias_map:
                code = alias_map[label]
                payments[code] = float(row["payment_per_dispatch_per_site_usd"])

    # Load site overrides (highest approved version_no per program_code)
    sites = {}
    with open(os.path.join(base_dir, "site_overrides.csv")) as f:
        for row in csv.DictReader(f):
            code = row["program_code"]
            if code in programs and row["approval_state"] == "approved":
                version = int(row["version_no"])
                if code not in sites or version > sites[code]["version"]:
                    sites[code] = {"version": version, "active_sites": int(row["active_sites"])}

    # Constants
    DISPATCHES_10 = 36
    DISPATCHES_20 = 18
    DAYS_PER_YEAR = 360

    results = []
    for code in sorted(programs.keys()):
        p = programs[code]
        # Resolve active sites: override wins if approved version exists
        if code in sites:
            site_count = sites[code]["active_sites"]
        else:
            site_count = p["default_active_sites"]
        
        cost_per_1000 = p["acquisition_cost_per_1000_units_usd"]
        units_per_day = p["units_per_day"]
        cooler_type = p["cooler_type"]
        cooler_cost = cooler_costs[cooler_type]
        payment = payments[code]

        # Annual drug cost (identical for both)
        annual_drug = (cost_per_1000 / 1000) * units_per_day * DAYS_PER_YEAR * site_count
        
        # Cooler costs
        cooler_10 = cooler_cost * DISPATCHES_10 * site_count
        cooler_20 = cooler_cost * DISPATCHES_20 * site_count
        
        # Revenue
        rev_10 = payment * DISPATCHES_10 * site_count
        rev_20 = payment * DISPATCHES_20 * site_count
        
        # Margins
        margin_10 = rev_10 - annual_drug - cooler_10
        margin_20 = rev_20 - annual_drug - cooler_20
        diff = margin_20 - margin_10

        results.append({
            "program_code": code,
            "program_name": p["program_name"],
            "active_sites": site_count,
            "acquisition_cost_per_1000_units_usd": round(cost_per_1000, 2),
            "units_per_day": units_per_day,
            "cooler_type": cooler_type,
            "cooler_cost_usd": round(cooler_cost, 2),
            "payment_per_dispatch_per_site_usd": round(payment, 2),
            "annual_drug_cost_10_day_usd": round(annual_drug, 2),
            "annual_drug_cost_20_day_usd": round(annual_drug, 2),
            "annual_cooler_cost_10_day_usd": round(cooler_10, 2),
            "annual_cooler_cost_20_day_usd": round(cooler_20, 2),
            "annual_revenue_10_day_usd": round(rev_10, 2),
            "annual_revenue_20_day_usd": round(rev_20, 2),
            "annual_margin_10_day_usd": round(margin_10, 2),
            "annual_margin_20_day_usd": round(margin_20, 2),
            "annual_margin_difference_20_minus_10_usd": round(diff, 2)
        })

    total_margin_10 = round(sum(r["annual_margin_10_day_usd"] for r in results), 2)
    total_margin_20 = round(sum(r["annual_margin_20_day_usd"] for r in results), 2)
    total_diff = round(total_margin_20 - total_margin_10, 2)
    abs_total_diff = round(abs(total_diff), 2)

    decision = "move_to_20_day" if abs_total_diff < threshold else "keep_10_day"

    output = {
        "assumptions": {
            "dispatches_per_year_10_day": DISPATCHES_10,
            "dispatches_per_year_20_day": DISPATCHES_20,
            "days_per_dispatch_10_day": 10,
            "days_per_dispatch_20_day": 20,
            "switch_threshold_usd": threshold,
            "site_override_rule": "highest approved version_no per program_code, else default_active_sites"
        },
        "programs": results,
        "totals": {
            "annual_margin_10_day_usd": total_margin_10,
            "annual_margin_20_day_usd": total_margin_20,
            "absolute_difference_usd": abs_total_diff,
            "decision": decision
        }
    }

    json_path = os.path.join(base_dir, "oncocooler_analysis.json")
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)

    summary_path = os.path.join(base_dir, "oncocooler_summary.md")
    with open(summary_path, "w") as f:
        f.write("# Oncology Cooler Dispatch Analysis Summary\n\n")
        f.write(f"Total 10-day annual margin: ${total_margin_10:,.2f} USD\n")
        f.write(f"Total 20-day annual margin: ${total_margin_20:,.2f} USD\n")
        f.write(f"Absolute margin difference (20-day minus 10-day): ${abs_total_diff:,.2f} USD\n")
        f.write(f"Decision: `{decision}`\n")

    print(f"Generated {json_path} and {summary_path}")

if __name__ == "__main__":
    main()
