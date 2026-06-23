#!/usr/bin/env python3
import argparse
import csv
import json
import os

def main():
    parser = argparse.ArgumentParser(description="Compute 30-day vs 90-day refill cycle margin analysis.")
    parser.add_argument("--acquisition", required=True, help="Path to acquisition_cost.csv")
    parser.add_argument("--packaging", required=True, help="Path to packaging_cost.csv")
    parser.add_argument("--reimbursement", required=True, help="Path to reimbursement.csv")
    parser.add_argument("--threshold", type=float, default=12000.0, help="Decision threshold in USD")
    parser.add_argument("--output-dir", default=".", help="Directory for output files")
    args = parser.parse_args()

    # Constants
    PATIENTS = 240
    FILLS_30 = 12
    FILLS_90 = 4
    DOSES_30 = 60
    DOSES_90 = 180

    # Read acquisition (keyed by therapy)
    acq_data = {}
    with open(args.acquisition, newline='') as f:
        for row in csv.DictReader(f):
            acq_data[row['therapy']] = row

    # Read packaging (keyed by canister_size_units)
    pkg_data = {}
    with open(args.packaging, newline='') as f:
        for row in csv.DictReader(f):
            pkg_data[row['canister_size_units']] = row

    # Read reimbursement (keyed by therapy)
    reimb_data = {}
    with open(args.reimbursement, newline='') as f:
        for row in csv.DictReader(f):
            reimb_data[row['therapy']] = row

    therapies = sorted(acq_data.keys())
    results = []
    total_margin_30 = 0.0
    total_margin_90 = 0.0

    for t in therapies:
        acq = acq_data[t]
        reimb = reimb_data.get(t, {})

        price_per_1000 = float(acq['price_per_1000_doses_usd'])
        canister_size = int(acq['canister_size_units'])
        pkg_cost = float(pkg_data[str(canister_size)]['packaging_cost_usd'])
        reimb_per_fill = float(reimb.get('reimbursement_per_fill_240_patients_usd', 0))

        # Annual drug cost (identical for both models)
        annual_doses = PATIENTS * FILLS_30 * DOSES_30
        annual_drug_cost = (annual_doses / 1000.0) * price_per_1000

        # Packaging costs: packaging_cost * fills_per_year * patients
        pkg_30 = pkg_cost * FILLS_30 * PATIENTS
        pkg_90 = pkg_cost * FILLS_90 * PATIENTS

        # Reimbursement
        reimb_30 = reimb_per_fill * FILLS_30
        reimb_90 = reimb_per_fill * FILLS_90

        # Margins
        margin_30 = reimb_30 - (annual_drug_cost + pkg_30)
        margin_90 = reimb_90 - (annual_drug_cost + pkg_90)
        diff = margin_90 - margin_30

        total_margin_30 += margin_30
        total_margin_90 += margin_90

        results.append({
            "therapy": t,
            "price_per_1000_doses_usd": price_per_1000,
            "canister_size_units": canister_size,
            "packaging_cost_usd": pkg_cost,
            "reimbursement_per_fill_240_patients_usd": reimb_per_fill,
            "annual_drug_cost_30_day_usd": annual_drug_cost,
            "annual_drug_cost_90_day_usd": annual_drug_cost,
            "annual_packaging_cost_30_day_usd": pkg_30,
            "annual_packaging_cost_90_day_usd": pkg_90,
            "annual_reimbursement_30_day_usd": reimb_30,
            "annual_reimbursement_90_day_usd": reimb_90,
            "annual_margin_30_day_usd": margin_30,
            "annual_margin_90_day_usd": margin_90,
            "annual_margin_difference_90_minus_30_usd": diff
        })

    abs_diff = abs(total_margin_90 - total_margin_30)
    decision = "switch_to_90_day" if total_margin_90 > total_margin_30 and abs_diff > args.threshold else "keep_30_day"

    # Write JSON
    output_json = {
        "assumptions": {
            "patients_per_therapy": PATIENTS,
            "fills_per_year_30_day": FILLS_30,
            "fills_per_year_90_day": FILLS_90,
            "doses_per_fill_30_day": DOSES_30,
            "doses_per_fill_90_day": DOSES_90,
            "switch_threshold_usd": args.threshold
        },
        "therapies": results,
        "totals": {
            "total_annual_margin_30_day_usd": total_margin_30,
            "total_annual_margin_90_day_usd": total_margin_90,
            "absolute_difference_usd": abs_diff,
            "decision": decision
        }
    }
    json_path = os.path.join(args.output_dir, "cycle_margin_analysis.json")
    with open(json_path, 'w') as f:
        json.dump(output_json, f, indent=2)

    # Write Markdown
    md_path = os.path.join(args.output_dir, "cycle_margin_summary.md")
    with open(md_path, 'w') as f:
        f.write("# Inhaled Therapy Refill Cycle Analysis\n\n")
        f.write(f"Total annual margin under 30-day fills: ${total_margin_30:,.2f}\n")
        f.write(f"Total annual margin under 90-day fills: ${total_margin_90:,.2f}\n")
        f.write(f"Absolute margin difference (90-day vs 30-day): ${abs_diff:,.2f}\n")
        f.write(f"Decision: {decision}\n\n")
        direction = "improves" if total_margin_90 > total_margin_30 else "reduces"
        reason = "increased" if total_margin_90 > total_margin_30 else "fewer"
        verb = "outweighing" if total_margin_90 > total_margin_30 else "outweighing"
        exceeds = "exceeding" if abs_diff > args.threshold else "falling below"
        f.write(f"The 90-day model {direction} annual margin by ${abs_diff:,.2f} due to {reason} reimbursed fills per year {verb} packaging savings, {exceeds} the ${args.threshold:,} threshold.\n")

    print(f"JSON written to {json_path}")
    print(f"Summary written to {md_path}")
    print(f"Decision: {decision}")

if __name__ == "__main__":
    main()