#!/usr/bin/env python3
"""Compute SyncPack cycle analysis and generate JSON/MD outputs."""
import csv
import json
import sys
import os

def main():
    base_dir = sys.argv[1] if len(sys.argv) > 1 else "/root"
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 9000.0

    ingredients = {}
    with open(os.path.join(base_dir, "ingredient_cost.csv")) as f:
        for row in csv.DictReader(f):
            ingredients[row["medication"]] = {
                "price_per_1000": float(row["price_per_1000_capsules_usd"]),
                "blister_card_count": int(row["blister_card_count"])
            }

    cards = {}
    with open(os.path.join(base_dir, "card_cost.csv")) as f:
        for row in csv.DictReader(f):
            cards[int(row["blister_card_count"])] = float(row["card_cost_usd"])

    reimb = {}
    with open(os.path.join(base_dir, "reimbursement.csv")) as f:
        for row in csv.DictReader(f):
            reimb[row["medication"]] = float(row["reimbursement_per_cycle_180_patients_usd"])

    PATIENTS = 180
    FILLS_28 = 12
    FILLS_56 = 6
    CAPS_28 = 56
    CAPS_56 = 112

    medications = []
    for med_name in sorted(ingredients.keys()):
        ing = ingredients[med_name]
        price = ing["price_per_1000"]
        bc = ing["blister_card_count"]
        card_cost = cards[bc]
        rev = reimb[med_name]

        annual_drug = (CAPS_28 / 1000) * price * FILLS_28 * PATIENTS
        annual_pkg_28 = card_cost * FILLS_28 * PATIENTS
        annual_pkg_56 = card_cost * FILLS_56 * PATIENTS
        annual_rev_28 = rev * FILLS_28
        annual_rev_56 = rev * FILLS_56

        margin_28 = annual_rev_28 - annual_drug - annual_pkg_28
        margin_56 = annual_rev_56 - annual_drug - annual_pkg_56
        diff = margin_56 - margin_28

        medications.append({
            "medication": med_name,
            "price_per_1000_capsules_usd": round(price, 2),
            "blister_card_count": bc,
            "card_cost_usd": round(card_cost, 2),
            "reimbursement_per_cycle_180_patients_usd": round(rev, 2),
            "annual_drug_cost_28_day_usd": round(annual_drug, 2),
            "annual_drug_cost_56_day_usd": round(annual_drug, 2),
            "annual_packaging_cost_28_day_usd": round(annual_pkg_28, 2),
            "annual_packaging_cost_56_day_usd": round(annual_pkg_56, 2),
            "annual_reimbursement_28_day_usd": round(annual_rev_28, 2),
            "annual_reimbursement_56_day_usd": round(annual_rev_56, 2),
            "annual_margin_28_day_usd": round(margin_28, 2),
            "annual_margin_56_day_usd": round(margin_56, 2),
            "annual_margin_difference_56_minus_28_usd": round(diff, 2)
        })

    total_margin_28 = round(sum(m["annual_margin_28_day_usd"] for m in medications), 2)
    total_margin_56 = round(sum(m["annual_margin_56_day_usd"] for m in medications), 2)
    total_diff = round(total_margin_56 - total_margin_28, 2)
    abs_total_diff = round(abs(total_diff), 2)

    decision = "convert_to_56_day" if abs_total_diff < threshold else "keep_28_day"

    result = {
        "assumptions": {
            "patients_per_medication": PATIENTS,
            "fills_per_year_28_day": FILLS_28,
            "fills_per_year_56_day": FILLS_56,
            "capsules_per_fill_28_day": CAPS_28,
            "capsules_per_fill_56_day": CAPS_56,
            "switch_threshold_usd": threshold
        },
        "medications": medications,
        "totals": {
            "annual_margin_28_day_usd": total_margin_28,
            "annual_margin_56_day_usd": total_margin_56,
            "absolute_difference_usd": abs_total_diff,
            "decision": decision
        }
    }

    json_path = os.path.join(base_dir, "syncpack_analysis.json")
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2)

    summary_path = os.path.join(base_dir, "syncpack_summary.md")
    with open(summary_path, "w") as f:
        f.write("## SyncPack Cycle Analysis Summary\n\n")
        f.write(f"Total annual margin at 28-day cycle: **${total_margin_28:,.2f}**\n")
        f.write(f"Total annual margin at 56-day cycle: **${total_margin_56:,.2f}**\n")
        f.write(f"Absolute difference (56-day vs 28-day): **${abs_total_diff:,.2f}**\n\n")
        f.write(f"The absolute difference of ${abs_total_diff:,.2f} is {'below' if abs_total_diff < threshold else 'above or equal to'} the ${threshold:,.2f} threshold.\n\n")
        f.write(f"**Decision: `{decision}`** — {'move all medications to 56-day card cycles.' if decision == 'convert_to_56_day' else 'maintain current 28-day card cycles.'}\n")

    print(f"Generated {json_path} and {summary_path}")

if __name__ == "__main__":
    main()
