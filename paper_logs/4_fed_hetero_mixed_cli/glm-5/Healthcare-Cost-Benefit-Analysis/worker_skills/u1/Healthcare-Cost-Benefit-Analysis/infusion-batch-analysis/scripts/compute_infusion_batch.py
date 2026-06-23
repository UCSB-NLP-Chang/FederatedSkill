#!/usr/bin/env python3
"""Compute Infusion Batch analysis and generate JSON/MD outputs."""
import csv
import json
import sys
import os

def main():
    base_dir = sys.argv[1] if len(sys.argv) > 1 else "/root"
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 15000.0

    # Load therapy catalog
    with open(os.path.join(base_dir, "therapy_catalog.json")) as f:
        catalog = json.load(f)

    therapies = {}
    alias_map = {}
    for sl in catalog["service_lines"]:
        for t in sl["therapies"]:
            if t.get("include_in_review", False):
                code = t["therapy_code"]
                therapies[code] = t
                alias_map[t["therapy_name"]] = code
                for alias in t.get("aliases", []):
                    alias_map[alias] = code

    # Load bag supply costs
    bag_costs = {}
    with open(os.path.join(base_dir, "bag_supply_cost.csv")) as f:
        for row in csv.DictReader(f):
            bag_costs[int(row["bag_size_ml"])] = float(row["bag_supply_cost_usd"])

    # Load delivery payments
    payments = {}
    with open(os.path.join(base_dir, "delivery_payment.csv")) as f:
        for row in csv.DictReader(f):
            label = row["therapy_label"]
            if label in alias_map:
                payments[alias_map[label]] = float(row["payment_per_delivery_per_patient_usd"])

    # Load patient overrides (highest approved revision per therapy_code)
    patients = {}
    with open(os.path.join(base_dir, "patient_overrides.csv")) as f:
        for row in csv.DictReader(f):
            code = row["therapy_code"]
            if code in therapies and row["status"] == "approved":
                rev = int(row["revision"])
                if code not in patients or rev > patients[code]["revision"]:
                    patients[code] = {"revision": rev, "active_patients": int(row["active_patients"])}

    # Constants
    DELIVERIES_7 = 52
    DELIVERIES_14 = 26
    DAYS_PER_YEAR = 364

    results = []
    for code in sorted(therapies.keys()):
        if code not in patients:
            continue

        t = therapies[code]
        p_count = patients[code]["active_patients"]
        drug_cost_per_1000 = t["drug_cost_per_1000_mg_usd"]
        dose = t["dose_mg_per_day"]
        bag_size = t["bag_size_ml"]
        bag_cost = bag_costs[bag_size]
        payment = payments[code]

        # Annual drug cost (identical for both)
        annual_drug = (drug_cost_per_1000 / 1000) * dose * DAYS_PER_YEAR * p_count

        # Supply costs
        supply_7 = bag_cost * DELIVERIES_7 * p_count
        supply_14 = bag_cost * DELIVERIES_14 * p_count

        # Revenue
        rev_7 = payment * DELIVERIES_7 * p_count
        rev_14 = payment * DELIVERIES_14 * p_count

        # Margins
        margin_7 = rev_7 - annual_drug - supply_7
        margin_14 = rev_14 - annual_drug - supply_14
        diff = margin_14 - margin_7

        results.append({
            "therapy_code": code,
            "therapy_name": t["therapy_name"],
            "active_patients": p_count,
            "drug_cost_per_1000_mg_usd": drug_cost_per_1000,
            "dose_mg_per_day": dose,
            "bag_size_ml": bag_size,
            "bag_supply_cost_usd": bag_cost,
            "payment_per_delivery_per_patient_usd": payment,
            "annual_drug_cost_7_day_usd": annual_drug,
            "annual_drug_cost_14_day_usd": annual_drug,
            "annual_supply_cost_7_day_usd": supply_7,
            "annual_supply_cost_14_day_usd": supply_14,
            "annual_revenue_7_day_usd": rev_7,
            "annual_revenue_14_day_usd": rev_14,
            "annual_margin_7_day_usd": margin_7,
            "annual_margin_14_day_usd": margin_14,
            "annual_margin_difference_14_minus_7_usd": diff
        })

    total_margin_7 = sum(r["annual_margin_7_day_usd"] for r in results)
    total_margin_14 = sum(r["annual_margin_14_day_usd"] for r in results)
    total_diff = total_margin_14 - total_margin_7
    abs_total_diff = abs(total_diff)

    # Library pattern: convert_to_X / keep_X
    decision = "convert_to_14_day" if abs_total_diff < threshold else "keep_7_day"

    output = {
        "assumptions": {
            "deliveries_per_year_7_day": DELIVERIES_7,
            "deliveries_per_year_14_day": DELIVERIES_14,
            "days_per_delivery_7_day": 7,
            "days_per_delivery_14_day": 14,
            "switch_threshold_usd": threshold,
            "patient_override_rule": "highest approved revision per therapy_code"
        },
        "therapies": results,
        "totals": {
            "annual_margin_7_day_usd": round(total_margin_7, 2),
            "annual_margin_14_day_usd": round(total_margin_14, 2),
            "absolute_difference_usd": round(abs_total_diff, 2),
            "decision": decision
        }
    }

    json_path = os.path.join(base_dir, "infusion_batch_analysis.json")
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)

    summary_path = os.path.join(base_dir, "infusion_batch_summary.md")
    with open(summary_path, "w") as f:
        f.write("# Infusion Batch Analysis Summary\n\n")
        f.write(f"Total 7-day annual margin: ${round(total_margin_7, 2):,.2f} USD\n")
        f.write(f"Total 14-day annual margin: ${round(total_margin_14, 2):,.2f} USD\n")
        f.write(f"Absolute margin difference (14-day minus 7-day): ${round(abs_total_diff, 2):,.2f} USD\n")
        f.write(f"Decision: `{decision}`\n")

    print(f"Generated {json_path} and {summary_path}")

if __name__ == "__main__":
    main()