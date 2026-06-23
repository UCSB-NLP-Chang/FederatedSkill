#!/usr/bin/env python3
import argparse
import csv
import json
import sys

def main():
    parser = argparse.ArgumentParser(description="Compute refill cycle margin analysis.")
    parser.add_argument("--acq", required=True, help="Path to acquisition_cost.csv")
    parser.add_argument("--pkg", required=True, help="Path to packaging_cost.csv")
    parser.add_argument("--reim", required=True, help="Path to reimbursement.csv")
    parser.add_argument("--threshold", type=float, default=12000.0, help="Decision threshold USD")
    parser.add_argument("--out-json", default="cycle_margin_analysis.json")
    parser.add_argument("--out-md", default="cycle_margin_summary.md")
    args = parser.parse_args()

    # Load data (handles tab or comma separated)
    def load_csv(path):
        with open(path, newline='') as f:
            sample = f.read(1024)
            f.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters='\t,')
            return list(csv.DictReader(f, dialect=dialect))

    acq_rows = load_csv(args.acq)
    pkg_rows = load_csv(args.pkg)
    reim_rows = load_csv(args.reim)

    acq_data = {}
    for row in acq_rows:
        acq_data[row['therapy']] = {
            'price_per_1000': float(row['price_per_1000_doses_usd']),
            'canister_size': int(row['canister_size_units'])
        }

    pkg_data = {}
    for row in pkg_rows:
        pkg_data[int(row['canister_size_units'])] = float(row['packaging_cost_usd'])

    reim_data = {}
    for row in reim_rows:
        reim_data[row['therapy']] = float(row['reimbursement_per_fill_240_patients_usd'])

    # Constants
    PATIENTS = 240
    FILLS_30 = 12
    FILLS_90 = 4
    DOSES_30 = 60
    DOSES_90 = 180

    therapies = []
    total_margin_30 = 0.0
    total_margin_90 = 0.0

    for therapy, acq in acq_data.items():
        price = acq['price_per_1000']
        canister = acq['canister_size']
        pkg_cost = pkg_data.get(canister, 0.0)
        reim = reim_data.get(therapy, 0.0)

        # Drug cost (identical for both)
        annual_drug = (price / 1000.0) * DOSES_30 * FILLS_30 * PATIENTS

        # Packaging
        pkg_30 = pkg_cost * FILLS_30 * PATIENTS
        pkg_90 = pkg_cost * FILLS_90 * PATIENTS

        # Reimbursement
        reim_30 = reim * FILLS_30
        reim_90 = reim * FILLS_90

        # Margins
        margin_30 = reim_30 - annual_drug - pkg_30
        margin_90 = reim_90 - annual_drug - pkg_90
        diff = margin_90 - margin_30

        total_margin_30 += margin_30
        total_margin_90 += margin_90

        therapies.append({
            "therapy": therapy,
            "price_per_1000_doses_usd": price,
            "canister_size_units": canister,
            "packaging_cost_usd": pkg_cost,
            "reimbursement_per_fill_240_patients_usd": reim,
            "annual_drug_cost_30_day_usd": round(annual_drug, 2),
            "annual_drug_cost_90_day_usd": round(annual_drug, 2),
            "annual_packaging_cost_30_day_usd": round(pkg_30, 2),
            "annual_packaging_cost_90_day_usd": round(pkg_90, 2),
            "annual_reimbursement_30_day_usd": round(reim_30, 2),
            "annual_reimbursement_90_day_usd": round(reim_90, 2),
            "annual_margin_30_day_usd": round(margin_30, 2),
            "annual_margin_90_day_usd": round(margin_90, 2),
            "annual_margin_difference_90_minus_30_usd": round(diff, 2)
        })

    abs_diff = abs(total_margin_90 - total_margin_30)
    if abs_diff > args.threshold:
        decision = "switch_to_90_day" if total_margin_90 > total_margin_30 else "keep_30_day"
    else:
        decision = "keep_30_day"

    result = {
        "assumptions": {
            "patients_per_therapy": PATIENTS,
            "fills_per_year_30_day": FILLS_30,
            "fills_per_year_90_day": FILLS_90,
            "doses_per_fill_30_day": DOSES_30,
            "doses_per_fill_90_day": DOSES_90,
            "switch_threshold_usd": args.threshold
        },
        "therapies": therapies,
        "totals": {
            "total_annual_margin_30_day_usd": round(total_margin_30, 2),
            "total_annual_margin_90_day_usd": round(total_margin_90, 2),
            "absolute_difference_usd": round(abs_diff, 2),
            "decision": decision
        }
    }

    with open(args.out_json, 'w') as f:
        json.dump(result, f, indent=2)

    md_lines = [
        "**Inhaled Maintenance Therapy Refill Cycle Analysis**",
        "",
        f"Total annual margin (30-day fills): **${total_margin_30:,.2f}**",
        f"Total annual margin (90-day fills): **${total_margin_90:,.2f}**",
        f"Absolute margin difference (90-day vs 30-day): **${abs_diff:,.2f}**",
        "",
        f"Decision: **{decision}** — the absolute total margin difference of ${abs_diff:,.2f} {'exceeds' if abs_diff > args.threshold else 'does not exceed'} the ${args.threshold:,.0f} threshold, so the clinic should {'switch to the 90-day cycle' if decision == 'switch_to_90_day' else 'retain the 30-day refill cycle'}."
    ]
    with open(args.out_md, 'w') as f:
        f.write("\n".join(md_lines) + "\n")

    print(f"Done. abs_diff = {abs_diff}\ndecision = {decision}")

if __name__ == "__main__":
    main()
