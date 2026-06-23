#!/usr/bin/env python3
import argparse
import csv
import json
import sys

def main():
    parser = argparse.ArgumentParser(description="Compute pharmacy refill cycle revenue analysis.")
    parser.add_argument("--wholesale", required=True, help="Path to wholesale_price.csv")
    parser.add_argument("--vial", required=True, help="Path to vial_price.csv")
    parser.add_argument("--reim", required=True, help="Path to reimbursement.csv")
    parser.add_argument("--threshold", type=float, default=16000.0, help="Decision threshold USD")
    parser.add_argument("--out-json", default="refill_analysis.json")
    parser.add_argument("--out-md", default="refill_summary.md")
    args = parser.parse_args()

    def load_csv(path):
        with open(path, newline='') as f:
            sample = f.read(1024)
            f.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters='\t,')
            return list(csv.DictReader(f, dialect=dialect))

    wholesale_rows = load_csv(args.wholesale)
    vial_rows = load_csv(args.vial)
    reim_rows = load_csv(args.reim)

    wholesale_data = {}
    for row in wholesale_rows:
        wholesale_data[row['medication']] = {
            'price_per_1000': float(row['price_per_1000_tablets_usd']),
            'vial_size_drams': int(row['vial_size_drams'])
        }

    vial_data = {}
    for row in vial_rows:
        vial_data[int(row['vial_size_drams'])] = float(row['vial_price_usd'])

    reim_data = {}
    for row in reim_rows:
        reim_data[row['medication']] = float(row['reimbursement_per_fill_300_patients_usd'])

    PATIENTS = 300
    FILLS_90 = 4
    FILLS_100 = 3
    TABS_90 = 90
    TABS_100 = 100

    medications = []
    total_rev_90 = 0.0
    total_rev_100 = 0.0

    for med, w in wholesale_data.items():
        price = w['price_per_1000']
        vial_size = w['vial_size_drams']
        vial_cost = vial_data.get(vial_size, 0.0)
        reim = reim_data.get(med, 0.0)

        # Drug costs
        drug_90 = (price / 1000.0) * TABS_90 * FILLS_90 * PATIENTS
        drug_100 = (price / 1000.0) * TABS_100 * FILLS_100 * PATIENTS

        # Supply costs
        supply_90 = vial_cost * FILLS_90 * PATIENTS
        supply_100 = vial_cost * FILLS_100 * PATIENTS

        # Reimbursement
        reim_90 = reim * FILLS_90
        reim_100 = reim * FILLS_100

        # Revenue
        rev_90 = reim_90 - drug_90 - supply_90
        rev_100 = reim_100 - drug_100 - supply_100
        diff = rev_100 - rev_90

        total_rev_90 += rev_90
        total_rev_100 += rev_100

        medications.append({
            "medication": med,
            "price_per_1000_tablets_usd": price,
            "vial_size_drams": vial_size,
            "vial_price_usd": round(vial_cost, 2),
            "reimbursement_per_fill_300_patients_usd": reim,
            "annual_drug_cost_90_day_usd": round(drug_90, 2),
            "annual_drug_cost_100_day_usd": round(drug_100, 2),
            "annual_supply_cost_90_day_usd": round(supply_90, 2),
            "annual_supply_cost_100_day_usd": round(supply_100, 2),
            "annual_reimbursement_90_day_usd": round(reim_90, 2),
            "annual_reimbursement_100_day_usd": round(reim_100, 2),
            "annual_revenue_90_day_usd": round(rev_90, 2),
            "annual_revenue_100_day_usd": round(rev_100, 2),
            "annual_revenue_difference_100_minus_90_usd": round(diff, 2)
        })

    abs_diff = abs(total_rev_100 - total_rev_90)
    if abs_diff > args.threshold:
        decision = "switch_to_100_day" if total_rev_100 > total_rev_90 else "keep_90_day"
    else:
        decision = "keep_90_day"

    result = {
        "assumptions": {
            "patients_per_medication": PATIENTS,
            "fills_per_year_90_day": FILLS_90,
            "fills_per_year_100_day": FILLS_100,
            "tablets_per_fill_90_day": TABS_90,
            "tablets_per_fill_100_day": TABS_100,
            "switch_threshold_usd": args.threshold
        },
        "medications": medications,
        "totals": {
            "total_annual_revenue_90_day_usd": round(total_rev_90, 2),
            "total_annual_revenue_100_day_usd": round(total_rev_100, 2),
            "absolute_difference_usd": round(abs_diff, 2),
            "decision": decision
        }
    }

    with open(args.out_json, 'w') as f:
        json.dump(result, f, indent=2)

    md_lines = [
        "# Auto-Refill Policy Analysis Summary",
        "",
        f"- Total annual revenue (90-day fills): **${total_rev_90:,.2f}**",
        f"- Total annual revenue (100-day fills): **${total_rev_100:,.2f}**",
        f"- Absolute revenue difference (100-day vs 90-day): **${abs_diff:,.2f}**",
        f"- Threshold: **${args.threshold:,.2f}**",
        "",
        f"**Decision: `{decision}`**",
        "",
        f"The absolute revenue difference of **${abs_diff:,.2f}** {'exceeds' if abs_diff > args.threshold else 'does not exceed'} the ${args.threshold:,.2f} threshold, so the pharmacy should {'switch to the 100-day cycle' if decision == 'switch_to_100_day' else 'keep 90-day fills'}."
    ]
    with open(args.out_md, 'w') as f:
        f.write("\n".join(md_lines) + "\n")

    print(f"Done. abs_diff = {abs_diff}\ndecision = {decision}")

if __name__ == "__main__":
    main()
