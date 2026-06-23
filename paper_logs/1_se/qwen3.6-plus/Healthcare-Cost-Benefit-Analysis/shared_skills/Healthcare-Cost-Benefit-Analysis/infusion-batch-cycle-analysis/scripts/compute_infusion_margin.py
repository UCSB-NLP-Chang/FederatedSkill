#!/usr/bin/env python3
import argparse
import csv
import json
import sys

def main():
    parser = argparse.ArgumentParser(description="Compute infusion batch delivery cycle margin analysis.")
    parser.add_argument("--catalog", required=True, help="Path to therapy_catalog.json")
    parser.add_argument("--bag-cost", required=True, help="Path to bag_supply_cost.csv")
    parser.add_argument("--payment", required=True, help="Path to delivery_payment.csv")
    parser.add_argument("--overrides", required=True, help="Path to patient_overrides.csv")
    parser.add_argument("--threshold", type=float, default=15000.0, help="Decision threshold USD")
    parser.add_argument("--out-json", default="infusion_batch_analysis.json")
    parser.add_argument("--out-md", default="infusion_batch_summary.md")
    args = parser.parse_args()

    # Load catalog
    with open(args.catalog) as f:
        catalog = json.load(f)

    therapies = {}
    alias_to_code = {}
    for sl in catalog.get("service_lines", []):
        for t in sl.get("therapies", []):
            if t.get("include_in_review", False):
                code = t["therapy_code"]
                therapies[code] = {
                    "name": t["therapy_name"],
                    "drug_cost_per_1000": t["drug_cost_per_1000_mg_usd"],
                    "dose_mg_per_day": t["dose_mg_per_day"],
                    "bag_size_ml": t["bag_size_ml"]
                }
                for alias in t.get("aliases", []):
                    alias_to_code[alias] = code

    # Load bag costs
    bag_costs = {}
    with open(args.bag_cost, newline='') as f:
        for row in csv.DictReader(f):
            bag_costs[int(row["bag_size_ml"])] = float(row["bag_supply_cost_usd"])

    # Load payments
    payments = {}
    with open(args.payment, newline='') as f:
        for row in csv.DictReader(f):
            label = row["therapy_label"]
            if label in alias_to_code:
                payments[alias_to_code[label]] = float(row["payment_per_delivery_per_patient_usd"])

    # Load overrides
    overrides = {}
    with open(args.overrides, newline='') as f:
        for row in csv.DictReader(f):
            code = row["therapy_code"]
            if row["status"] == "approved":
                rev = int(row["revision"])
                if code not in overrides or rev > overrides[code]["rev"]:
                    overrides[code] = {"rev": rev, "patients": int(row["active_patients"])}

    DEL_7 = 52
    DEL_14 = 26
    DAYS_YEAR = 364

    results = []
    total_m7 = 0.0
    total_m14 = 0.0

    for code, t in therapies.items():
        patients = overrides.get(code, {}).get("patients", 0)
        bag_cost = bag_costs.get(t["bag_size_ml"], 0.0)
        payment = payments.get(code, 0.0)

        drug_annual = (t["drug_cost_per_1000"] / 1000.0) * t["dose_mg_per_day"] * DAYS_YEAR * patients
        supply_7 = bag_cost * DEL_7 * patients
        supply_14 = bag_cost * DEL_14 * patients
        rev_7 = payment * DEL_7 * patients
        rev_14 = payment * DEL_14 * patients

        m7 = rev_7 - drug_annual - supply_7
        m14 = rev_14 - drug_annual - supply_14
        diff = m14 - m7

        total_m7 += m7
        total_m14 += m14

        results.append({
            "therapy_code": code,
            "therapy_name": t["name"],
            "active_patients": patients,
            "drug_cost_per_1000_mg_usd": t["drug_cost_per_1000"],
            "dose_mg_per_day": t["dose_mg_per_day"],
            "bag_size_ml": t["bag_size_ml"],
            "bag_supply_cost_usd": bag_cost,
            "payment_per_delivery_per_patient_usd": payment,
            "annual_drug_cost_7_day_usd": round(drug_annual, 2),
            "annual_drug_cost_14_day_usd": round(drug_annual, 2),
            "annual_supply_cost_7_day_usd": round(supply_7, 2),
            "annual_supply_cost_14_day_usd": round(supply_14, 2),
            "annual_revenue_7_day_usd": round(rev_7, 2),
            "annual_revenue_14_day_usd": round(rev_14, 2),
            "annual_margin_7_day_usd": round(m7, 2),
            "annual_margin_14_day_usd": round(m14, 2),
            "annual_margin_difference_14_minus_7_usd": round(diff, 2)
        })

    abs_diff = abs(total_m14 - total_m7)
    if abs_diff > args.threshold:
        decision = "move_to_14_day" if total_m14 > total_m7 else "keep_7_day"
    else:
        decision = "keep_7_day"

    out = {
        "assumptions": {
            "deliveries_per_year_7_day": DEL_7,
            "deliveries_per_year_14_day": DEL_14,
            "days_per_delivery_7_day": 7,
            "days_per_delivery_14_day": 14,
            "switch_threshold_usd": args.threshold,
            "patient_override_rule": "highest approved revision per therapy_code"
        },
        "therapies": results,
        "totals": {
            "total_annual_margin_7_day_usd": round(total_m7, 2),
            "total_annual_margin_14_day_usd": round(total_m14, 2),
            "absolute_difference_usd": round(abs_diff, 2),
            "decision": decision
        }
    }

    with open(args.out_json, 'w') as f:
        json.dump(out, f, indent=2)

    md = [
        "# Infusion Batch Delivery Analysis",
        "",
        f"**7-day total annual margin:** ${total_m7:,.2f}",
        f"**14-day total annual margin:** ${total_m14:,.2f}",
        f"**Absolute margin difference:** ${abs_diff:,.2f}",
        "",
        f"**Decision:** `{decision}`"
    ]
    with open(args.out_md, 'w') as f:
        f.write("\n".join(md) + "\n")

    print(f"Done. abs_diff={abs_diff}, decision={decision}")

if __name__ == "__main__":
    main()
